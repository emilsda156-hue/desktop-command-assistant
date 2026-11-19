"""Allowlisted tools. No shell execution; destructive actions require UI approval."""
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
import webbrowser
import zipfile

HOME = Path.home() / 'Orbit'

def normalized(text):
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c)).replace('ł', 'l').strip()


def parse_tool(command):
    text = normalized(command)
    patterns = [
        ('cancel_power', r'(?:anuluj (?:wylaczenie|restart)|cancel (?:shutdown|restart))'),
        ('shutdown', r'(?:wylacz komputer|shutdown(?: computer)?)'),
        ('restart', r'(?:uruchom ponownie(?: komputer)?|restart(?: computer)?)'),
        ('sleep', r'(?:uspij(?: komputer)?|sleep(?: computer)?)'),
        ('lock', r'(?:zablokuj (?:ekran|komputer)|lock(?: screen)?)'),
        ('unmute', r'(?:wlacz dzwiek|unmute)'), ('mute', r'(?:wycisz(?: dzwiek)?|mute)'),
        ('processes', r'(?:pokaz procesy|top processes|zuzycie (?:ram|cpu)|(?:ram|cpu) usage)'),
        ('close_process', r'(?:zamknij proces|close process) (.+)'),
        ('organize', r'(?:posprzataj pobrane|sprzataj pobrane|organize downloads)'),
        ('search', r'(?:szukaj pliku|znajdz plik|find file) (.+)'),
        ('note', r'(?:notatka|note) (.+)'),
        ('backup', r'(?:kopia folderu|backup folder) (.+)'),
        ('screenshot', r'(?:zrzut ekranu|screenshot)(?: (.+))?'),
        ('weather', r'(?:pogoda|weather) (.+)'),
        ('currency', r'(?:kurs|rate) ([a-z]{3})'),
        ('status', r'(?:status) (https?://\S+)'),
        ('url', r'(?:otworz strone|open website) (https?://\S+)'),
        ('task', r'(?:dodaj zadanie|add task) (.+)'),
        ('tasks', r'(?:pokaz zadania|show tasks)'),
        ('done', r'(?:zakoncz zadanie|complete task) (\d+)'),
        ('reminder', r'(?:przypomnij|remind) (.+)'),
        ('script', r'(?:uruchom skrypt|run script) ([\w-]+)'),
    ]
    for kind, pattern in patterns:
        if kind in {'shutdown', 'restart'}:
            pattern += r'(?: (?:za|in) (\d+) (sekund(?:y)?|seconds?|minut(?:y)?|minutes?))?'
        match = re.fullmatch(pattern, text)
        if match:
            # Preserve original case, accents and paths for user values.
            value = command.strip()[match.start(1):match.end(1)] if match.lastindex and match.group(1) else ''
            delay = 0
            if kind in {'shutdown', 'restart'} and value:
                delay = int(value) * (60 if match.group(2).startswith('min') else 1)
                if delay > 86400:
                    raise ValueError('Maksymalne opóźnienie to 24 godziny.')
            return {'kind': kind, 'value': value.strip().strip('"'), 'delay': delay}
    return None


def path_value(value):
    return Path(os.path.expandvars(value.strip().strip('"'))).expanduser().resolve()


def safe_destination(path):
    # Default locations never overwrite existing files.
    path = Path(path)
    candidate = path
    number = 1
    while candidate.exists():
        candidate = path.with_name(f'{path.stem}_{number}{path.suffix}')
        number += 1
    return candidate


def require_windows():
    if os.name != 'nt':
        raise RuntimeError('Ta akcja wymaga Windows.')


def fetch_json(url):
    request = Request(url, headers={'User-Agent': 'Orbit/2.0'})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read(2_000_000))


def web_url(value):
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Podaj adres http:// lub https:// bez hasła.')
    return value


def process_list():
    import psutil
    processes = list(psutil.process_iter(['pid', 'name', 'username']))
    for process in processes:
        try:
            process.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    time.sleep(1)
    rows = []
    for process in processes:
        try:
            rows.append({'pid': process.pid, 'name': process.name(), 'ram': process.memory_info().rss / 1024**2, 'cpu': process.cpu_percent(None)})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return rows


def closable_processes(name):
    import psutil
    if not re.fullmatch(r'[\w .-]+\.exe', name, flags=re.I):
        raise ValueError('Podaj dokładną nazwę, np. notepad.exe.')
    protected = {'system', 'system.exe', 'registry.exe', 'svchost.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe', 'lsass.exe', 'services.exe', 'smss.exe', 'explorer.exe', 'dwm.exe', 'python.exe', 'pythonw.exe'}
    if name.lower() in protected:
        raise ValueError('Orbit nie zamyka chronionych procesów systemu ani siebie.')
    user = psutil.Process().username()
    candidates = []
    for process in psutil.process_iter(['name', 'username', 'create_time']):
        if (process.info['name'] or '').lower() == name.lower() and process.info['username'] == user and process.pid != os.getpid():
            candidates.append((process.pid, process.info['create_time']))
    return candidates


def confirmation(action):
    kind, value = action['kind'], action['value']
    if kind in {'shutdown', 'restart', 'sleep'}:
        return f"{kind}: opóźnienie {action['delay']} s. Zapisz pracę. Kontynuować?"
    if kind == 'close_process':
        action['targets'] = closable_processes(value)
        if not action['targets']:
            raise ValueError('Nie znaleziono procesu należącego do bieżącego użytkownika.')
        return f"Zamknąć {value}, PID: {[p[0] for p in action['targets']]}? Niezapisane dane mogą zostać utracone."
    if kind == 'organize':
        return 'Przenieść pliki z Pobrane do podfolderów Zdjęcia, Archiwa, Instalatory, Dokumenty i Inne? Nic nie zostanie usunięte ani nadpisane.'
    if kind == 'script':
        spec = script_spec(value)
        action['script_spec'] = spec
        return f"Uruchomić zatwierdzony skrypt {value}: {spec['path']}? Skrypt może zmieniać pliki i system."
    return None


def script_spec(alias):
    config = HOME / 'scripts.json'
    scripts = json.loads(config.read_text('utf-8')) if config.exists() else {}
    spec = scripts.get(alias)
    if not isinstance(spec, dict) or spec.get('approved') is not True:
        raise ValueError('Skrypt niezatwierdzony. Użyj przycisku „Dodaj skrypt” i wybierz zaufany plik .py.')
    path = path_value(spec.get('path', ''))
    if path.suffix.lower() != '.py' or not path.is_file():
        raise ValueError('Zatwierdzony plik .py nie istnieje.')
    return {'path': str(path)}


def approve_script(alias, path):
    if not re.fullmatch(r'[\w-]+', alias):
        raise ValueError('Nazwa skryptu: litery, cyfry, myślnik, podkreślenie.')
    path = path_value(path)
    if path.suffix.lower() != '.py' or not path.is_file():
        raise ValueError('Wybierz istniejący plik .py.')
    HOME.mkdir(parents=True, exist_ok=True)
    config = HOME / 'scripts.json'
    scripts = json.loads(config.read_text('utf-8')) if config.exists() else {}
    scripts[alias] = {'path': str(path), 'approved': True}
    config.write_text(json.dumps(scripts, ensure_ascii=False, indent=2), encoding='utf-8')


def load_tasks():
    file = HOME / 'tasks.json'
    return json.loads(file.read_text('utf-8')) if file.exists() else []


def save_tasks(tasks):
    HOME.mkdir(parents=True, exist_ok=True)
    temp = HOME / 'tasks.tmp'
    temp.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(HOME / 'tasks.json')


def run_tool(action, confirmed=False):
    kind, value = action['kind'], action['value']
    if kind in {'shutdown', 'restart', 'sleep', 'close_process', 'organize', 'script'} and not confirmed:
        raise PermissionError('Ta akcja wymaga potwierdzenia w oknie Orbit.')
    if kind in {'shutdown', 'restart', 'cancel_power', 'sleep', 'lock', 'mute', 'unmute'}:
        require_windows()
        if kind in {'shutdown', 'restart'}:
            subprocess.run(['shutdown.exe', '/s' if kind == 'shutdown' else '/r', '/t', str(action['delay'])], check=True, shell=False)
            return 'Windows otrzymał polecenie. Anulowanie: „anuluj wyłączenie”. Przy opóźnieniu Windows może wymusić zamknięcie aplikacji — zapisz pracę.'
        if kind == 'cancel_power':
            subprocess.run(['shutdown.exe', '/a'], check=True, shell=False)
        elif kind == 'sleep':
            if not ctypes.windll.powrprof.SetSuspendState(False, False, False):
                raise OSError('Windows odrzucił uśpienie.')
        elif kind == 'lock':
            if not ctypes.windll.user32.LockWorkStation():
                raise OSError('Windows odrzucił blokadę.')
        else:
            from pycaw.pycaw import AudioUtilities
            import comtypes
            comtypes.CoInitialize()
            try:
                AudioUtilities.GetSpeakers().EndpointVolume.SetMute(kind == 'mute', None)
            finally:
                comtypes.CoUninitialize()
        return 'Wykonano: ' + kind
    if kind == 'processes':
        rows = process_list()
        format_row = lambda row: f"{row['name']} · PID {row['pid']} · {row['ram']:.0f} MB · {row['cpu']:.1f}% CPU"
        return 'Najwięcej RAM:\n' + '\n'.join(map(format_row, sorted(rows, key=lambda row: row['ram'], reverse=True)[:5])) + '\n\nNajwięcej CPU (próbka 1 s):\n' + '\n'.join(map(format_row, sorted(rows, key=lambda row: row['cpu'], reverse=True)[:5]))
    if kind == 'close_process':
        import psutil
        results = []
        for pid, created in action.get('targets', []):
            try:
                process = psutil.Process(pid)
                if process.create_time() != created or process.name().lower() != value.lower() or process.username() != psutil.Process().username():
                    results.append(f'PID {pid}: pominięty, proces zmienił się.')
                    continue
                process.terminate()
                process.wait(timeout=3)
                results.append(f'PID {pid}: zamknięty.')
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as error:
                results.append(f'PID {pid}: {type(error).__name__}; nie wymuszono zamknięcia.')
        return '\n'.join(results) or 'Brak zatwierdzonych procesów.'
    if kind == 'organize':
        source = Path.home() / 'Downloads'
        if not source.is_dir():
            raise ValueError('Nie znaleziono standardowego folderu Downloads. Folder przeniesiony wymaga dostosowania.')
        groups = {'Zdjęcia': {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic'}, 'Archiwa': {'.zip', '.rar', '.7z', '.tar', '.gz'}, 'Instalatory': {'.exe', '.msi', '.msix'}, 'Dokumenty': {'.pdf', '.doc', '.docx', '.txt', '.md', '.xlsx', '.csv', '.pptx'}}
        count = 0
        for file in list(source.iterdir()):
            if not file.is_file() or file.is_symlink() or file.suffix.lower() in {'.crdownload', '.part', '.tmp'}:
                continue
            group = next((name for name, extensions in groups.items() if file.suffix.lower() in extensions), 'Inne')
            destination = source / group
            if destination.is_symlink():
                raise ValueError('Folder docelowy jest dowiązaniem; przerwano porządkowanie.')
            destination.mkdir(exist_ok=True)
            shutil.move(str(file), str(safe_destination(destination / file.name)))
            count += 1
        return f'Przeniesiono {count} plików. Bez usuwania i nadpisywania.'
    if kind == 'search':
        # query | root; defaults to home. No traversal through links.
        query, _, root_value = value.partition(' | ')
        root = path_value(root_value) if root_value else Path.home()
        if not root.is_dir() or not query:
            raise ValueError('Użyj: znajdź plik raport | C:\\Dokumenty')
        found = []
        deadline = time.monotonic() + 15
        for directory, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
            for name in files:
                if query.lower() in name.lower() or (query.startswith('*.') and name.lower().endswith(query[1:].lower())):
                    found.append(str(Path(directory) / name))
                    if len(found) >= 100:
                        return '\n'.join(found) + '\nLimit 100 wyników.'
            if time.monotonic() > deadline:
                return '\n'.join(found) + '\nPrzerwano po 15 s; zawęź folder.'
        return '\n'.join(found) or 'Nie znaleziono plików.'
    if kind == 'note':
        name, separator, content = value.partition(' | ')
        if not separator or Path(name).name != name or Path(name).suffix.lower() not in {'.txt', '.md'}:
            raise ValueError('Użyj: notatka pomysly.md | Treść notatki')
        destination = HOME / 'Notatki'
        destination.mkdir(parents=True, exist_ok=True)
        file = safe_destination(destination / name)
        with file.open('x', encoding='utf-8') as stream:
            stream.write(content)
        return 'Zapisano: ' + str(file)
    if kind == 'backup':
        source_value, _, target_value = value.partition(' | ')
        source = path_value(source_value)
        if not source.is_dir() or source.is_symlink():
            raise ValueError('Wskaż istniejący folder, nie dowiązanie.')
        target = path_value(target_value) if target_value else HOME / 'Kopie'
        target = target.resolve()
        if target == source or source in target.parents:
            raise ValueError('Kopia nie może być zapisana wewnątrz kopiowanego folderu.')
        target.mkdir(parents=True, exist_ok=True)
        archive = safe_destination(target / (source.name + time.strftime('_%Y%m%d_%H%M%S.zip')))
        count = 0
        with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as output:
            for directory, dirs, files in os.walk(source, followlinks=False):
                dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
                output.write(directory, str(Path(directory).relative_to(source)) + '/')
                for name in files:
                    file = Path(directory) / name
                    if not file.is_symlink():
                        output.write(file, str(file.relative_to(source)))
                        count += 1
        return f'Kopia ZIP: {archive} ({count} plików). Oryginały pozostawiono.'
    if kind == 'screenshot':
        from PIL import ImageGrab
        file = path_value(value) if value else HOME / 'Zrzuty' / time.strftime('%Y%m%d_%H%M%S.png')
        if file.suffix.lower() != '.png':
            raise ValueError('Podaj plik docelowy .png.')
        file.parent.mkdir(parents=True, exist_ok=True)
        file = safe_destination(file)
        ImageGrab.grab(all_screens=True).save(file, 'PNG')
        return 'Zrzut wszystkich ekranów: ' + str(file)
    if kind == 'weather':
        geo = fetch_json('https://geocoding-api.open-meteo.com/v1/search?count=1&language=pl&name=' + quote(value))
        locations = geo.get('results') or []
        if not locations:
            return 'Nie znaleziono miasta.'
        city = locations[0]
        weather = fetch_json(f"https://api.open-meteo.com/v1/forecast?latitude={city['latitude']}&longitude={city['longitude']}&current=temperature_2m,apparent_temperature,wind_speed_10m&timezone=auto")['current']
        return f"{city['name']} ({city.get('country', '')}) · {weather['temperature_2m']} °C · odczuwalna {weather['apparent_temperature']} °C · wiatr {weather['wind_speed_10m']} km/h · {weather['time']}. Źródło: Open-Meteo."
    if kind == 'currency':
        data = fetch_json('https://api.nbp.pl/api/exchangerates/rates/a/' + value.lower() + '/?format=json')
        rate = data['rates'][0]
        return f"1 {value.upper()} = {rate['mid']} PLN · {rate['effectiveDate']} · średni kurs NBP, tabela A."
    if kind == 'status':
        url = web_url(value)
        with urlopen(Request(url, method='HEAD', headers={'User-Agent': 'Orbit/2.0'}), timeout=10) as response:
            return f'{url}: HTTP {response.status} · sprawdzono teraz. To dostępność adresu, nie pełny status usługi.'
    if kind == 'url':
        webbrowser.open(web_url(value))
        return 'Wysłano adres do przeglądarki.'
    if kind in {'task', 'tasks', 'done', 'reminder'}:
        tasks = load_tasks()
        if kind in {'task', 'reminder'}:
            due = None
            title = value
            if kind == 'reminder':
                # e.g. przypomnij za 5 minut | woda / remind in 5 minutes | water
                timing, separator, title = value.partition(' | ')
                match = re.fullmatch(r'(?:za|in) (\d+) (minut(?:y)?|minutes?)', normalized(timing))
                if not separator or not match or not title.strip() or not 1 <= int(match.group(1)) <= 10080:
                    raise ValueError('Użyj: przypomnij za 5 minut | Wypij wodę (1–10080 minut).')
                due = time.time() + int(match.group(1)) * 60
            tasks.append({'id': max((t['id'] for t in tasks), default=0) + 1, 'title': title, 'done': False, 'due': due, 'notified': False})
            save_tasks(tasks)
            return f"Dodano zadanie {tasks[-1]['id']}: {title}. Przypomnienia działają, gdy Orbit jest otwarty."
        if kind == 'done':
            target = next((task for task in tasks if task['id'] == int(value)), None)
            if not target:
                return 'Nie znaleziono zadania.'
            target['done'] = True
            save_tasks(tasks)
            return 'Zadanie zakończone.'
        return '\n'.join(f"{task['id']}. {'✓' if task['done'] else '○'} {task['title']}" for task in tasks) or 'Lista jest pusta.'
    if kind == 'script':
        # Revalidate approval immediately before launch; no command-line input.
        spec = script_spec(value)
        if spec != action.get('script_spec'):
            raise ValueError('Konfiguracja skryptu zmieniła się; potwierdź ponownie.')
        process = subprocess.Popen([sys.executable, spec['path']], cwd=str(Path(spec['path']).parent), shell=False)
        return f'Uruchomiono skrypt: PID {process.pid}. Wynik w osobnym procesie; Orbit nie gwarantuje jego bezpieczeństwa.'
    raise ValueError('Nieznana akcja.')

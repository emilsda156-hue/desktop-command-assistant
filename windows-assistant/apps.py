"""Installed app discovery and validated app/game launch targets."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlparse
import webbrowser
from tools import HOME, normalized, web_url, closable_processes

# display name | aliases | known executables. Presence is checked, never assumed.
CATALOG = [
 ('Google Chrome', 'chrome|google chrome', 'chrome.exe'), ('Mozilla Firefox', 'firefox|mozilla firefox', 'firefox.exe'),
 ('Microsoft Edge', 'edge|microsoft edge', 'msedge.exe'), ('Opera GX', 'opera gx|opera', 'opera.exe'), ('Brave', 'brave', 'brave.exe'),
 ('Discord', 'discord|komunikator|messenger', 'Discord.exe'), ('WhatsApp', 'whatsapp', 'WhatsApp.exe'), ('Telegram', 'telegram', 'Telegram.exe'),
 ('Microsoft Teams', 'teams|microsoft teams', 'ms-teams.exe|Teams.exe'), ('Zoom', 'zoom', 'Zoom.exe'), ('Skype', 'skype', 'Skype.exe'), ('Slack', 'slack', 'slack.exe'),
 ('Spotify', 'spotify', 'Spotify.exe'), ('VLC', 'vlc|vlc media player', 'vlc.exe'), ('Tidal', 'tidal', 'TIDAL.exe'), ('Apple Music', 'apple music', 'AppleMusic.exe'),
 ('OBS Studio', 'obs|obs studio', 'obs64.exe'), ('NVIDIA App', 'nvidia app|geforce experience', 'NVIDIA App.exe|NVIDIA GeForce Experience.exe'),
 ('AMD Software', 'amd adrenalin|amd software', 'RadeonSoftware.exe'), ('Word', 'word|microsoft word', 'WINWORD.EXE'), ('Excel', 'excel|microsoft excel', 'EXCEL.EXE'),
 ('PowerPoint', 'powerpoint|microsoft powerpoint', 'POWERPNT.EXE'), ('Notepad++', 'notepad++', 'notepad++.exe'), ('Notion', 'notion', 'Notion.exe'), ('Obsidian', 'obsidian', 'Obsidian.exe'),
 ('LibreOffice', 'libreoffice', 'soffice.exe|soffice.bin'), ('Visual Studio Code', 'visual studio code|vscode|vs code|edytor|editor', 'Code.exe'),
 ('PyCharm', 'pycharm', 'pycharm64.exe'), ('Windows Terminal', 'terminal|windows terminal', 'wt.exe'), ('PowerShell', 'powershell', 'powershell.exe|pwsh.exe'),
 ('Task Manager', 'menedzer zadan|task manager', 'taskmgr.exe'), ('File Explorer', 'eksplorator|eksplorator plikow|file explorer', 'explorer.exe'),
 ('Control Panel', 'panel sterowania|control panel', 'control.exe'), ('Settings', 'ustawienia|settings|ustawienia windows', 'SystemSettings.exe'),
 ('Photoshop', 'photoshop', 'Photoshop.exe'), ('GIMP', 'gimp', 'gimp-3.exe|gimp-2.10.exe'), ('Blender', 'blender', 'blender.exe'),
 ('DaVinci Resolve', 'davinci resolve|davinci|resolve', 'Resolve.exe'), ('CapCut', 'capcut', 'CapCut.exe'), ('7-Zip', '7-zip|7zip', '7zFM.exe'),
 ('WinRAR', 'winrar', 'WinRAR.exe'), ('qBittorrent', 'qbittorrent', 'qbittorrent.exe'), ('MSI Afterburner', 'msi afterburner|afterburner', 'MSIAfterburner.exe'),
 ('HWiNFO', 'hwinfo|hwinfo64', 'HWiNFO64.exe'), ('Steam', 'steam', 'steam.exe'), ('Epic Games Launcher', 'epic|epic games|epic games launcher', 'EpicGamesLauncher.exe'),
 ('Ubisoft Connect', 'ubisoft|ubisoft connect', 'UbisoftConnect.exe'), ('EA App', 'ea|ea app', 'EADesktop.exe'), ('GOG Galaxy', 'gog|gog galaxy', 'GalaxyClient.exe'),
 ('Battle.net', 'battle.net|battlenet', 'Battle.net.exe'), ('Riot Client', 'riot|riot client', 'RiotClientServices.exe'), ('Xbox', 'xbox|aplikacja xbox', 'XboxPcApp.exe'),
 ('CurseForge', 'curseforge', 'CurseForge.exe'), ('Prism Launcher', 'prism|prism launcher', 'prismlauncher.exe'),
 ('Minecraft Launcher', 'minecraft launcher|minecraft', 'MinecraftLauncher.exe'), ('Notepad', 'notatnik|notepad', 'notepad.exe'),
 ('Calculator', 'kalkulator|calculator', 'calc.exe'),
]
WEBSITES = {'youtube': 'https://www.youtube.com', 'yt': 'https://www.youtube.com', 'gmail': 'https://mail.google.com', 'google drive': 'https://drive.google.com', 'dysk google': 'https://drive.google.com', 'chatgpt': 'https://chatgpt.com', 'netflix': 'https://www.netflix.com', 'reddit': 'https://www.reddit.com'}


def load_config():
    file = HOME / 'apps.json'
    return json.loads(file.read_text('utf-8')) if file.exists() else {'apps': {}, 'aliases': {}, 'profiles': {'gamingowy': {'open': ['discord', 'steam'], 'close': []}, 'gaming': {'open': ['discord', 'steam'], 'close': []}, 'nauki': {'open': ['przegladarka', 'notatnik', 'spotify'], 'close': []}, 'study': {'open': ['przegladarka', 'notatnik', 'spotify'], 'close': []}}}


def validate_target(target):
    if target.startswith('steam://rungameid/') and re.fullmatch(r'steam://rungameid/\d+', target):
        return 'uri'
    if target.startswith('com.epicgames.launcher://apps/') and re.fullmatch(r'com\.epicgames\.launcher://apps/[A-Za-z0-9_%:/?=&.\-]+', target):
        return 'uri'
    # Launcher-specific game IDs are user supplied, never invented.
    if re.fullmatch(r'(?:uplay://launch/\d+(?:/\d+)?|origin://launchgame/[A-Za-z0-9:._-]+|goggalaxy://[A-Za-z0-9/?=&._-]+|battlenet://[A-Za-z0-9/?=&._-]+|riotclient://[A-Za-z0-9/?=&._-]+)', target):
        return 'uri'
    path = Path(target).expanduser()
    if path.is_file() and path.suffix.lower() in {'.exe', '.lnk', '.url'}:
        return 'file'
    raise ValueError('Wybierz istniejący .exe/.lnk/.url lub poprawny protokół gry (Steam/Epic/Uplay/Origin/GOG/Battle.net/Riot).')


def register_app(alias, target, process_names=''):
    alias = normalized(alias)
    if not alias or len(alias) > 100:
        raise ValueError('Podaj krótką nazwę aplikacji lub gry.')
    validate_target(target)
    processes = [name.strip() for name in process_names.split(',') if name.strip()]
    if any(not re.fullmatch(r'[\w .+-]+\.exe', name, re.I) for name in processes):
        raise ValueError('Nazwy procesów muszą kończyć się .exe, oddzielaj przecinkami.')
    config = load_config()
    config['apps'][alias] = {'target': target, 'processes': processes}
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / 'apps.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')


class AppRegistry:
    def __init__(self):
        self.shortcuts = []
        self.store = []
        self.paths = {}
        self.scanned = False

    def scan(self):
        if os.name != 'nt':
            return
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths', 0, winreg.KEY_READ | view) as key:
                        for index in range(winreg.QueryInfoKey(key)[0]):
                            exe = winreg.EnumKey(key, index)
                            try:
                                with winreg.OpenKey(key, exe) as sub:
                                    path = winreg.QueryValue(sub, None).strip('"')
                                    if Path(path).is_file():
                                        self.paths[exe.lower()] = path
                            except OSError:
                                pass
                except OSError:
                    pass
        roots = [Path.home() / 'Desktop', Path(os.environ.get('PUBLIC', 'C:/Users/Public')) / 'Desktop', Path(os.environ.get('APPDATA', '')) / 'Microsoft/Windows/Start Menu/Programs', Path(os.environ.get('PROGRAMDATA', 'C:/ProgramData')) / 'Microsoft/Windows/Start Menu/Programs']
        self.shortcuts = []
        for root in roots:
            if root.is_dir():
                self.shortcuts.extend(file for file in root.rglob('*') if file.suffix.lower() in {'.lnk', '.url'} and file.is_file())
        try:
            data = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', '[Console]::OutputEncoding=[System.Text.Encoding]::UTF8; Get-StartApps | ConvertTo-Json -Compress'], capture_output=True, text=True, encoding='utf-8', timeout=25, check=True, shell=False)
            apps = json.loads(data.stdout or '[]')
            self.store = apps if isinstance(apps, list) else [apps]
        except (OSError, ValueError, subprocess.SubprocessError):
            self.store = []
        self.scanned = True

    def resolve(self, name):
        name = normalized(name)
        config = load_config()
        name = normalized(config.get('aliases', {}).get(name, name))
        if name in {'przegladarka', 'browser'}:
            return {'kind': 'website', 'target': 'https://www.google.com', 'processes': []}
        if name in WEBSITES:
            return {'kind': 'website', 'target': WEBSITES[name], 'processes': []}
        if name in config['apps']:
            spec = config['apps'][name]
            return {'kind': validate_target(spec['target']), 'target': spec['target'], 'processes': spec.get('processes', [])}
        entry = next((entry for entry in CATALOG if name in [normalized(a) for a in entry[1].split('|')]), None)
        executables = entry[2].split('|') if entry else []
        if entry and name in {'ustawienia', 'settings', 'ustawienia windows'}:
            return {'kind': 'settings', 'target': 'ms-settings:', 'processes': executables}
        for exe in executables:
            path = self.paths.get(exe.lower()) or shutil.which(exe)
            if path:
                return {'kind': 'file', 'target': path, 'processes': executables}
        names = {name}
        if entry:
            names.update(normalized(a) for a in entry[1].split('|'))
            names.add(normalized(entry[0]))
        matches = [file for file in self.shortcuts if normalized(file.stem) in names]
        if len(matches) == 1:
            return {'kind': 'file', 'target': str(matches[0]), 'processes': executables}
        matches_store = [app for app in self.store if normalized(app.get('Name', '')) in names]
        if len(matches_store) == 1:
            app = matches_store[0]
            app_id = app.get('AppID', '')
            if re.fullmatch(r'[\w.!{}\\: -]+', app_id) and '!' in app_id:
                return {'kind': 'store', 'target': app_id, 'processes': executables}
        if len(matches) > 1 or len(matches_store) > 1:
            raise ValueError('Nazwa jest niejednoznaczna. Dodaj dokładny skrót w „Dodaj aplikację”.')
        # Explicit .exe names on PATH are allowed; arguments are not.
        if re.fullmatch(r'[\w.+-]+\.exe', name):
            path = shutil.which(name)
            if path:
                return {'kind': 'file', 'target': path, 'processes': [name]}
        raise ValueError('Nie znalazłem takiej aplikacji na komputerze. Przeskanuj aplikacje lub dodaj jej skrót. Gry i modpacki wymagają własnego skrótu/ID; nie zgaduję.')

    def launch(self, name):
        if not self.scanned:
            self.scan()
        return self.launch_spec(self.resolve(name))

    def launch_spec(self, spec):
        if spec['kind'] == 'website':
            webbrowser.open(spec['target'])
        else:
            if os.name != 'nt':
                raise RuntimeError('Uruchamianie aplikacji wymaga Windows.')
            if spec['kind'] == 'store':
                subprocess.Popen(['explorer.exe', 'shell:AppsFolder\\' + spec['target']], shell=False)
            else:
                os.startfile(spec['target'])
        return 'Już włączam. Przekazano polecenie uruchomienia; nie gwarantuje to załadowania gry ani zalogowania do launchera.'

    def close_targets(self, name):
        if not self.scanned:
            self.scan()
        spec = self.resolve(name)
        targets = []
        for process in spec['processes']:
            targets.extend(closable_processes(process))
        if not targets:
            raise ValueError('Brak procesu do zamknięcia. Dla własnej gry dodaj jej dokładną nazwę .exe; nie zamykam launchera zamiast gry.')
        return list(set(targets))

REGISTRY = AppRegistry()


def parse_app(command):
    text = normalized(command)
    match = re.fullmatch(r'(?:tryb|mode|uruchom tryb) (.+)', text)
    if match:
        return {'kind': 'profile', 'value': match.group(1), 'delay': 0}
    match = re.fullmatch(r'(?:odpal|otworz|wlacz|uruchom|open|launch|start|zamknij|close) (.+)', text)
    if not match:
        return None
    closing = text.startswith(('zamknij ', 'close '))
    name = match.group(1)
    # Known website in chosen browser: otwórz Gmail w chrome / open gmail in firefox.
    website = re.fullmatch(r'(.+) (?:w|in) (.+)', name)
    if website and not closing and website.group(1) in WEBSITES:
        return {'kind': 'browser_site', 'value': website.group(2), 'url': WEBSITES[website.group(1)], 'delay': 0}
    return {'kind': 'close_app' if closing else 'open_app', 'value': name, 'delay': 0}


def profile_plan(name):
    profile = load_config()['profiles'].get(name)
    if not isinstance(profile, dict):
        raise ValueError('Nie ma takiego profilu w apps.json.')
    plan = {'open': [], 'close': []}
    for app in profile.get('open', []):
        plan['open'].append((app, REGISTRY.resolve(app)))
    for app in profile.get('close', []):
        plan['close'].extend(REGISTRY.close_targets(app))
    return plan

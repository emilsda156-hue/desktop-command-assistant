"""Windows controls using fixed APIs, validated values and safe fallbacks."""
import ctypes
from ctypes import wintypes
import io
import os
from pathlib import Path
import re
import subprocess
import time
from tools import HOME, normalized, require_windows, safe_destination


def parse_control(command):
    patterns = [
        ('hibernate', r'(?:hibernuj(?: system)?|hibernate)'), ('logout', r'(?:wyloguj(?: uzytkownika)?|log out)'),
        ('power_plan', r'(?:plan zasilania|power plan) (oszczedzanie|zrownowazony|wysoka wydajnosc|saver|balanced|performance)'),
        ('volume', r'(?:glosnosc|volume) (\d{1,3})(?: ?%)?'),
        ('volume_up', r'(?:podglosnij o|volume up) (\d{1,3})'), ('volume_down', r'(?:scisz o|volume down) (\d{1,3})'),
        ('mute_app', r'(?:wycisz aplikacje|mute app) (.+)'),
        ('mute_mic', r'(?:wycisz mikrofon|mute microphone)'), ('unmute_mic', r'(?:wlacz mikrofon|unmute microphone)'),
        ('audio_output', r'(?:wyjscie audio|audio output) (.+)'),
        ('brightness', r'(?:jasnosc|brightness) (\d{1,3})(?: ?%)?'),
        ('night', r'(?:tryb nocny|night light)(?: (?:on|off|wlacz|wylacz))?'),
        ('display_settings', r'(?:rozdzielczosc|resolution|odswiezanie|refresh rate)(?: .+)?'),
        ('minimize', r'(?:minimalizuj wszystkie okna|minimize all)'), ('maximize', r'(?:maksymalizuj|maximize)'),
        ('close_window', r'(?:zamknij aktywne okno|close active window)'),
        ('switch_window', r'(?:przelacz okno|switch window)'), ('pin', r'(?:przypnij okno|pin window)'), ('unpin', r'(?:odepnij okno|unpin window)'),
        ('snap_left', r'(?:okno w lewo|snap left)'), ('snap_right', r'(?:okno w prawo|snap right)'),
        ('snap_pair', r'(?:uloz okna obok siebie|snap two windows)'),
        ('new_desktop', r'(?:nowy pulpit|new desktop)'), ('next_desktop', r'(?:kolejny pulpit|next desktop)'), ('previous_desktop', r'(?:poprzedni pulpit|previous desktop)'),
        ('screenshot_window', r'(?:zrzut aktywnego okna|screenshot window)(?: (.+))?'),
        ('screenshot_clipboard', r'(?:zrzut do schowka|screenshot clipboard)'),
        ('wifi', r'(?:wi-?fi) (on|off|wlacz|wylacz)'), ('connect_wifi', r'(?:polacz wi-?fi|connect wifi) (.+)'),
        ('disconnect_wifi', r'(?:rozlacz wi-?fi|disconnect wifi)'),
        ('bluetooth', r'(?:bluetooth)(?: .+)?'), ('airplane', r'(?:tryb samolotowy|airplane mode)(?: .+)?'),
        ('eject', r'(?:wysun usb|eject usb)(?: .+)?'),
        ('hotkey', r'(?:skrot|hotkey) (.+)'), ('dictate', r'(?:wpisz tekst|type text) (.+)'), ('click', r'(?:kliknij|click) (\d+ \d+)'),
        ('media_pause', r'(?:pauza|wznow muzyke|pause|play music)'), ('media_next', r'(?:nastepny utwor|next track)'), ('media_previous', r'(?:poprzedni utwor|previous track)'),
        ('clipboard_read', r'(?:odczytaj schowek|read clipboard)'), ('clipboard_clear', r'(?:wyczysc schowek|clear clipboard)'), ('clipboard_write', r'(?:do schowka|to clipboard) (.+)'),
        ('active_title', r'(?:aktywne okno|active window)'), ('ocr', r'(?:odczytaj ekran|read screen)'),
    ]
    text = normalized(command)
    for kind, pattern in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            value = command.strip()[match.start(1):match.end(1)] if match.lastindex and match.group(1) else ''
            return {'kind': kind, 'value': value, 'delay': 0}
    return None


def foreground():
    require_windows()
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.restype = wintypes.HWND
    return user32.GetForegroundWindow()


def window_title(hwnd=None):
    require_windows()
    user32 = ctypes.windll.user32
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    hwnd = hwnd or foreground()
    buffer = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd) + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    return buffer.value


def audio_action(kind, value):
    import comtypes
    from pycaw.pycaw import AudioUtilities
    comtypes.CoInitialize()
    try:
        if kind in {'mute_mic', 'unmute_mic'}:
            device = AudioUtilities.GetMicrophone()
            device.EndpointVolume.SetMute(kind == 'mute_mic', None)
            return 'Wyciszam mikrofon.' if kind == 'mute_mic' else 'Mikrofon włączony.'
        if kind == 'mute_app':
            from apps import CATALOG
            entry = next((entry for entry in CATALOG if normalized(value) in [normalized(alias) for alias in entry[1].split('|')]), None)
            names = entry[2].lower().split('|') if entry else [value.lower()]
            count = 0
            for session in AudioUtilities.GetAllSessions():
                if session.Process and session.Process.name().lower() in names:
                    session.SimpleAudioVolume.SetMute(1, None)
                    count += 1
            return f'Wyciszono {count} sesji audio.' if count else 'Brak aktywnej sesji audio tej aplikacji.'
        volume = AudioUtilities.GetSpeakers().EndpointVolume
        amount = int(value)
        if not 0 <= amount <= 100:
            raise ValueError('Głośność i zmiana: 0–100 procent.')
        current = volume.GetMasterVolumeLevelScalar() * 100
        target = amount if kind == 'volume' else max(0, min(100, current + (amount if kind == 'volume_up' else -amount)))
        volume.SetMasterVolumeLevelScalar(target / 100, None)
        return f'Głośność na {target:.0f} procent.'
    finally:
        comtypes.CoUninitialize()


def window_screenshot(hwnd=None):
    from PIL import ImageGrab
    require_windows()
    rect = wintypes.RECT()
    user32 = ctypes.windll.user32
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    if not user32.GetWindowRect(hwnd or foreground(), ctypes.byref(rect)):
        raise OSError('Nie odczytano granic aktywnego okna.')
    return ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom), all_screens=True)


def run_control(action, confirmed=False):
    require_windows()
    kind, value = action['kind'], action['value']
    risky = {'hibernate', 'logout', 'close_window', 'wifi', 'connect_wifi', 'disconnect_wifi', 'hotkey', 'dictate', 'click'}
    if kind in risky and not confirmed:
        raise PermissionError('Najpierw potwierdź tę akcję.')
    if kind in {'volume', 'volume_up', 'volume_down', 'mute_app', 'mute_mic', 'unmute_mic'}:
        return audio_action(kind, value)
    if kind in {'hibernate', 'logout'}:
        subprocess.run(['shutdown.exe', '/h' if kind == 'hibernate' else '/l'], shell=False, check=True)
        return 'Hibernuję system.' if kind == 'hibernate' else 'Wylogowuję użytkownika.'
    if kind == 'power_plan':
        aliases = {'oszczedzanie': 'SCHEME_MAX', 'saver': 'SCHEME_MAX', 'zrownowazony': 'SCHEME_BALANCED', 'balanced': 'SCHEME_BALANCED', 'wysoka wydajnosc': 'SCHEME_MIN', 'performance': 'SCHEME_MIN'}
        subprocess.run(['powercfg.exe', '/setactive', aliases[normalized(value)]], shell=False, check=True)
        return 'Zmieniono plan zasilania. Na niektórych komputerach dostępny jest tylko plan zrównoważony.'
    if kind == 'brightness':
        import screen_brightness_control as sbc
        if not 0 <= int(value) <= 100:
            raise ValueError('Jasność: 0–100 procent.')
        sbc.set_brightness(int(value))
        return f'Jasność ustawiona na {value} procent.'
    settings = {'night': 'ms-settings:nightlight', 'display_settings': 'ms-settings:display', 'audio_output': 'ms-settings:sound', 'bluetooth': 'ms-settings:bluetooth', 'airplane': 'ms-settings:network-airplanemode', 'eject': 'ms-settings:connecteddevices'}
    if kind in settings:
        os.startfile(settings[kind])
        return 'Otwieram odpowiednie ustawienia Windows. Zmień opcję ręcznie; ta wersja nie przełącza jej automatycznie.'
    if kind in {'wifi', 'connect_wifi', 'disconnect_wifi'}:
        if kind == 'wifi':
            enabled = normalized(value) in {'on', 'wlacz'}
            subprocess.run(['netsh.exe', 'interface', 'set', 'interface', 'name=Wi-Fi', 'admin=enabled' if enabled else 'admin=disabled'], shell=False, check=True, capture_output=True)
            return 'Zmieniono stan interfejsu Wi-Fi. Wymaga administratora i interfejsu o nazwie Wi-Fi.'
        args = ['netsh.exe', 'wlan', 'disconnect'] if kind == 'disconnect_wifi' else ['netsh.exe', 'wlan', 'connect', 'name=' + value]
        subprocess.run(args, shell=False, check=True, capture_output=True)
        return 'Wysłano polecenie sieci Wi-Fi; sprawdź status połączenia. Łączenie korzysta tylko z istniejącego profilu.'
    if kind in {'clipboard_read', 'clipboard_write', 'clipboard_clear'}:
        import pyperclip
        if kind == 'clipboard_read':
            return pyperclip.paste()[:20000] or 'Nie widzę żadnego tekstu w schowku.'
        pyperclip.copy(value if kind == 'clipboard_write' else '')
        return 'Wkleiłem wynik do schowka.' if kind == 'clipboard_write' else 'Wyczyściłem schowek.'
    if kind == 'active_title':
        return window_title(action.get('hwnd')) or 'Aktywne okno nie ma tytułu.'
    if kind == 'ocr':
        import pytesseract
        from PIL import ImageGrab
        text = pytesseract.image_to_string(ImageGrab.grab(all_screens=True), lang='pol+eng')
        return text[:20000].strip() or 'Nie znaleziono tekstu. OCR wymaga Tesseract i języków pol+eng.'
    if kind in {'screenshot_window', 'screenshot_clipboard'}:
        if kind == 'screenshot_window':
            file = Path(value).expanduser().resolve() if value else HOME / 'Zrzuty' / time.strftime('okno_%Y%m%d_%H%M%S.png')
            if file.suffix.lower() != '.png':
                raise ValueError('Podaj plik .png.')
            file.parent.mkdir(parents=True, exist_ok=True)
            file = safe_destination(file)
            window_screenshot(action.get('hwnd')).save(file, 'PNG')
            return 'Zrzut ekranu zapisany: ' + str(file)
        import win32clipboard
        from PIL import ImageGrab
        stream = io.BytesIO()
        ImageGrab.grab(all_screens=True).convert('RGB').save(stream, 'BMP')
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, stream.getvalue()[14:])
        finally:
            win32clipboard.CloseClipboard()
        return 'Zrzut ekranu w schowku.'
    if kind in {'maximize', 'pin', 'unpin', 'close_window'}:
        hwnd = action.get('hwnd') or foreground()
        user32 = ctypes.windll.user32
        if not hwnd or not window_title(hwnd):
            raise ValueError('Nie znaleziono aktywnego okna.')
        if kind == 'maximize':
            user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
            user32.ShowWindow(hwnd, 3)
        elif kind == 'close_window':
            user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            user32.PostMessageW(hwnd, 0x0010, 0, 0)
        else:
            user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
            user32.SetWindowPos(hwnd, wintypes.HWND(-1 if kind == 'pin' else -2), 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
        return {'maximize': 'Maksymalizuję.', 'close_window': 'Wysłano prośbę zamknięcia okna. Program może poprosić o zapisanie zmian.', 'pin': 'Przypinam na wierzchu.', 'unpin': 'Odpinam okno.'}[kind]
    import pyautogui as keys
    # PyAutoGUI emergency failsafe stays enabled: move pointer to top-left to abort.
    combos = {'minimize': ['win', 'd'], 'switch_window': ['alt', 'tab'], 'snap_left': ['win', 'left'], 'snap_right': ['win', 'right'], 'new_desktop': ['win', 'ctrl', 'd'], 'next_desktop': ['win', 'ctrl', 'right'], 'previous_desktop': ['win', 'ctrl', 'left']}
    if kind in combos:
        keys.hotkey(*combos[kind])
        return 'Gotowe. Wysłano skrót do Windows.'
    if kind == 'snap_pair':
        keys.hotkey('win', 'left')
        keys.hotkey('alt', 'tab')
        keys.hotkey('win', 'right')
        return 'Wysłano skróty układania dwóch ostatnich okien. Sprawdź układ.'
    if kind == 'hotkey':
        combo = [key.strip().lower() for key in value.split('+')]
        if not 1 <= len(combo) <= 5 or any(key not in keys.KEYBOARD_KEYS for key in combo):
            raise ValueError('Nieprawidłowe klawisze. Przykład: skrót ctrl+c.')
        keys.hotkey(*combo)
    elif kind == 'dictate':
        import pyperclip
        previous = pyperclip.paste()
        pyperclip.copy(value)
        keys.hotkey('ctrl', 'v')
        time.sleep(0.2)
        pyperclip.copy(previous)
    elif kind == 'click':
        x, y = map(int, value.split())
        if not keys.onScreen(x, y):
            raise ValueError('Współrzędne poza głównym ekranem.')
        keys.click(x, y)
    elif kind in {'media_pause', 'media_next', 'media_previous'}:
        keys.press({'media_pause': 'playpause', 'media_next': 'nexttrack', 'media_previous': 'prevtrack'}[kind])
    else:
        raise ValueError('Nieznana kontrolka systemu.')
    return 'Gotowe.'

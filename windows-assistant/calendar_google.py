"""Native desktop OAuth. Credentials are user-local, never shipped in the ZIP."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import threading
from tools import HOME

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
LOCK = threading.Lock()

def service(interactive=False):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    token = HOME / 'google_token.json'
    credentials_file = HOME / 'google_credentials.json'
    with LOCK:
        credentials = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            if not interactive:
                raise ValueError('Najpierw kliknij „Połącz Google” i zaloguj się w przeglądarce.')
            if not credentials_file.exists():
                raise ValueError('Brakuje danych aplikacji OAuth typu Desktop. Wybierz własny plik JSON z Google Cloud; instrukcja jest w README.')
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_file), SCOPES)
            credentials = flow.run_local_server(host='127.0.0.1', port=0, open_browser=True, timeout_seconds=180)
        HOME.mkdir(parents=True, exist_ok=True)
        token.write_text(credentials.to_json(), encoding='utf-8')
    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)


def connect(credentials_file):
    source = Path(credentials_file)
    data = json.loads(source.read_text('utf-8'))
    if not isinstance(data.get('installed'), dict):
        raise ValueError('Wybierz klienta OAuth typu Desktop, nie Web.')
    HOME.mkdir(parents=True, exist_ok=True)
    (HOME / 'google_credentials.json').write_text(json.dumps(data), encoding='utf-8')
    service(interactive=True)
    return 'Kalendarz Google połączony. Dane logowania pozostają na tym komputerze.'


def disconnect():
    for name in ('google_token.json', 'google_credentials.json'):
        (HOME / name).unlink(missing_ok=True)
    return 'Usunięto lokalne logowanie. Cofnij dostęp aplikacji również w ustawieniach konta Google, jeśli chcesz odwołać zgodę.'


def events():
    now = datetime.now(timezone.utc).isoformat()
    items = service().events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute().get('items', [])
    return '\n'.join(f"{item['start'].get('dateTime', item['start'].get('date'))} · {item.get('summary', '(bez tytułu)')}" for item in items) or 'Brak nadchodzących wydarzeń.'


def add_event(value):
    # calendar Tytuł | 2026-11-21 07:00 | 30
    title, separator, timing = value.partition(' | ')
    if not separator:
        raise ValueError('Użyj: kalendarz Spotkanie | 2026-11-21 07:00 | 30 (czas lokalny, minuty).')
    start_value, _, duration_value = timing.partition(' | ')
    start = datetime.strptime(start_value, '%Y-%m-%d %H:%M').astimezone()
    duration = int(duration_value or '30')
    if not title.strip() or not 1 <= duration <= 1440:
        raise ValueError('Podaj tytuł i długość 1–1440 minut.')
    body = {'summary': title, 'start': {'dateTime': start.isoformat()}, 'end': {'dateTime': (start + timedelta(minutes=duration)).isoformat()}, 'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 15}]}}
    event = service().events().insert(calendarId='primary', body=body).execute()
    return 'Dodano do Kalendarza Google: ' + event.get('htmlLink', title)

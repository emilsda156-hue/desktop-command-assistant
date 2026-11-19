"""Lokalny asystent Windows. Python 3.11+, tkinter i yt-dlp."""
import re
import subprocess
import threading
import webbrowser
from urllib.parse import quote


def classify(command):
    text = command.strip().lower()
    if 'kalkulator' in text:
        return 'calculator', ''
    if 'notatnik' in text:
        return 'notepad', ''
    if re.search(r'przegl[aą]dark', text):
        return 'browser', ''
    if re.search(r'youtube|\byt\b', text):
        if 'najnowsz' in text:
            handle = re.search(r'@[\w.\-]+', command)
            return 'latest', handle.group(0) if handle else ''
        query = re.sub(r'^(otw[oó]rz|odpal|uruchom|włącz)\s+', '', text)
        return 'youtube', re.sub(r'^(youtube|yt)\s*', '', query)
    return 'unknown', ''


def execute(command):
    kind, value = classify(command)
    if kind == 'calculator':
        subprocess.Popen(['calc.exe'], shell=False)
        return 'Uruchomiono kalkulator.'
    if kind == 'notepad':
        subprocess.Popen(['notepad.exe'], shell=False)
        return 'Uruchomiono Notatnik.'
    if kind == 'browser':
        webbrowser.open('https://www.google.com')
        return 'Otwarto domyślną przeglądarkę.'
    if kind == 'youtube':
        webbrowser.open('https://www.youtube.com/results?search_query=' + quote(value) if value else 'https://www.youtube.com')
        return 'Otwarto YouTube.'
    if kind == 'latest':
        if not value:
            return 'Podaj identyfikator kanału, np. odpal yt najnowszy odcinek @mkbhd.'
        from yt_dlp import YoutubeDL
        options = {'quiet': True, 'extract_flat': True, 'playlistend': 1, 'skip_download': True, 'socket_timeout': 20}
        with YoutubeDL(options) as ydl:
            data = ydl.extract_info('https://www.youtube.com/' + value + '/videos', download=False)
        entries = (data or {}).get('entries') or []
        video = next((entry for entry in entries if entry), None)
        if not video or not re.fullmatch(r'[A-Za-z0-9_-]{11}', video.get('id', '')):
            return 'Nie znaleziono filmu. Sprawdź identyfikator kanału i połączenie z internetem.'
        webbrowser.open('https://www.youtube.com/watch?v=' + video['id'])
        return 'Otwarto najnowszy film z zakładki Filmy: ' + video.get('title', value)
    return 'Obsługuję: kalkulator, notatnik, przeglądarkę, YouTube i najnowszy film @kanału.'


def main():
    import tkinter as tk
    from tkinter import scrolledtext

    root = tk.Tk()
    root.title('Orbit — asystent Windows')
    root.geometry('720x540')
    root.minsize(520, 400)
    root.configure(bg='#17191c')
    tk.Label(root, text='ORBIT', font=('Segoe UI', 14, 'bold'), bg='#17191c', fg='#93edc6').pack(anchor='w', padx=28, pady=(24, 6))
    tk.Label(root, text='Co dziś robimy?', font=('Segoe UI', 26), bg='#17191c', fg='#f1f2f4').pack(anchor='w', padx=28, pady=(4, 16))
    history = scrolledtext.ScrolledText(root, font=('Segoe UI', 11), bg='#22252a', fg='#f1f2f4', relief='flat', wrap='word', state='disabled')
    history.pack(fill='both', expand=True, padx=28, pady=8)

    def append(message):
        history.configure(state='normal')
        history.insert('end', message + '\n\n')
        history.see('end')
        history.configure(state='disabled')

    append('Gotowy. Wpisz np. „odpal kalkulator” lub „odpal yt najnowszy odcinek @mkbhd”.')
    row = tk.Frame(root, bg='#17191c')
    row.pack(fill='x', padx=28, pady=20)
    entry = tk.Entry(row, font=('Segoe UI', 12), bg='#22252a', fg='#f1f2f4', insertbackground='#93edc6', relief='flat')
    entry.pack(side='left', fill='x', expand=True, ipady=12)
    busy = False

    def submit(event=None):
        nonlocal busy
        command = entry.get().strip()
        if not command or busy:
            return
        busy = True
        entry.delete(0, 'end')
        append('Ty: ' + command)
        send.configure(state='disabled')
        def finish(result):
            nonlocal busy
            append('Orbit: ' + result)
            busy = False
            send.configure(state='normal')
        def worker():
            try:
                result = execute(command)
            except ImportError:
                result = 'Brakuje yt-dlp. Uruchom ponownie instaluj.bat.'
            except Exception as error:
                result = 'Nie udało się wykonać polecenia: ' + str(error)
            root.after(0, lambda: finish(result))
        threading.Thread(target=worker, daemon=True).start()
    send = tk.Button(row, text='Wyślij →', command=submit, bg='#93edc6', fg='#17191c', relief='flat', font=('Segoe UI', 11), padx=18, pady=10)
    send.pack(side='right', padx=(10, 0))
    entry.bind('<Return>', submit)
    entry.focus_set()
    root.mainloop()


if __name__ == '__main__':
    main()
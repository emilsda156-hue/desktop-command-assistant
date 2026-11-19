"""Push-to-talk online recognition. Called only after explicit UI consent."""
LANGUAGES = {'Polski': 'pl-PL', 'English': 'en-US'}

def recognize(language):
    import speech_recognition as sr
    if language not in LANGUAGES.values():
        raise ValueError('Wybierz pl-PL lub en-US.')
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio = recognizer.listen(source, timeout=6, phrase_time_limit=12)
    try:
        return recognizer.recognize_google(audio, language=language)
    except sr.UnknownValueError as error:
        raise ValueError('Nie rozpoznano mowy. Spróbuj ponownie lub wpisz polecenie.') from error
    except sr.RequestError as error:
        raise RuntimeError('Rozpoznawanie online niedostępne. Sprawdź internet lub wpisz polecenie.') from error

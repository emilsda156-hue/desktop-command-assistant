# Orbit — asystent Windows

## Instalacja
1. Zainstaluj Python 3.11 lub nowszy z https://www.python.org/downloads/windows/ z Python Launcher i tkinter.
2. Rozpakuj wszystkie pliki ZIP do stałego folderu, np. Dokumenty/Orbit. Nie uruchamiaj ich wewnątrz ZIP.
3. Kliknij dwa razy `instaluj.bat`. Pobiera bibliotekę yt-dlp i tworzy skrót na pulpicie.
4. Uruchom skrót Orbit lub `uruchom.bat`.

## Polecenia
- `odpal kalkulator`
- `otwórz notatnik`
- `uruchom przeglądarkę`
- `odpal yt`
- `odpal yt muzyka do pracy`
- `odpal yt najnowszy odcinek @mkbhd`

Dla najnowszego filmu użyj dokładnego @identyfikatora kanału widocznego na YouTube. Asystent otwiera pierwszy film z domyślnie posortowanej zakładki /videos; Shorts i transmisje nie są uwzględniane. Internet i działający YouTube są wymagane. Filmy nie są pobierane. YouTube może zablokować odczyt lub wymagać logowania — błąd pojawi się w oknie; asystent nie obchodzi ograniczeń serwisu.

## Zakres i bezpieczeństwo
To lokalny asystent rozpoznający określone polskie polecenia, nie uniwersalny model AI. Nie wymaga klucza API, konta ani administratora. Wykonuje tylko wymienione akcje; nigdy nie wykonuje wpisanego kodu PowerShell ani dowolnych poleceń systemowych. Nie działa głosowo ani w tle i nie startuje automatycznie z Windowsem. Historia znika po zamknięciu. Aby usunąć program, usuń jego folder i skrót.

Panel internetowy jest podglądem — przeglądarka nie ma dostępu do programów Windows. Kontrola komputera działa tylko w uruchomionym lokalnie programie.
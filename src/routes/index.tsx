import { createFileRoute } from '@tanstack/react-router';
import { useState, type FormEvent } from 'react';
import { ArrowUp, ArrowUpRight, AudioLines, Box, Calculator, Check, ChevronRight, Command, Download, ExternalLink, FileText, Globe, History, Info, Laptop, MessageSquare, Monitor, ShieldCheck, Sparkles, Terminal, Youtube } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { parseCommand } from '@/lib/commands';

export const Route = createFileRoute('/')({
  head: () => ({ meta: [
    { title: 'Orbit — Asystent poleceń na Windows' },
    { name: 'description', content: 'Orbit: otwieraj kalkulator, Notatnik i najnowsze filmy YouTube za pomocą polskich poleceń. Pobierz lokalnego asystenta na Windows.' },
    { property: 'og:title', content: 'Orbit — Asystent poleceń na Windows' },
    { property: 'og:description', content: 'Twój komputer, Twoje polecenia. Lokalny asystent na Windows z obsługą YouTube i aplikacji.' },
    { property: 'og:type', content: 'website' },
    { name: 'twitter:card', content: 'summary_large_image' },
  ] }),
  component: Index,
});

type View = 'assistant' | 'history' | 'commands';
type Message = { role: 'user' | 'assistant'; text: string; time: string };
const actions = [
  { icon: Youtube, title: 'Otwórz YouTube', subtitle: 'Twój moment na przerwę', command: 'odpal yt' },
  { icon: Calculator, title: 'Uruchom kalkulator', subtitle: 'Wszystko się zgadza', command: 'odpal kalkulator' },
  { icon: FileText, title: 'Otwórz notatnik', subtitle: 'Zapisz to, co ważne', command: 'otwórz notatnik' },
  { icon: Globe, title: 'Otwórz przeglądarkę', subtitle: 'Świat na wyciągnięcie ręki', command: 'uruchom przeglądarkę' },
];

function Index() {
  const [view, setView] = useState<View>('assistant');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [installOpen, setInstallOpen] = useState(false);
  const [aboutOpen, setAboutOpen] = useState(false);

  function run(command: string) {
    if (!command.trim()) return;
    const action = parseCommand(command);
    let response: string;
    if (action.type === 'youtube') {
      const url = action.query ? `https://www.youtube.com/results?search_query=${encodeURIComponent(action.query)}` : 'https://www.youtube.com';
      const opened = window.open(url, '_blank', 'noopener,noreferrer');
      void opened;
      response = 'Wysłano polecenie otwarcia YouTube do przeglądarki. Jeśli nowa karta się nie pojawiła, zezwól na wyskakujące okna.';
    } else if (action.type === 'browser') {
      window.open('https://www.google.com', '_blank', 'noopener,noreferrer');
      response = 'Wysłano polecenie otwarcia Google w nowej karcie.';
    } else if (action.type === 'calculator' || action.type === 'notepad') {
      response = `${action.label} jest dostępny w lokalnym programie Orbit. Ten panel internetowy nie ma dostępu do aplikacji na Twoim komputerze. Pobierz wersję na Windows, aby wykonać to polecenie.`;
    } else if (action.type === 'latest') {
      response = action.query ? `W lokalnym programie otworzę najnowszy film kanału ${action.query}. Pobierz Orbit na Windows — panel internetowy nie odczytuje listy filmów.` : 'Podaj @identyfikator kanału, np. „odpal yt najnowszy odcinek @mkbhd”. Najnowszy film otwiera lokalna wersja Orbit na Windows.';
    } else {
      response = 'Nie rozpoznaję tego polecenia. Mogę otworzyć YouTube, przeglądarkę, kalkulator lub notatnik. Najnowszy film: „odpal yt najnowszy odcinek @mkbhd”.';
    }
    const time = new Date().toLocaleTimeString('pl-PL', { hour: '2-digit', minute: '2-digit' });
    setMessages(previous => [...previous, { role: 'user', text: command, time }, { role: 'assistant', text: response, time }]);
    setInput('');
    setView('assistant');
  }

  function submit(event: FormEvent) { event.preventDefault(); run(input); }

  return <div className="app-layout">
    <aside className="sidebar">
      <div className="brand"><AudioLines className="brand-symbol" size={32} strokeWidth={2.4} />orbit<span className="text-primary text-xs self-start mt-1">®</span></div>
      <nav className="nav-list" aria-label="Menu główne">
        <Button variant="ghost" className="nav-item" data-active={view === 'assistant'} onClick={() => setView('assistant')}><MessageSquare />Asystent</Button>
        <Button variant="ghost" className="nav-item" data-active={view === 'history'} onClick={() => setView('history')}><History />Historia poleceń</Button>
        <Button variant="ghost" className="nav-item" data-active={view === 'commands'} onClick={() => setView('commands')}><Command />Polecenia</Button>
      </nav>
      <div className="sidebar-label">Twój komputer</div>
      <Button variant="ghost" className="nav-item sidebar-extra justify-start text-xs text-muted-foreground" onClick={() => setInstallOpen(true)}><Monitor />Połącz z Windowsem<ChevronRight className="ml-auto" /></Button>
      <div className="sidebar-footer">
        <div className="local-badge"><div className="flex items-center gap-2 text-xs"><ShieldCheck className="text-primary" size={16} />Lokalnie. Prywatnie.</div><p className="text-muted-foreground text-[10px] leading-5 mt-2">Twoje polecenia zostają<br />na Twoim komputerze.*</p></div>
        <Button variant="ghost" className="mt-5 text-muted-foreground text-[11px] w-full justify-start" onClick={() => setAboutOpen(true)}><Info />O projekcie<ArrowUpRight className="ml-auto" /></Button>
        <div className="px-3 mt-3 text-[9px] text-muted-foreground font-mono">ORBIT / WINDOWS EDITION</div>
      </div>
    </aside>
    <main className="min-w-0">
      <header className="workspace-header"><div className="flex items-center gap-3 text-xs"><span className="text-muted-foreground">Przestrzeń robocza</span><ChevronRight size={12} /><span>{view === 'assistant' ? 'Asystent' : view === 'history' ? 'Historia poleceń' : 'Polecenia'}</span></div><div className="flex items-center gap-5"><span className="header-status text-[10px] text-muted-foreground flex items-center gap-2"><span className="dot" />Podgląd przeglądarkowy</span><Button variant="outline" size="sm" onClick={() => setInstallOpen(true)}><Download />Pobierz na Windows</Button></div></header>
      <div className="workspace-content">
        <div className="flex items-center justify-between"><div><div className="eyebrow">Twój osobisty asystent</div><h1 className="text-[22px] font-semibold mt-2">Mniej klikania. Więcej działania<span className="text-primary">.</span></h1></div><span className="hidden sm:flex text-[9px] text-muted-foreground font-mono items-center gap-2"><Box size={13} />v1.0</span></div>
        {view === 'assistant' ? <div className="workspace-columns">
          <section className="min-w-0">
            <div className="assistant-space">{messages.length === 0 ? <><div className="signal-mark" aria-label="Symbol asystenta Orbit"><div className="signal-bars"><i /><i /><i /><i /><i /></div></div><div className="text-[9px] text-primary font-mono flex items-center gap-2 mb-3"><span className="dot" />GOTOWY NA POLECENIE</div><h2>Hej, co dziś robimy?</h2><p>Małe sprawy, załatwione od ręki.<br />Od czego zaczynamy?</p></> : <div className="message-list" aria-live="polite">{messages.slice(-8).map((message, index) => <div key={index} className={`chat-message ${message.role === 'user' ? 'user' : ''}`}><div className="text-[9px] text-muted-foreground mb-1">{message.role === 'user' ? 'TY' : 'ORBIT'} · {message.time}</div>{message.text}</div>)}</div>}</div>
            <div className="flex justify-between items-center mb-3"><span className="eyebrow">Na dobry początek</span><Sparkles size={13} className="text-muted-foreground" /></div>
            <div className="quick-grid">{actions.map(action => <Button key={action.title} variant="outline" className="quick-item" onClick={() => run(action.command)}><action.icon /><div><span>{action.title}</span><small>{action.subtitle}</small></div><ArrowUpRight className="ml-auto opacity-40" /></Button>)}</div>
            <form className="command-composer" onSubmit={submit}><Terminal size={17} className="text-muted-foreground shrink-0" /><input aria-label="Twoje polecenie" value={input} onChange={event => setInput(event.target.value)} placeholder="Wpisz polecenie…" autoComplete="off" /><Button type="submit" size="icon" aria-label="Wyślij polecenie" title="Wyślij polecenie" disabled={!input.trim()}><ArrowUp /></Button></form>
            <div className="flex items-center justify-between text-[9px] text-muted-foreground mt-3 gap-2"><span>Wersja lokalna wykonuje polecenia na komputerze.</span><span className="font-mono shrink-0">PL / POLSKI</span></div>
          </section>
          <aside className="right-panel">
            <div className="panel-section"><h3 className="panel-title"><Laptop size={15} />Twoje środowisko</h3><div className="connection-row"><span className="text-muted-foreground">System docelowy</span><span className="flex gap-2 items-center"><Monitor size={12} />Windows</span></div><div className="connection-row"><span className="text-muted-foreground">Tryb</span><span className="soft-tag">Podgląd</span></div><div className="connection-row"><span className="text-muted-foreground">Program lokalny</span><span className="text-muted-foreground">Niepołączony</span></div><Button variant="ghost" className="text-primary text-[10px] h-8 p-0" onClick={() => setInstallOpen(true)}>Zainstaluj asystenta<ArrowUpRight /></Button></div>
            <div className="panel-section"><h3 className="panel-title mb-4">Do Twojej dyspozycji</h3><div className="capability"><Check />Aplikacje Windows</div><div className="capability"><Check />YouTube i najnowsze filmy</div><div className="capability"><Check />Strony internetowe</div><div className="capability"><Check />Polecenia po polsku</div></div>
            <div className="panel-section border-b-0"><h3 className="panel-title"><AudioLines size={15} className="text-primary" />Jedno polecenie, gotowe.</h3><p className="text-[11px] leading-6 text-muted-foreground">Na przykład coś do obejrzenia:</p><Button variant="ghost" className="h-auto w-full whitespace-normal text-left justify-start p-0 mt-3 text-[11px] leading-6 text-foreground" onClick={() => { setInput('odpal yt najnowszy odcinek @mkbhd'); }}>„Odpal yt najnowszy odcinek @mkbhd”<ArrowUpRight className="shrink-0" /></Button><span className="text-[9px] text-muted-foreground block mt-4">Dostępne w wersji na Windows</span></div>
          </aside>
        </div> : view === 'history' ? <section className="content-page"><div className="flex justify-between items-center"><h2>Historia poleceń</h2><Button variant="outline" size="sm" disabled={!messages.length} onClick={() => setMessages([])}>Wyczyść historię</Button></div>{messages.length ? messages.map((message, index) => <div className="chat-message" key={index}><div className="text-muted-foreground text-[10px]">{message.role === 'user' ? 'Ty' : 'Orbit'} · {message.time}</div>{message.text}</div>) : <p>Nie ma jeszcze żadnych poleceń.</p>}<p className="mt-6">Historia tej sesji znika po odświeżeniu strony.</p></section> : <section className="content-page"><h2>Polecenia</h2><p>Dostępne w lokalnej wersji na Windows.</p>{[...actions, { icon: Youtube, title: 'Najnowszy film kanału', subtitle: 'Podaj dokładny @identyfikator z YouTube', command: 'odpal yt najnowszy odcinek @mkbhd' }].map(action => <div key={action.title} className="installation-step"><action.icon size={20} className="text-primary shrink-0" /><div className="flex-1 min-w-0"><h3 className="text-sm">{action.title}</h3><p className="font-mono break-words mt-1">{action.command}</p></div><Button variant="ghost" size="icon" title="Wstaw polecenie" aria-label={`Wstaw: ${action.title}`} onClick={() => { setInput(action.command); setView('assistant'); }}><ArrowUpRight /></Button></div>)}</section>}
        <footer className="workspace-footer"><span className="flex items-center gap-2"><ShieldCheck size={12} />Bez konta. Bez kluczy API. Po Twojemu.</span><span>Orbit — Twój komputer, Twoje polecenia.</span></footer>
      </div>
    </main>
    <Dialog open={installOpen} onOpenChange={setInstallOpen}><DialogContent><DialogTitle>Orbit na Twoim Windowsie</DialogTitle><DialogDescription>Do uruchamiania aplikacji potrzebujesz programu lokalnego. Panel internetowy nie steruje komputerem.</DialogDescription><div>{[
      ['Zainstaluj Python 3.11 lub nowszy', 'Pobierz go z python.org. W instalatorze uwzględnij Python Launcher i tkinter.'],
      ['Pobierz i rozpakuj Orbit', 'Zapisz cały folder w stałym miejscu na komputerze.'],
      ['Uruchom instaluj.bat', 'Instalacja pobierze yt-dlp i utworzy skrót Orbit na pulpicie.'],
      ['Otwórz Orbit i wpisz polecenie', 'Na przykład: odpal kalkulator. Nie są potrzebne uprawnienia administratora.'],
    ].map(([title, description], index) => <div className="installation-step" key={title}><span className="step-number">0{index + 1}</span><div><h3 className="text-xs font-semibold">{title}</h3><p className="text-[11px] text-muted-foreground leading-5 mt-1">{description}</p></div></div>)}</div><Button asChild><a href="/downloads/orbit-windows.zip" download><Download />Pobierz Orbit na Windows · ZIP</a></Button><Button variant="link" asChild><a href="https://www.python.org/downloads/windows/" target="_blank" rel="noopener noreferrer">Pobierz Python<ExternalLink /></a></Button><p className="text-[10px] leading-5 text-muted-foreground">Kod źródłowy, nie gotowy plik EXE. Polecenia tekstowe; bez obsługi głosu. Najnowsze filmy wymagają internetu i mogą być niedostępne przy ograniczeniach YouTube.</p></DialogContent></Dialog>
    <Dialog open={aboutOpen} onOpenChange={setAboutOpen}><DialogContent><DialogTitle>O projekcie Orbit</DialogTitle><DialogDescription>Lokalny asystent określonych poleceń na Windows. Nie jest uniwersalną sztuczną inteligencją i nie wykonuje dowolnego kodu systemowego.</DialogDescription><p className="text-sm text-muted-foreground leading-7">*Historia lokalnego programu pozostaje w pamięci komputera i znika po zamknięciu. Otwieranie stron oraz odczyt YouTube wysyła zapytania do tych serwisów. Panel internetowy jest niezależnym podglądem, bez połączenia z lokalnym programem.</p></DialogContent></Dialog>
  </div>;
}

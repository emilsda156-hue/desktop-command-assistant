export type Command = { type: 'calculator' | 'notepad' | 'browser' | 'youtube' | 'latest' | 'unknown'; label: string; query?: string };

export function parseCommand(input: string): Command {
  const text = input.trim().toLocaleLowerCase('pl');
  if (/kalkulator/.test(text)) return { type: 'calculator', label: 'Kalkulator' };
  if (/notatnik/.test(text)) return { type: 'notepad', label: 'Notatnik' };
  if (/przegl[aą]dark/.test(text)) return { type: 'browser', label: 'Przeglądarka' };
  if (/(youtube|\byt\b)/.test(text)) {
    const handle = input.match(/@[\w.\-]+/u)?.[0];
    if (/najnowsz/.test(text)) return { type: 'latest', label: 'Najnowszy odcinek', ...(handle ? { query: handle } : {}) };
    const query = input.replace(/^(?:otw[oó]rz|odpal|uruchom|włącz)\s+/i, '').replace(/^(?:youtube|yt)\s*/i, '').trim();
    return { type: 'youtube', label: 'YouTube', query };
  }
  return { type: 'unknown', label: 'Nieznane polecenie' };
}
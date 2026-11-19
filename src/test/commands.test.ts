import { describe, expect, it } from 'vitest';
import { parseCommand } from '@/lib/commands';

describe('Polecenia asystenta', () => {
  it('rozpoznaje uruchomienie kalkulatora', () => {
    expect(parseCommand('odpal kalkulator').type).toBe('calculator');
  });
  it('rozpoznaje najnowszy film wskazanego youtubera', () => {
    expect(parseCommand('odpal yt najnowszy odcinek @mkbhd')).toEqual({ type: 'latest', label: 'Najnowszy odcinek', query: '@mkbhd' });
  });
  it('nie wykonuje dowolnego kodu jako polecenia', () => {
    expect(parseCommand('powershell Remove-Item C:').type).toBe('unknown');
  });
});
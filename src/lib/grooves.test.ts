import { describe, expect, it } from 'vitest';
import {
  GROOVES,
  beatMs,
  getGroove,
  isSwingable,
  meanAbsOffsetMs,
  noteTimings,
  positions,
} from './grooves';

describe('grooves', () => {
  it('garde des positions croissantes dans [0, 1[ pour tout swing', () => {
    for (const groove of GROOVES) {
      expect(groove.grid.length).toBe(groove.target.length);
      for (const swing of [0, 0.5, 1]) {
        const p = positions(groove, swing);
        expect(p[0]).toBe(0);
        for (let i = 1; i < p.length; i++) expect(p[i]).toBeGreaterThan(p[i - 1]);
        expect(p[p.length - 1]).toBeLessThan(1);
      }
    }
  });

  it('interpole entre la grille et la cible', () => {
    const samba = getGroove('samba');
    expect(positions(samba, 0)).toEqual([0, 0.25, 0.5, 0.75]);
    expect(positions(samba, 1)).toEqual([0, 0.27, 0.46, 0.71]);
    expect(positions(samba, 0.5)[2]).toBeCloseTo(0.48);
    expect(positions(samba, 2)).toEqual(positions(samba, 1));
    expect(positions(samba, -1)).toEqual(positions(samba, 0));
  });

  it('place la samba dans les fourchettes mesurées', () => {
    const [, second, third, fourth] = positions(getGroove('samba'), 1);
    expect(second).toBeGreaterThanOrEqual(0.25);
    expect(second).toBeLessThanOrEqual(0.29);
    expect(third).toBeGreaterThanOrEqual(0.42);
    expect(third).toBeLessThanOrEqual(0.5);
    expect(fourth).toBeGreaterThanOrEqual(0.67);
    expect(fourth).toBeLessThanOrEqual(0.75);
  });

  it('convertit le BPM en millisecondes', () => {
    expect(beatMs(120)).toBe(500);
    const t = noteTimings(getGroove('samba'), 1, 120);
    expect(t[1].ms).toBeCloseTo(135);
    expect(t[1].offsetMs).toBeCloseTo(10); // en retard
    expect(t[2].offsetMs).toBeCloseTo(-20); // en avance
    expect(t[3].offsetMs).toBeCloseTo(-20);
  });

  it('donne un écart moyen de 1/40 du temps pour la samba', () => {
    for (const bpm of [60, 90, 140]) {
      const mean = meanAbsOffsetMs(noteTimings(getGroove('samba'), 1, bpm));
      expect(mean).toBeCloseTo(beatMs(bpm) / 40);
    }
  });

  it('sait quels grooves réagissent au curseur de swing', () => {
    expect(isSwingable(getGroove('samba'))).toBe(true);
    expect(isSwingable(getGroove('jazz'))).toBe(true);
    expect(isSwingable(getGroove('mpc'))).toBe(true);
    expect(isSwingable(getGroove('straight'))).toBe(false);
    expect(isSwingable(getGroove('garfinho'))).toBe(false);
    expect(isSwingable(getGroove('tercina'))).toBe(false);
  });
});

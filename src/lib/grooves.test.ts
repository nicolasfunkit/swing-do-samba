import { describe, expect, it } from 'vitest';
import {
  GROOVES,
  beatMs,
  getGroove,
  isSwingable,
  jazzSwingRatio,
  meanAbsOffsetMs,
  noteTimings,
  positions,
  positionsFromDurations,
} from './grooves';

describe('grooves', () => {
  it('garde des positions croissantes dans [0, 1[ pour tout swing', () => {
    for (const groove of GROOVES) {
      expect(groove.grid.length).toBe(groove.target.length);
      for (const swing of [0, 0.5, 1]) {
        for (const bpm of [60, 160, 300]) {
          const p = positions(groove, swing, bpm);
          expect(p[0]).toBe(0);
          for (let i = 1; i < p.length; i++) expect(p[i]).toBeGreaterThan(p[i - 1]);
          expect(p[p.length - 1]).toBeLessThan(1);
        }
      }
    }
  });

  it('interpole entre la grille et la cible', () => {
    const samba = getGroove('samba');
    expect(positions(samba, 0, 90)).toEqual([0, 0.25, 0.5, 0.75]);
    expect(positions(samba, 1, 90)).toEqual([0, 0.25, 0.468, 0.723]);
    expect(positions(samba, 0.5, 90)[2]).toBeCloseTo(0.484);
    expect(positions(samba, 2, 90)).toEqual(positions(samba, 1, 90));
    expect(positions(samba, -1, 90)).toEqual(positions(samba, 0, 90));
    expect(positions(samba, 1, 150)).toEqual(positions(samba, 1, 90));
  });

  it.each(['samba', 'samba-hosoi'])('place %s dans les fourchettes de la vidéo', (id) => {
    const [, second, third, fourth] = positions(getGroove(id), 1, 90);
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
    expect(t[1].ms).toBeCloseTo(125);
    expect(t[1].offsetMs).toBeCloseTo(0); // sur la grille
    expect(t[2].offsetMs).toBeCloseTo(-16); // en avance
    expect(t[3].offsetMs).toBeCloseTo(-13.5);
  });

  it('retrouve les avances publiées au tempo moyen du corpus (103 bpm)', () => {
    const t = noteTimings(getGroove('samba'), 1, 103);
    expect(Math.round(-t[2].offsetMs)).toBe(19); // 3ᵉ note, aigu du spectre
    expect(Math.round(-t[3].offsetMs)).toBe(16); // 4ᵉ note
  });

  it('donne un écart moyen de 1/40 du temps pour la version Hosoi', () => {
    for (const bpm of [60, 90, 140]) {
      const mean = meanAbsOffsetMs(noteTimings(getGroove('samba-hosoi'), 1, bpm));
      expect(mean).toBeCloseTo(beatMs(bpm) / 40);
    }
  });

  it('garde un écart moyen proportionnel au temps', () => {
    for (const bpm of [60, 90, 140]) {
      const mean = meanAbsOffsetMs(noteTimings(getGroove('samba'), 1, bpm));
      expect(mean).toBeCloseTo((beatMs(bpm) * (0.032 + 0.027)) / 4);
    }
  });

  it('fait baisser le rapport du jazz quand le tempo monte', () => {
    expect(jazzSwingRatio(60)).toBe(3.5);
    expect(jazzSwingRatio(120)).toBe(3.5);
    expect(jazzSwingRatio(200)).toBeCloseTo(2);
    expect(jazzSwingRatio(240)).toBeCloseTo(1.5);
    expect(jazzSwingRatio(300)).toBe(1);
    expect(jazzSwingRatio(400)).toBe(1);
    for (let bpm = 61; bpm <= 300; bpm++) {
      expect(jazzSwingRatio(bpm)).toBeLessThanOrEqual(jazzSwingRatio(bpm - 1));
    }
  });

  it('place la 2ᵉ croche du jazz selon le rapport', () => {
    const jazz = getGroove('jazz');
    expect(positions(jazz, 1, 200)[1]).toBeCloseTo(2 / 3); // 2:1
    expect(positions(jazz, 1, 300)[1]).toBeCloseTo(0.5); // croches droites
    expect(positions(jazz, 0, 200)[1]).toBe(0.5);
    // Entre 133 et 300 bpm, la note courte dure 100 ms.
    const t = noteTimings(jazz, 1, 180);
    expect(beatMs(180) - t[1].ms).toBeCloseTo(100);
  });

  it('convertit les durées de Gerischer en positions', () => {
    expect(positionsFromDurations([100, 100, 100, 100])).toEqual([0, 0.25, 0.5, 0.75]);
    const pandeiro = positions(getGroove('bahia-pandeiro'), 1, 100);
    expect(pandeiro[1]).toBeCloseTo(0.2725);
    expect(pandeiro[2]).toBeCloseTo(0.4625);
    expect(pandeiro[3]).toBeCloseTo(0.6875);
    // Dans les trois instruments, la 3ᵉ et la 4ᵉ note sont en avance.
    for (const id of ['bahia-pandeiro', 'bahia-reco-reco', 'bahia-triangle']) {
      const p = positions(getGroove(id), 1, 100);
      expect(p[2]).toBeLessThan(0.5);
      expect(p[3]).toBeLessThan(0.75);
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

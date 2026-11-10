/**
 * Modèle des grooves : chaque groove décrit où tombent les notes à
 * l'intérieur d'UN temps, en fraction du temps (0 = début, 1 = temps suivant).
 *
 * - `grid`   : positions de référence, écrites sur la partition (swing 0 %).
 * - `target` : positions réellement jouées (swing 100 %).
 *
 * Le curseur de swing interpole linéairement entre les deux. Comme tout est
 * exprimé en fraction du temps, le BPM ne change pas les proportions : il ne
 * change que leur traduction en millisecondes.
 */
export interface Groove {
  id: string;
  label: string;
  hint: string;
  grid: number[];
  target: number[];
}

const SIXTEENTHS = [0, 0.25, 0.5, 0.75];

export const GROOVES: Groove[] = [
  {
    id: 'samba',
    label: 'Samba',
    hint: 'La 2ᵉ retarde un peu, les 3ᵉ et 4ᵉ sont tirées vers l’avant.',
    grid: SIXTEENTHS,
    // Milieu des fourchettes mesurées : 25–29 %, 42–50 %, 67–75 %.
    target: [0, 0.27, 0.46, 0.71],
  },
  {
    id: 'straight',
    label: 'Grille droite',
    hint: 'Quatre doubles-croches égales, quantifiées.',
    grid: SIXTEENTHS,
    target: SIXTEENTHS,
  },
  {
    id: 'garfinho',
    label: 'Garfinho',
    hint: 'Double-croche, croche, double-croche : 0 · 25 · 75 %.',
    grid: [0, 0.25, 0.75],
    target: [0, 0.25, 0.75],
  },
  {
    id: 'tercina',
    label: 'Tercina',
    hint: 'Triolet : trois notes égales, 0 · 33 · 67 %.',
    grid: [0, 1 / 3, 2 / 3],
    target: [0, 1 / 3, 2 / 3],
  },
  {
    id: 'jazz',
    label: 'Jazz',
    hint: 'Deux croches, la 2ᵉ retardée jusqu’au rapport 2:1.',
    grid: [0, 0.5],
    target: [0, 2 / 3],
  },
  {
    id: 'mpc',
    label: 'Swing MPC',
    hint: 'Les 2ᵉ et 4ᵉ doubles-croches retardent (réglage 62 %).',
    grid: SIXTEENTHS,
    // Swing MPC à 62 % : chaque paire de doubles-croches est découpée 62/38.
    target: [0, 0.31, 0.5, 0.81],
  },
];

export function getGroove(id: string): Groove {
  const groove = GROOVES.find((g) => g.id === id);
  if (!groove) throw new Error(`Groove inconnu : ${id}`);
  return groove;
}

/** Vrai si le curseur de swing a un effet sur ce groove. */
export function isSwingable(groove: Groove): boolean {
  return groove.grid.some((g, i) => g !== groove.target[i]);
}

/** Positions des notes (fractions du temps) pour un swing entre 0 et 1. */
export function positions(groove: Groove, swing: number): number[] {
  const s = Math.min(1, Math.max(0, swing));
  return groove.grid.map((g, i) => g + (groove.target[i] - g) * s);
}

/** Durée d'un temps en millisecondes. */
export function beatMs(bpm: number): number {
  return 60000 / bpm;
}

export interface NoteTiming {
  index: number;
  /** Position jouée, en fraction du temps. */
  fraction: number;
  /** Position de référence (grille), en fraction du temps. */
  gridFraction: number;
  /** Instant joué, en ms depuis le début du temps. */
  ms: number;
  /** Écart à la grille en ms : positif = en retard, négatif = en avance. */
  offsetMs: number;
}

export function noteTimings(groove: Groove, swing: number, bpm: number): NoteTiming[] {
  const beat = beatMs(bpm);
  return positions(groove, swing).map((fraction, index) => {
    const gridFraction = groove.grid[index];
    return {
      index,
      fraction,
      gridFraction,
      ms: fraction * beat,
      offsetMs: (fraction - gridFraction) * beat,
    };
  });
}

/** Écart moyen à la grille (valeur absolue), sur toutes les notes du temps. */
export function meanAbsOffsetMs(timings: NoteTiming[]): number {
  if (timings.length === 0) return 0;
  return timings.reduce((sum, t) => sum + Math.abs(t.offsetMs), 0) / timings.length;
}

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
 *
 * Exception : le jazz, dont le rapport long/court dépend du tempo. Un groove
 * peut donc fournir `targetAt`, qui calcule ses positions pour un BPM donné.
 */
export interface Groove {
  id: string;
  label: string;
  hint: string;
  grid: number[];
  target: number[];
  /** Positions jouées quand elles dépendent du tempo (remplace `target`). */
  targetAt?: (bpm: number) => number[];
  /** Tempo maximal proposé pour ce groove (160 par défaut). */
  maxBpm?: number;
}

export const DEFAULT_MAX_BPM = 160;

/**
 * Rapport long/court des croches swinguées selon le tempo.
 *
 * Modèle simple tiré de Friberg & Sundström (2002), mesures sur la cymbale
 * ride de batteurs : la note courte dure à peu près 100 ms quel que soit le
 * tempo, et le rapport va d'environ 3,5:1 à tempo lent à 1:1 à tempo rapide.
 * On garde donc la note courte à 100 ms et on borne le rapport entre 1 et 3,5.
 */
const JAZZ_SHORT_NOTE_MS = 100;
const JAZZ_MAX_RATIO = 3.5;

export function jazzSwingRatio(bpm: number): number {
  const ratio = (beatMs(bpm) - JAZZ_SHORT_NOTE_MS) / JAZZ_SHORT_NOTE_MS;
  return Math.min(JAZZ_MAX_RATIO, Math.max(1, ratio));
}

const SIXTEENTHS = [0, 0.25, 0.5, 0.75];

export const GROOVES: Groove[] = [
  {
    id: 'samba',
    label: 'Samba',
    hint: 'La 2ᵉ note traîne un peu, la 3ᵉ et la 4ᵉ arrivent en avance.',
    grid: SIXTEENTHS,
    // Milieu des fourchettes mesurées : 25–29 %, 42–50 %, 67–75 %.
    target: [0, 0.27, 0.46, 0.71],
  },
  {
    id: 'straight',
    label: 'Grille droite',
    hint: 'Quatre doubles-croches égales.',
    grid: SIXTEENTHS,
    target: SIXTEENTHS,
  },
  {
    id: 'garfinho',
    label: 'Garfinho',
    hint: 'Double-croche, croche, double-croche.',
    grid: [0, 0.25, 0.75],
    target: [0, 0.25, 0.75],
  },
  {
    id: 'tercina',
    label: 'Tercina',
    hint: 'Trois notes égales dans le temps.',
    grid: [0, 1 / 3, 2 / 3],
    target: [0, 1 / 3, 2 / 3],
  },
  {
    id: 'jazz',
    label: 'Jazz',
    hint: 'Deux croches, la 2ᵉ en retard. Plus le tempo monte, moins elle traîne.',
    grid: [0, 0.5],
    // Valeur d'écriture (2:1) ; la valeur jouée vient de `targetAt`.
    target: [0, 2 / 3],
    targetAt: (bpm) => {
      const ratio = jazzSwingRatio(bpm);
      return [0, ratio / (ratio + 1)];
    },
    maxBpm: 300,
  },
  {
    id: 'mpc',
    label: 'Swing MPC',
    hint: 'La 2ᵉ et la 4ᵉ double-croche en retard.',
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
  return groove.targetAt !== undefined || groove.grid.some((g, i) => g !== groove.target[i]);
}

/** Positions des notes (fractions du temps) pour un swing entre 0 et 1. */
export function positions(groove: Groove, swing: number, bpm: number): number[] {
  const s = Math.min(1, Math.max(0, swing));
  const target = groove.targetAt ? groove.targetAt(bpm) : groove.target;
  return groove.grid.map((g, i) => g + (target[i] - g) * s);
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
  return positions(groove, swing, bpm).map((fraction, index) => {
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

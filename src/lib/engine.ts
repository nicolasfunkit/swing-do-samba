import * as Tone from 'tone';

export interface EngineParams {
  bpm: number;
  /** Positions des notes dans le temps, en fraction (voir grooves.ts). */
  positions: number[];
  palma: boolean;
}

/** Un temps déjà programmé dans l'horloge audio (temps en secondes). */
export interface ScheduledBeat {
  index: number;
  start: number;
  duration: number;
  positions: number[];
}

interface Voices {
  tamborimTone: Tone.MembraneSynth;
  tamborimNoise: Tone.NoiseSynth;
  surdo: Tone.MembraneSynth;
  palma: Tone.NoiseSynth;
  nodes: Tone.ToneAudioNode[];
}

/** Fréquence de réveil du planificateur. */
const TICK_MS = 25;
/** Fenêtre d'anticipation : on programme les temps qui démarrent d'ici là. */
const LOOKAHEAD_S = 0.15;

function createVoices(): Voices {
  const out = new Tone.Gain(0.7).toDestination();

  // Tamborim : un corps aigu très court + un claquement de bruit filtré.
  const tamborimTone = new Tone.MembraneSynth({
    pitchDecay: 0.006,
    octaves: 1.5,
    oscillator: { type: 'triangle' },
    envelope: { attack: 0.001, decay: 0.09, sustain: 0, release: 0.02 },
  }).connect(out);
  tamborimTone.volume.value = -8;

  const highpass = new Tone.Filter(2500, 'highpass').connect(out);
  const tamborimNoise = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.035, sustain: 0, release: 0.01 },
  }).connect(highpass);
  tamborimNoise.volume.value = -14;

  // Surdo : membrane grave, marque les temps.
  const surdo = new Tone.MembraneSynth({
    pitchDecay: 0.03,
    octaves: 2.5,
    envelope: { attack: 0.001, decay: 0.45, sustain: 0, release: 0.05 },
  }).connect(out);
  surdo.volume.value = -4;

  // Palma : bruit blanc passe-bande, sur le 2. Le filtre retire l'essentiel
  // de l'énergie, d'où le gain élevé : il faut passer par-dessus le surdo,
  // qui frappe au même instant.
  const bandpass = new Tone.Filter({ type: 'bandpass', frequency: 1300, Q: 0.8 }).connect(out);
  const palma = new Tone.NoiseSynth({
    noise: { type: 'white' },
    envelope: { attack: 0.001, decay: 0.12, sustain: 0, release: 0.03 },
  }).connect(bandpass);
  palma.volume.value = 3;

  return {
    tamborimTone,
    tamborimNoise,
    surdo,
    palma,
    nodes: [tamborimTone, tamborimNoise, surdo, palma, highpass, bandpass, out],
  };
}

/**
 * Planificateur à anticipation : un minuteur JS (imprécis) se réveille
 * souvent et programme, sur l'horloge audio (précise), les temps qui
 * commencent dans les 150 ms à venir. Les paramètres sont relus à chaque
 * nouveau temps, donc un changement de BPM ou de swing s'entend au temps
 * suivant, sans coupure.
 */
export class Engine {
  private timer: ReturnType<typeof setInterval> | null = null;
  private voices: Voices | null = null;
  private beats: ScheduledBeat[] = [];
  private nextStart = 0;
  private beatIndex = 0;

  constructor(private readonly getParams: () => EngineParams) {}

  async start(): Promise<void> {
    if (this.timer !== null) return;
    await Tone.start();
    this.voices ??= createVoices();
    this.beats = [];
    this.beatIndex = 0;
    this.nextStart = this.now() + 0.1;
    this.tick();
    this.timer = setInterval(() => this.tick(), TICK_MS);
  }

  stop(): void {
    if (this.timer !== null) clearInterval(this.timer);
    this.timer = null;
    this.beats = [];
  }

  dispose(): void {
    this.stop();
    this.voices?.nodes.forEach((node) => node.dispose());
    this.voices = null;
  }

  /** Heure de l'horloge audio, en secondes. */
  now(): number {
    return Tone.immediate();
  }

  /** Le temps en cours de lecture, pour synchroniser l'affichage. */
  currentBeat(): ScheduledBeat | null {
    const now = this.now();
    return this.beats.find((b) => now >= b.start && now < b.start + b.duration) ?? null;
  }

  private tick(): void {
    const now = this.now();
    // Après une longue pause du minuteur (onglet en arrière-plan), on repart
    // de maintenant plutôt que de rattraper les temps manqués d'un coup.
    if (this.nextStart < now) this.nextStart = now + 0.05;
    while (this.nextStart < now + LOOKAHEAD_S) this.scheduleBeat();
    this.beats = this.beats.filter((b) => b.start + b.duration > now - 0.5);
  }

  private scheduleBeat(): void {
    const voices = this.voices;
    if (!voices) return;
    const { bpm, positions, palma } = this.getParams();
    const duration = 60 / bpm;
    const start = this.nextStart;
    const isBeatTwo = this.beatIndex % 2 === 1;

    // Surdo : étouffé sur le 1, ouvert et plus fort sur le 2.
    voices.surdo.triggerAttackRelease(isBeatTwo ? 'F1' : 'A1', 0.2, start, isBeatTwo ? 0.9 : 0.4);
    if (palma && isBeatTwo) voices.palma.triggerAttackRelease(0.06, start, 1);

    positions.forEach((fraction, i) => {
      const time = start + fraction * duration;
      const velocity = i === 0 ? 0.9 : 0.6;
      voices.tamborimTone.triggerAttackRelease('A5', 0.03, time, velocity);
      voices.tamborimNoise.triggerAttackRelease(0.02, time, velocity);
    });

    this.beats.push({ index: this.beatIndex, start, duration, positions: [...positions] });
    this.beatIndex += 1;
    this.nextStart = start + duration;
  }
}

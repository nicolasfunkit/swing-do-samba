<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Engine } from './lib/engine';
  import {
    GROOVES,
    beatMs,
    DEFAULT_MAX_BPM,
    accentsFor,
    getGroove,
    isSwingable,
    meanAbsOffsetMs,
    noteTimings,
    positions,
  } from './lib/grooves';

  let bpm = $state(90);
  let swingPct = $state(100);
  let grooveId = $state('samba');
  let palma = $state(false);
  let playing = $state(false);

  /** Avancement dans le temps en cours (0 à 1), ou null à l'arrêt. */
  let phase = $state<number | null>(null);
  let beatNumber = $state(1);

  const groove = $derived(getGroove(grooveId));
  const swingable = $derived(isSwingable(groove));
  const maxBpm = $derived(groove.maxBpm ?? DEFAULT_MAX_BPM);
  const swing = $derived(swingPct / 100);
  const timings = $derived(noteTimings(groove, swing, bpm));
  const beat = $derived(beatMs(bpm));
  const meanOffset = $derived(meanAbsOffsetMs(timings));

  const engine = new Engine(() => ({
    bpm,
    positions: positions(groove, swing, bpm),
    accents: [accentsFor(groove, 0), accentsFor(groove, 1)],
    palma,
  }));

  // Rapport réellement joué entre les deux croches du jazz, swing compris.
  const jazzRatio = $derived.by(() => {
    if (groove.id !== 'jazz') return null;
    const second = timings[1].fraction;
    return (second / (1 - second)).toFixed(1).replace('.', ',');
  });

  function selectGroove(id: string) {
    grooveId = id;
    // Le jazz monte jusqu'à 300 bpm, les autres s'arrêtent à 160.
    bpm = Math.min(bpm, getGroove(id).maxBpm ?? DEFAULT_MAX_BPM);
  }

  let frame = 0;

  function draw() {
    const current = engine.currentBeat();
    if (current) {
      phase = (engine.now() - current.start) / current.duration;
      beatNumber = (current.index % 2) + 1;
    }
    frame = requestAnimationFrame(draw);
  }

  async function toggle() {
    if (playing) {
      engine.stop();
      cancelAnimationFrame(frame);
      playing = false;
      phase = null;
      return;
    }
    await engine.start();
    playing = true;
    frame = requestAnimationFrame(draw);
  }

  onDestroy(() => {
    cancelAnimationFrame(frame);
    engine.dispose();
  });

  // Géométrie de la ligne de temps (unités du viewBox).
  // Une unité SVG = un pixel : la ligne s'étire avec l'écran, mais les
  // points et les textes gardent une taille lisible sur téléphone.
  let stageWidth = $state(700);
  // Deux lignes, une par temps de la mesure : les notes tombent au même
  // endroit sur les deux, mais les accents diffèrent.
  const BEATS = [0, 1];
  const ROW_GAP = 92;
  const HEIGHT = 226;
  const PAD_LEFT = 22;
  const PAD_RIGHT = 34;
  const rowY = (beatInCycle: number) => 78 + beatInCycle * ROW_GAP;
  const x = (fraction: number) =>
    PAD_LEFT + fraction * Math.max(stageWidth - PAD_LEFT - PAD_RIGHT, 100);

  const NOTE_COLORS = ['var(--note-1)', 'var(--note-2)', 'var(--note-3)', 'var(--note-4)'];
  const LIT_MS = 90;

  // Accent de chaque note, pour le temps 1 puis le temps 2.
  const accents = $derived(BEATS.map((b) => accentsFor(groove, b)));
  const NOTE_RADIUS = 9;
  // Une note forte reçoit le signe d'accent musical « > » au-dessus de son numéro.
  const isAccented = (accent: number) => accent >= 0.8;

  function accentLabel(accent: number): string {
    if (accent >= 0.8) return 'forte';
    if (accent >= 0.55) return 'moyenne';
    return 'faible';
  }

  function isLit(beatInCycle: number, fraction: number): boolean {
    if (phase === null || beatNumber - 1 !== beatInCycle) return false;
    const elapsed = (phase - fraction) * beat;
    return elapsed >= 0 && elapsed < LIT_MS;
  }

  const pct = (fraction: number) => `${(fraction * 100).toFixed(1).replace('.', ',')} %`;
  const ms = (value: number) => `${Math.round(value)} ms`;

  function offsetLabel(offsetMs: number): string {
    const rounded = Math.round(offsetMs);
    if (rounded === 0) return 'sur la grille';
    return rounded > 0 ? `${rounded} ms en retard` : `${-rounded} ms en avance`;
  }
</script>

<main>
  <header>
    <p class="eyebrow">Le microtemps du samba</p>
    <h1>Le swing du samba</h1>
    <p class="lede">Ni garfinho, ni tercina.</p>
  </header>

  <section class="grooves" aria-label="Choix du groove">
    {#each GROOVES as g (g.id)}
      <button class="chip" class:active={g.id === grooveId} onclick={() => selectGroove(g.id)}>
        {g.label}
      </button>
    {/each}
  </section>
  <p class="hint">
    {groove.hint}
    {#if jazzRatio !== null}
      Rapport long/court à ce tempo : <strong>{jazzRatio}:1</strong>.
    {/if}
  </p>

  <section class="stage">
    <div class="svg-wrap" bind:clientWidth={stageWidth}>
      <svg
        viewBox="0 0 {stageWidth} {HEIGHT}"
        width={stageWidth}
        height={HEIGHT}
        role="img"
        aria-label="Position et accent des notes sur les deux temps de la mesure"
      >
        {#each BEATS as b}
          {@const Y = rowY(b)}
          <line class="axis" x1={x(0)} y1={Y} x2={x(1)} y2={Y} />
          <text class="row-label" x={x(1)} y={Y - 32}>temps {b + 1}</text>

          <!-- Repères : doubles-croches droites et tiers du triolet -->
          {#each [0, 0.25, 0.5, 0.75, 1] as tick}
            <line class="tick" x1={x(tick)} y1={Y - 16} x2={x(tick)} y2={Y + 16} />
            {#if b === 1}
              <text class="tick-label" x={x(tick)} y={Y + 36}>
                {Math.round(tick * beat)}{tick === 1 ? ' ms' : ''}
              </text>
            {/if}
          {/each}
          {#each [1 / 3, 2 / 3] as tick}
            <line class="tick triplet" x1={x(tick)} y1={Y - 16} x2={x(tick)} y2={Y + 16} />
          {/each}

          <!-- Grille de référence (cercles vides) et déplacement -->
          {#each timings as t (t.index)}
            <circle class="ghost" cx={x(t.gridFraction)} cy={Y} r="4.5" />
            {#if Math.abs(t.fraction - t.gridFraction) > 0.002}
              <line
                class="shift"
                x1={x(t.gridFraction)}
                y1={Y - 18}
                x2={x(t.fraction)}
                y2={Y - 18}
                stroke={NOTE_COLORS[t.index % 4]}
              />
              <circle cx={x(t.fraction)} cy={Y - 18} r="3.5" fill={NOTE_COLORS[t.index % 4]} />
            {/if}
          {/each}

          <!-- Notes jouées : l'anneau marque la note qui sonne, le « > » une note accentuée -->
          {#each timings as t (t.index)}
            {@const cx = x(t.fraction)}
            <circle {cx} cy={Y} r={NOTE_RADIUS} fill={NOTE_COLORS[t.index % 4]} />
            {#if isLit(b, t.fraction)}
              <circle
                class="halo"
                {cx}
                cy={Y}
                r={NOTE_RADIUS + 5}
                stroke={NOTE_COLORS[t.index % 4]}
              />
            {/if}
            <text class="note-label" x={cx} y={Y - 32}>{t.index + 1}</text>
            {#if isAccented(accents[b][t.index] ?? 0.6)}
              <polyline
                class="accent"
                points="{cx - 6},{Y - 56} {cx + 6},{Y - 52} {cx - 6},{Y - 48}"
              />
            {/if}
          {/each}

          {#if phase !== null && beatNumber - 1 === b}
            <line class="playhead" x1={x(phase)} y1={Y - 26} x2={x(phase)} y2={Y + 22} />
          {/if}
        {/each}
      </svg>
    </div>
    <p class="legend">
      Une ligne par temps. Points pleins : ce qui est joué. Signe &gt; au-dessus du numéro : note
      accentuée. Cercles vides : la grille. Pointillés : la tercina.
    </p>
  </section>

  <section class="controls">
    <button class="play" onclick={toggle} aria-pressed={playing}>
      {playing ? 'Stop' : 'Jouer'}
    </button>

    <label>
      <span>Tempo <strong>{bpm} bpm</strong></span>
      <input type="range" min="60" max={maxBpm} step="1" bind:value={bpm} />
    </label>

    <label class:disabled={!swingable}>
      <span>
        Swing <strong>{swingable ? `${swingPct} %` : 'fixe'}</strong>
      </span>
      <input type="range" min="0" max="100" step="1" bind:value={swingPct} disabled={!swingable} />
    </label>

    <label class="check">
      <input type="checkbox" bind:checked={palma} />
      <span>Palma sur le 2</span>
    </label>
  </section>

  <section class="stats">
    <div class="stat">
      <span class="stat-label">Durée d’un temps</span>
      <span class="stat-value">{ms(beat)}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Écart moyen</span>
      <span class="stat-value">{ms(meanOffset)}</span>
      {#if meanOffset > 0.5}
        <span class="stat-note">1/{Math.round(beat / meanOffset)} du temps</span>
      {/if}
    </div>
    <div class="stat">
      <span class="stat-label">Temps</span>
      <span class="stat-value">{playing ? beatNumber : '–'}</span>
    </div>
  </section>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Note</th>
          <th>Position</th>
          <th>En ms</th>
          <th>Écart</th>
          <th>Accent (temps 1 / temps 2)</th>
        </tr>
      </thead>
      <tbody>
        {#each timings as t (t.index)}
          <tr>
            <td>
              <span class="dot" style:background={NOTE_COLORS[t.index % 4]}></span>
              {t.index + 1}
            </td>
            <td>{pct(t.fraction)}</td>
            <td>{ms(t.ms)}</td>
            <td>{offsetLabel(t.offsetMs)}</td>
            <td>
              {accentLabel(accents[0][t.index] ?? 0.6)} / {accentLabel(accents[1][t.index] ?? 0.6)}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <footer>
    D’après la vidéo « O swing do samba » d’André Hosoi. Chiffres du samba : Naveda, Gouyon, Guedes et Leman (2011).
  </footer>
</main>

<style>
  :global(:root) {
    --bg: #f6f4ef;
    --surface: #ffffff;
    --text: #1c1b22;
    --muted: #6a6875;
    --line: #d9d5cc;
    --accent: #0f8f6f;
    --note-1: #1c1b22;
    --note-2: #0f8f6f;
    --note-3: #c98a00;
    --note-4: #c2378a;
    color-scheme: light dark;
  }

  @media (prefers-color-scheme: dark) {
    :global(:root) {
      --bg: #12121a;
      --surface: #1c1c28;
      --text: #f1eff7;
      --muted: #9c9aab;
      --line: #34344a;
      --accent: #3fd0a8;
      --note-1: #f1eff7;
      --note-2: #3fd0a8;
      --note-3: #f2b632;
      --note-4: #f067b4;
    }
  }

  :global(body) {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
    line-height: 1.5;
  }

  main {
    max-width: 780px;
    margin: 0 auto;
    padding: max(24px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right))
      max(40px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left));
  }

  button,
  label {
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .eyebrow {
    margin: 0;
    font-size: 0.75rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent);
    font-weight: 600;
  }

  h1 {
    margin: 4px 0 4px;
    font-size: clamp(1.8rem, 6vw, 2.6rem);
    line-height: 1.1;
  }

  .lede {
    margin: 0 0 24px;
    color: var(--muted);
  }

  .grooves {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .chip {
    min-height: 44px;
    padding: 8px 16px;
    border: 1px solid var(--line);
    border-radius: 999px;
    background: var(--surface);
    color: var(--text);
    font: inherit;
    cursor: pointer;
  }

  .chip.active {
    border-color: var(--accent);
    background: var(--accent);
    color: var(--bg);
    font-weight: 600;
  }

  .hint {
    margin: 12px 0 16px;
    color: var(--muted);
    min-height: 1.5em;
  }

  .stage {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 12px 8px 8px;
  }

  .svg-wrap {
    width: 100%;
    overflow: hidden;
  }

  svg {
    display: block;
  }

  .axis {
    stroke: var(--line);
    stroke-width: 2;
  }

  .tick {
    stroke: var(--line);
    stroke-width: 1.5;
  }

  .tick.triplet {
    stroke: var(--note-4);
    stroke-dasharray: 4 5;
    opacity: 0.7;
  }

  .tick-label,
  .note-label {
    fill: var(--muted);
    font-size: 12px;
    text-anchor: middle;
    font-variant-numeric: tabular-nums;
  }

  .note-label {
    fill: var(--text);
    font-weight: 700;
  }

  .ghost {
    fill: var(--surface);
    stroke: var(--muted);
    stroke-width: 2;
  }

  .shift {
    stroke-width: 2.5;
    stroke-linecap: round;
  }

  .halo {
    fill: none;
    stroke-width: 2.5;
  }

  .accent {
    fill: none;
    stroke: var(--text);
    stroke-width: 2.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .row-label {
    fill: var(--muted);
    font-size: 11px;
    text-anchor: end;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  .playhead {
    stroke: var(--text);
    stroke-width: 2;
  }

  .legend {
    margin: 4px 8px 4px;
    font-size: 0.8rem;
    color: var(--muted);
    text-align: center;
  }

  .controls {
    display: grid;
    grid-template-columns: auto 1fr 1fr;
    gap: 16px 20px;
    align-items: center;
    margin: 20px 0;
  }

  .play {
    grid-row: span 2;
    min-width: 110px;
    padding: 16px 20px;
    border: none;
    border-radius: 14px;
    background: var(--accent);
    color: var(--bg);
    font: inherit;
    font-size: 1.1rem;
    font-weight: 700;
    cursor: pointer;
  }

  label {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  label.disabled {
    opacity: 0.5;
  }

  label strong {
    font-variant-numeric: tabular-nums;
  }

  input[type='range'] {
    width: 100%;
    height: 32px;
    margin: 0;
    accent-color: var(--accent);
  }

  .check {
    grid-column: 2 / -1;
    flex-direction: row;
    align-items: center;
    gap: 10px;
    min-height: 44px;
  }

  .check input {
    accent-color: var(--accent);
    width: 22px;
    height: 22px;
  }

  .stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 20px;
  }

  .stat {
    display: flex;
    flex-direction: column;
    padding: 12px 14px;
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 12px;
  }

  .stat-label,
  .stat-note {
    font-size: 0.8rem;
    color: var(--muted);
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 10px 8px;
    text-align: left;
    border-bottom: 1px solid var(--line);
    white-space: nowrap;
  }

  th {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }

  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    margin-right: 6px;
    border-radius: 50%;
  }

  footer {
    margin-top: 28px;
    font-size: 0.8rem;
    color: var(--muted);
  }

  @media (max-width: 560px) {
    .controls {
      grid-template-columns: 1fr;
    }

    .play {
      grid-row: auto;
    }

    .check {
      grid-column: auto;
    }

    .stats {
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .stat:last-child {
      display: none;
    }

    .stat-value {
      font-size: 1.25rem;
    }

    th,
    td {
      padding: 10px 6px;
      font-size: 0.9rem;
    }
  }
</style>

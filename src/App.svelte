<script lang="ts">
  import { onDestroy } from 'svelte';
  import { Engine } from './lib/engine';
  import {
    GROOVES,
    beatMs,
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
  const swing = $derived(swingPct / 100);
  const timings = $derived(noteTimings(groove, swing, bpm));
  const beat = $derived(beatMs(bpm));
  const meanOffset = $derived(meanAbsOffsetMs(timings));

  const engine = new Engine(() => ({
    bpm,
    positions: positions(groove, swing),
    palma,
  }));

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
  const X0 = 60;
  const WIDTH = 880;
  const Y = 110;
  const x = (fraction: number) => X0 + fraction * WIDTH;

  const NOTE_COLORS = ['var(--note-1)', 'var(--note-2)', 'var(--note-3)', 'var(--note-4)'];
  const LIT_MS = 90;

  function isLit(fraction: number): boolean {
    if (phase === null) return false;
    const elapsed = (phase - fraction) * beat;
    return elapsed >= 0 && elapsed < LIT_MS;
  }

  const pct = (fraction: number) => `${(fraction * 100).toFixed(1).replace('.', ',')} %`;
  const ms = (value: number) => `${Math.round(value)} ms`;

  function offsetLabel(offsetMs: number): string {
    const rounded = Math.round(offsetMs);
    if (rounded === 0) return 'sur la grille';
    return rounded > 0 ? `+${rounded} ms · en retard` : `−${-rounded} ms · en avance`;
  }
</script>

<main>
  <header>
    <p class="eyebrow">Microtemps dans la samba</p>
    <h1>Le swing de la samba</h1>
    <p class="lede">Ni garfinho, ni tercina : le tamborim joue entre les deux.</p>
  </header>

  <section class="grooves" aria-label="Choix du groove">
    {#each GROOVES as g (g.id)}
      <button class="chip" class:active={g.id === grooveId} onclick={() => (grooveId = g.id)}>
        {g.label}
      </button>
    {/each}
  </section>
  <p class="hint">{groove.hint}</p>

  <section class="stage">
    <svg viewBox="0 0 1000 200" role="img" aria-label="Position des notes dans un temps">
      <line class="axis" x1={x(0)} y1={Y} x2={x(1)} y2={Y} />

      <!-- Repères : doubles-croches droites et tiers du triolet -->
      {#each [0, 0.25, 0.5, 0.75, 1] as tick}
        <line class="tick" x1={x(tick)} y1={Y - 22} x2={x(tick)} y2={Y + 22} />
        <text class="tick-label" x={x(tick)} y={Y + 44}>{Math.round(tick * beat)}</text>
      {/each}
      {#each [1 / 3, 2 / 3] as tick}
        <line class="tick triplet" x1={x(tick)} y1={Y - 22} x2={x(tick)} y2={Y + 22} />
      {/each}
      <text class="tick-label unit" x={x(1) + 14} y={Y + 44}>ms</text>

      <!-- Grille de référence (cercles vides) et déplacement -->
      {#each timings as t (t.index)}
        <circle class="ghost" cx={x(t.gridFraction)} cy={Y} r="11" />
        {#if Math.abs(t.fraction - t.gridFraction) > 0.002}
          <line
            class="shift"
            x1={x(t.gridFraction)}
            y1={Y - 30}
            x2={x(t.fraction)}
            y2={Y - 30}
            stroke={NOTE_COLORS[t.index % 4]}
          />
          <circle cx={x(t.fraction)} cy={Y - 30} r="4" fill={NOTE_COLORS[t.index % 4]} />
        {/if}
      {/each}

      <!-- Notes jouées -->
      {#each timings as t (t.index)}
        <circle
          class="note"
          class:lit={isLit(t.fraction)}
          cx={x(t.fraction)}
          cy={Y}
          r={isLit(t.fraction) ? 17 : 11}
          fill={NOTE_COLORS[t.index % 4]}
        />
        <text class="note-label" x={x(t.fraction)} y={Y - 44}>{t.index + 1}</text>
      {/each}

      {#if phase !== null}
        <line class="playhead" x1={x(phase)} y1={Y - 60} x2={x(phase)} y2={Y + 26} />
      {/if}
    </svg>
    <p class="legend">
      Cercles vides : grille écrite · traits pointillés : tiers du triolet · points pleins : notes
      jouées
    </p>
  </section>

  <section class="controls">
    <button class="play" onclick={toggle} aria-pressed={playing}>
      {playing ? 'Arrêter' : 'Lire'}
    </button>

    <label>
      <span>Tempo <strong>{bpm} bpm</strong></span>
      <input type="range" min="60" max="160" step="1" bind:value={bpm} />
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
      <span class="stat-label">Un temps</span>
      <span class="stat-value">{ms(beat)}</span>
    </div>
    <div class="stat">
      <span class="stat-label">Écart moyen à la grille</span>
      <span class="stat-value">{ms(meanOffset)}</span>
      {#if meanOffset > 0.5}
        <span class="stat-note">≈ 1/{Math.round(beat / meanOffset)} du temps</span>
      {/if}
    </div>
    <div class="stat">
      <span class="stat-label">Temps en cours</span>
      <span class="stat-value">{playing ? beatNumber : '–'}</span>
    </div>
  </section>

  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Note</th>
          <th>Position</th>
          <th>Instant</th>
          <th>Écart à la grille</th>
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
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <footer>
    D’après la vidéo « O swing do samba » d’André Hosoi. Mesures citées : Gouyon (2007), samba de
    roda.
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
    padding: 32px 16px 48px;
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
    padding: 8px 14px;
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

  svg {
    display: block;
    width: 100%;
    height: auto;
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
    font-size: 18px;
    text-anchor: middle;
    font-variant-numeric: tabular-nums;
  }

  .tick-label.unit {
    text-anchor: start;
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
    stroke-width: 3;
    stroke-linecap: round;
  }

  .note {
    transition: r 80ms ease-out;
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
    accent-color: var(--accent);
  }

  .check {
    grid-column: 2 / -1;
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .check input {
    accent-color: var(--accent);
    width: 18px;
    height: 18px;
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
      grid-template-columns: 1fr;
    }
  }
</style>

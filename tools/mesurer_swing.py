#!/usr/bin/env python3
"""Mesure le swing d'un instrument qui joue quatre doubles-croches par temps.

Le script lit un fichier audio ou vidéo, repère les attaques de notes, les
regroupe par temps et donne la position moyenne des 2ᵉ, 3ᵉ et 4ᵉ
doubles-croches à l'intérieur du temps (0 = le temps, 1 = le temps suivant).

Il ne dépend que de la bibliothèque standard de Python et de `ffmpeg`.
Mode d'emploi et limites : docs/mesurer-le-swing.md

Exemples :
    python3 tools/mesurer_swing.py --autotest
    python3 tools/mesurer_swing.py cavaco.mp4 --debut 12 --fin 45 --bpm 96
    python3 tools/mesurer_swing.py cavaco.mp4 --debut 1:12 --fin 2:05.5
    python3 tools/mesurer_swing.py cavaco.mp4 --debut 12 --fin 45 --json cavaco.json --labels cavaco.txt
    python3 tools/mesurer_swing.py partido.mp4 --debut 8 --fin 60 --bpm 92 --cycle 16

Avec --cycle, le motif peut avoir des silences (partido alto, variations de
levada) : les notes sont rangées dans les cases d'un cycle de N doubles-croches.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import subprocess
import sys
import tempfile
import wave
from array import array
from itertools import accumulate
from pathlib import Path

SR = 44100  # fréquence d'échantillonnage de travail
HOP = 44  # pas d'analyse : 1 ms
WIN = 256  # fenêtre d'énergie : 5,8 ms
LAG = 8  # on compare l'énergie à celle d'il y a 8 ms
# Trois bandes : corps de la note, médium, attaque du médiator ou des doigts.
BANDS = [(150, 800), (800, 3000), (3000, 12000)]
GRID = [0.25, 0.5, 0.75]
LEVEL_WINDOW_S = 0.04  # durée sur laquelle on mesure la force d'une note

# Positions publiées, pour situer le résultat (voir docs/grooves-bresiliens.md).
REFERENCES = {
    "Grille droite": [0.25, 0.5, 0.75],
    "Samba, disques (Naveda 2011)": [0.25, 0.468, 0.723],
    "Tamborim seul (Fuentes 2019)": [0.27, 0.434, 0.671],
    "Pandeiro seul (Lindsay 2007)": [0.293, 0.441, 0.672],
    "Tercina (2ᵉ et 3ᵉ notes)": [1 / 3, None, 2 / 3],
}


# --- Lecture du son -------------------------------------------------------


def decode(path: str, start: float | None, end: float | None, band: tuple[int, int]) -> array:
    """Décode le fichier en mono 44,1 kHz, filtré sur une bande, via ffmpeg."""
    low, high = band
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    if end is not None:
        cmd += ["-to", str(end)]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR)]
    cmd += ["-af", f"highpass=f={low},lowpass=f={high}", "-f", "s16le", "-"]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except FileNotFoundError:
        sys.exit("ffmpeg est introuvable : installe-le (sudo apt install ffmpeg).")
    except subprocess.CalledProcessError as error:
        sys.exit(f"ffmpeg n'a pas pu lire {path} :\n{error.stderr.decode(errors='replace')}")
    pcm = array("h")
    pcm.frombytes(result.stdout[: len(result.stdout) // 2 * 2])
    if sys.byteorder == "big":
        pcm.byteswap()
    return pcm


def energy_envelope(pcm: array) -> list[int]:
    """Énergie du signal sur une fenêtre glissante, un point par milliseconde."""
    cumulative = [0]
    cumulative.extend(accumulate(sample * sample for sample in pcm))
    count = max(0, (len(pcm) - WIN) // HOP)
    return [cumulative[i * HOP + WIN] - cumulative[i * HOP] for i in range(count)]


# --- Détection des attaques ----------------------------------------------


def onset_strength(envelopes: list[list[int]]) -> list[float]:
    """Flux d'énergie : somme, sur les bandes, des hausses de niveau en dB."""
    length = min(len(envelope) for envelope in envelopes)
    flux = [0.0] * length
    for envelope in envelopes:
        peak = max(envelope[:length], default=0) or 1
        # Plancher à -40 dB du maximum, pour ne pas amplifier le bruit de fond.
        level = [10 * math.log10(value / peak + 1e-4) for value in envelope[:length]]
        for t in range(LAG, length):
            rise = level[t] - level[t - LAG]
            if rise > 0:
                flux[t] += rise
    # Lissage triangulaire sur 5 ms.
    kernel = [1, 2, 3, 2, 1]
    smooth = [0.0] * length
    for t in range(2, length - 2):
        smooth[t] = sum(k * flux[t + i - 2] for i, k in enumerate(kernel)) / 9
    return smooth


def pick_onsets(flux: list[float], min_gap_s: float, sensitivity: float) -> list[float]:
    """Instants (en secondes depuis le début du passage) des pics du flux."""
    gap = max(1, round(min_gap_s * SR / HOP))
    candidates = []
    for t in range(gap, len(flux) - gap):
        value = flux[t]
        if value <= 0 or value < flux[t - 1] or value <= flux[t + 1]:
            continue
        if value >= max(flux[t - gap : t + gap + 1]):
            candidates.append(t)
    if not candidates:
        return []
    heights = sorted(flux[t] for t in candidates)
    reference = heights[min(len(heights) - 1, int(0.9 * len(heights)))]
    threshold = 0.25 * reference / sensitivity
    onsets = []
    for t in candidates:
        if flux[t] < threshold:
            continue
        # Interpolation parabolique pour descendre sous la milliseconde.
        a, b, c = flux[t - 1], flux[t], flux[t + 1]
        denominator = a - 2 * b + c
        shift = 0.5 * (a - c) / denominator if denominator else 0.0
        onsets.append(((t + shift) * HOP + WIN / 2) / SR)
    return onsets


def note_levels(envelopes: list[list[int]], onsets: list[float]) -> list[float]:
    """Force de chaque note en dB : énergie des 40 ms qui suivent l'attaque."""
    length = min(len(envelope) for envelope in envelopes)
    span = round(LEVEL_WINDOW_S * SR / HOP)
    levels = []
    for onset in onsets:
        first = max(0, round((onset * SR - WIN / 2) / HOP))
        total = sum(sum(envelope[first : min(length, first + span)]) for envelope in envelopes)
        levels.append(10 * math.log10(total + 1))
    return levels


# --- Regroupement par temps ----------------------------------------------


def estimate_beat(onsets: list[float], bpm: float | None) -> float:
    """Durée d'un temps : donnée par l'utilisateur, ou déduite des attaques.

    L'écart entre une attaque et la quatrième suivante vaut un temps entier,
    quel que soit le swing : sa médiane donne donc le tempo sans biais.
    """
    if bpm:
        return 60 / bpm
    if len(onsets) < 9:
        sys.exit("Trop peu d'attaques détectées pour estimer le tempo : précise --bpm.")
    spans = [onsets[i + 4] - onsets[i] for i in range(len(onsets) - 4)]
    return statistics.median(spans)


def nearest(onsets: list[float], start_index: int, target: float) -> int | None:
    best = None
    for j in range(start_index, len(onsets)):
        if best is None or abs(onsets[j] - target) < abs(onsets[best] - target):
            best = j
        if onsets[j] > target:
            break
    return best


def segment(onsets: list[float], levels: list[float], beat: float, first: int, tolerance: float):
    """Découpe la suite d'attaques en temps de quatre notes.

    Un temps est gardé seulement s'il contient exactement quatre attaques,
    chacune à moins de `tolerance` (en fraction du temps) de sa place sur la
    grille droite. Les autres sont comptés comme rejetés.
    """
    kept = []
    rejected = 0
    lost_at = None
    i = first
    while i < len(onsets) - 1:
        start = onsets[i]
        j = None
        skipped = 0
        # Cherche le début du temps suivant ; si la note manque, saute un temps.
        for multiple in range(1, 9):
            candidate = nearest(onsets, i + 1, start + multiple * beat)
            if candidate is not None and abs(onsets[candidate] - (start + multiple * beat)) <= tolerance * beat:
                j = candidate
                skipped = multiple - 1
                break
        if j is None:
            if start + 8 * beat < onsets[-1]:
                lost_at = start
            break
        rejected += skipped
        if skipped == 0:
            interval = onsets[j] - start
            inside = onsets[i + 1 : j]
            fractions = [(t - start) / interval for t in inside]
            if len(inside) == 3 and all(abs(f - g) < tolerance for f, g in zip(fractions, GRID)):
                mean_level = sum(levels[i : i + 4]) / 4
                kept.append(
                    {
                        "debut": start,
                        "duree": interval,
                        "positions": fractions,
                        "niveaux": [level - mean_level for level in levels[i : i + 4]],
                    }
                )
                beat = 0.8 * beat + 0.2 * interval  # suit les variations de tempo
            else:
                rejected += 1
        i = j
    return kept, rejected, lost_at


# --- Mode cycle : motifs avec silences ------------------------------------


def track_beats(onsets: list[float], beat: float, first: int, tolerance: float) -> list[tuple[int, int]]:
    """Suit la pulsation à partir d'une note posée sur un temps.

    Renvoie les ancres : couples (numéro du temps, indice de l'attaque) pour
    chaque temps où une note tombe à moins de `tolerance` de l'instant prévu.
    Les temps sans note sont sautés ; ils seront interpolés ensuite.
    """
    anchors = [(0, first)]
    last_number, last_time, index = 0, onsets[first], first
    number = 0
    while True:
        number += 1
        predicted = last_time + (number - last_number) * beat
        if predicted > onsets[-1] + tolerance * beat:
            break
        j = nearest(onsets, index + 1, predicted)
        if j is not None and abs(onsets[j] - predicted) <= tolerance * beat:
            beat = 0.7 * beat + 0.3 * (onsets[j] - last_time) / (number - last_number)
            anchors.append((number, j))
            last_number, last_time, index = number, onsets[j], j
    return anchors


def assign_slots(onsets: list[float], levels: list[float], anchors: list[tuple[int, int]], tolerance: float):
    """Range chaque attaque dans une double-croche, entre deux ancres.

    Entre deux ancres séparées de plusieurs temps, les temps intermédiaires
    sont placés à intervalles égaux. `span` garde la longueur de ce trou, pour
    pouvoir écarter les notes mesurées trop loin d'une ancre.
    """
    notes = []
    off_grid = 0
    places = [0.0, 0.25, 0.5, 0.75, 1.0]
    for (number_a, j_a), (number_b, j_b) in zip(anchors, anchors[1:]):
        span = number_b - number_a
        interval = (onsets[j_b] - onsets[j_a]) / span
        notes.append({"temps": number_a, "place": 0, "fraction": 0.0, "niveau": levels[j_a], "span": 0, "t": onsets[j_a]})
        for j in range(j_a + 1, j_b):
            relative = (onsets[j] - onsets[j_a]) / interval
            whole = math.floor(relative)
            fraction = relative - whole
            place = min(range(5), key=lambda q: abs(fraction - places[q]))
            if abs(fraction - places[place]) >= tolerance:
                off_grid += 1
                continue
            if place == 4:
                whole, place, fraction = whole + 1, 0, fraction - 1.0
            notes.append(
                {"temps": number_a + whole, "place": place, "fraction": fraction, "niveau": levels[j], "span": span, "t": onsets[j]}
            )
    return notes, off_grid


def fit_spread(onsets: list[float], beat: float, first: int, tolerance: float, max_span: int) -> float:
    """Qualité d'un tempo candidat : dispersion des positions, plus petit = mieux.

    Au bon tempo, les notes d'une même place tombent toujours au même endroit
    du temps. À un tempo faux, elles s'éparpillent ou sortent de la grille.
    """
    anchors = track_beats(onsets, beat, first, tolerance)
    if len(anchors) < 3:
        return math.inf
    notes, _ = assign_slots(onsets, [0.0] * len(onsets), anchors, tolerance)
    weighted, freedom = 0.0, 0
    for place in (1, 2, 3):
        values = [n["fraction"] for n in notes if n["place"] == place and n["span"] <= max_span]
        if len(values) > 1:
            weighted += statistics.variance(values) * (len(values) - 1)
            freedom += len(values) - 1
    if freedom < 4:
        return math.inf
    unassigned = 1 - len(notes) / len(onsets)
    return math.sqrt(weighted / freedom) + 0.3 * unassigned


def estimate_beat_fit(onsets: list[float], bpm: float | None, first: int, tolerance: float, max_span: int) -> float:
    """Durée d'un temps pour un motif à trous.

    On essaie une série de tempos et on garde celui qui donne les positions
    les plus resserrées. Sans --bpm, la recherche couvre 50 à 160 bpm et peut
    se tromper d'un facteur simple (double, moitié) : mieux vaut le donner.
    """
    if bpm:
        candidates = [bpm * (0.94 + 0.005 * i) for i in range(25)]
    else:
        candidates = [50 + i for i in range(111)]
    scored = [(fit_spread(onsets, 60 / c, first, tolerance, max_span), c) for c in candidates]
    spread, best = min(scored)
    if math.isinf(spread):
        sys.exit("Aucun tempo ne permet de suivre la pulsation : vérifie --bpm et --premiere.")
    return 60 / best


def summarize_cycle(notes: list[dict], anchors: list[tuple[int, int]], onsets: list[float], cycle: int, max_span: int) -> dict:
    beats_per_cycle = cycle // 4
    total_beats = anchors[-1][0]
    mean_level = statistics.fmean(n["niveau"] for n in notes)
    intervals = [
        (onsets[j_b] - onsets[j_a]) / (b - a) for (a, j_a), (b, j_b) in zip(anchors, anchors[1:])
    ]
    beat = statistics.median(intervals)
    cases = []
    for case in range(cycle):
        beat_in_cycle, place = divmod(case, 4)
        occurrences = sum(1 for number in range(total_beats) if number % beats_per_cycle == beat_in_cycle)
        played = [n for n in notes if n["temps"] % beats_per_cycle == beat_in_cycle and n["place"] == place]
        measured = [n["fraction"] for n in played if place and n["span"] <= max_span]
        entry = {
            "case": case + 1,
            "temps": beat_in_cycle + 1,
            "double_croche": place + 1,
            "jouee": len(played) / occurrences if occurrences else 0.0,
            "n": len(measured),
            "position": statistics.fmean(measured) if measured else None,
            "ecart_type": statistics.stdev(measured) if len(measured) > 1 else None,
            "niveau_db": statistics.fmean(n["niveau"] for n in played) - mean_level if played else None,
        }
        cases.append(entry)
    pooled = []
    for place in (1, 2, 3):
        values = [n["fraction"] for n in notes if n["place"] == place and n["span"] <= max_span]
        pooled.append(
            {
                "n": len(values),
                "moyenne": statistics.fmean(values) if values else None,
                "mediane": statistics.median(values) if values else None,
                "ecart_type": statistics.stdev(values) if len(values) > 1 else None,
            }
        )
    return {
        "mode": "cycle",
        "cases_par_cycle": cycle,
        "temps_suivis": total_beats,
        "temps_ancres": len(anchors) - 1,
        "plus_long_trou": max(b - a for (a, _), (b, _) in zip(anchors, anchors[1:])),
        "notes_ecartees": sum(1 for n in notes if n["place"] and n["span"] > max_span),
        "tempo_bpm": 60 / beat,
        "cases": cases,
        "regroupe": pooled,
    }


def print_cycle_report(summary: dict, onset_count: int, off_grid: int, max_span: int) -> None:
    cycle = summary["cases_par_cycle"]
    beat_ms = 60000 / summary["tempo_bpm"]
    share = 100 * summary["temps_ancres"] / max(1, summary["temps_suivis"])
    print(f"Attaques détectées : {onset_count}")
    print(f"Cycle : {cycle} doubles-croches ({cycle // 4} temps), {summary['temps_suivis'] // (cycle // 4)} cycles complets suivis")
    print(f"Temps suivis : {summary['temps_suivis']}, dont {summary['temps_ancres']} portent une note ({share:.0f} %)")
    print(f"Plus long trou sans note sur un temps : {summary['plus_long_trou']} temps")
    print(f"Notes hors grille : {off_grid}   notes écartées (trou de plus de {max_span} temps) : {summary['notes_ecartees']}")
    print(f"Tempo médian : {summary['tempo_bpm']:.1f} bpm (un temps = {beat_ms:.0f} ms)")
    print()
    print("Motif joué (x : presque toujours, o : parfois, . : jamais ou presque)")
    marks = ["x" if c["jouee"] >= 2 / 3 else "o" if c["jouee"] >= 0.2 else "." for c in summary["cases"]]
    print("  " + " | ".join(" ".join(marks[i : i + 4]) for i in range(0, cycle, 4)))
    print()
    print("Par case (position en % du temps, grille droite : 0 · 25 · 50 · 75)")
    print("  case  temps.note   jouée   position   écart-type   écart ms   force dB     n")
    for c in summary["cases"]:
        if c["jouee"] < 0.2:
            continue
        name = f"{c['temps']}.{c['double_croche']}"
        played = f"{100 * c['jouee']:4.0f} %"
        level = "     —" if c["niveau_db"] is None else f"{c['niveau_db']:+6.1f}".replace(".", ",")
        if c["double_croche"] == 1 or c["position"] is None:
            print(f"  {c['case']:>4}  {name:>9}   {played}        —            —          —     {level}     —")
            continue
        grid = (c["double_croche"] - 1) / 4
        spread = "    —" if c["ecart_type"] is None else pct(c["ecart_type"])
        offset = (c["position"] - grid) * beat_ms
        print(f"  {c['case']:>4}  {name:>9}   {played}    {pct(c['position'])}        {spread}      {offset:+5.0f}     {level}   {c['n']:>3}")
    print()
    print("Regroupé par place dans le temps, toutes cases confondues (en %)")
    print("                       2ᵉ note   3ᵉ note   4ᵉ note")
    for label, key in [("Moyenne", "moyenne"), ("Médiane", "mediane"), ("Écart-type", "ecart_type")]:
        cells = "    ".join("    —" if p[key] is None else pct(p[key]) for p in summary["regroupe"])
        print(f"  {label:<18}  {cells}")
    print(f"  {'Nombre de notes':<18}  " + "    ".join(f"{p['n']:5d}" for p in summary["regroupe"]))
    print()
    print("Pour comparer, positions publiées (en %)")
    for name, reference in REFERENCES.items():
        cells = "    ".join("    —" if v is None else pct(v) for v in reference)
        print(f"  {name:<30}  {cells}")


def analyse_cycle(path: str, start, end, bpm, first, sensitivity, min_gap, tolerance, cycle, max_span):
    envelopes = [energy_envelope(decode(path, start, end, band)) for band in BANDS]
    if min(len(e) for e in envelopes) < 1000:
        sys.exit("Le passage est trop court ou vide.")
    onsets = pick_onsets(onset_strength(envelopes), min_gap, sensitivity)
    if len(onsets) < 8 or first >= len(onsets):
        sys.exit(f"Trop peu d'attaques détectées ({len(onsets)}).")
    levels = note_levels(envelopes, onsets)
    beat = estimate_beat_fit(onsets, bpm, first, tolerance, max_span)
    anchors = track_beats(onsets, beat, first, tolerance)
    if len(anchors) < 3:
        sys.exit("La pulsation n'a pas pu être suivie : vérifie --bpm et --premiere.")
    notes, off_grid = assign_slots(onsets, levels, anchors, tolerance)
    summary = summarize_cycle(notes, anchors, onsets, cycle, max_span)
    return onsets, anchors, summary, off_grid


# --- Statistiques et affichage -------------------------------------------


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def summarize(beats: list[dict]) -> dict:
    columns = list(zip(*(b["positions"] for b in beats)))
    level_columns = list(zip(*(b["niveaux"] for b in beats)))
    durations = [b["duree"] for b in beats]
    return {
        "temps_gardes": len(beats),
        "tempo_bpm": 60 / statistics.median(durations),
        "moyenne": [statistics.fmean(c) for c in columns],
        "mediane": [statistics.median(c) for c in columns],
        "ecart_type": [statistics.stdev(c) if len(c) > 1 else 0.0 for c in columns],
        "p10": [percentile(list(c), 0.1) for c in columns],
        "p90": [percentile(list(c), 0.9) for c in columns],
        "niveau_db": [statistics.fmean(c) for c in level_columns],
    }


def pct(value: float) -> str:
    return f"{value * 100:5.1f}".replace(".", ",")


def print_report(summary: dict, rejected: int, onset_count: int, lost_at: float | None) -> None:
    n = summary["temps_gardes"]
    beat_ms = 60000 / summary["tempo_bpm"]
    print(f"Attaques détectées : {onset_count}")
    print(f"Temps gardés : {n}   rejetés : {rejected}")
    if lost_at is not None:
        print(f"Attention : la pulsation est perdue après {lost_at:.1f} s, la suite n'est pas analysée.")
    print(f"Tempo médian : {summary['tempo_bpm']:.1f} bpm (un temps = {beat_ms:.0f} ms)")
    print()
    print("Position dans le temps, en % (grille droite : 25 · 50 · 75)")
    print("                       2ᵉ note   3ᵉ note   4ᵉ note")
    for label, key in [("Moyenne", "moyenne"), ("Médiane", "mediane"), ("10ᵉ centile", "p10"), ("90ᵉ centile", "p90")]:
        print(f"  {label:<18}  " + "    ".join(pct(v) for v in summary[key]))
    print("  Écart-type          " + "    ".join(pct(v) for v in summary["ecart_type"]))
    errors = [sd / math.sqrt(n) for sd in summary["ecart_type"]]
    print("  Erreur sur moyenne  " + "    ".join(pct(v) for v in errors))
    print()
    offsets = [(m - g) * beat_ms for m, g in zip(summary["moyenne"], GRID)]
    print("Écart à la grille, en ms (négatif = en avance)")
    print("                      " + "    ".join(f"{v:+5.0f}" for v in offsets))
    print()
    print("Force des notes, en dB par rapport à la moyenne du temps")
    print("  note 1 à 4 :  " + "   ".join(f"{v:+5.1f}".replace(".", ",") for v in summary["niveau_db"]))
    print()
    print("Pour comparer, positions publiées (en %)")
    for name, reference in REFERENCES.items():
        cells = "    ".join("    —" if v is None else pct(v) for v in reference)
        print(f"  {name:<30}  {cells}")
    print(f"  {'Cette mesure':<30}  " + "    ".join(pct(v) for v in summary["moyenne"]))


# --- Chaîne complète ------------------------------------------------------


def analyse(path: str, start, end, bpm, first, sensitivity, min_gap, tolerance):
    envelopes = [energy_envelope(decode(path, start, end, band)) for band in BANDS]
    if min(len(e) for e in envelopes) < 1000:
        sys.exit("Le passage est trop court ou vide.")
    onsets = pick_onsets(onset_strength(envelopes), min_gap, sensitivity)
    levels = note_levels(envelopes, onsets)
    beat = estimate_beat(onsets, bpm)
    kept, rejected, lost_at = segment(onsets, levels, beat, first, tolerance)
    return onsets, kept, rejected, lost_at


def synthesize(path: Path, positions: list[float], bpm: float, beats: int, jitter_ms: float, mask: list[int] | None = None) -> None:
    """Écrit un WAV de cordes grattées au swing connu, pour tester le script."""
    rng = random.Random(7)
    strings = [293.66, 392.0, 493.88, 587.33]  # ré sol si ré, l'accord du cavaquinho
    beat = 60 / bpm
    signal = [0.0] * int((beats + 2) * beat * SR * 1.02 + SR)
    note_length = int(0.14 * SR)
    start = 0.3
    for b in range(beats + 1):
        duration = beat * (1 + 0.01 * math.sin(b / 7))  # léger flottement de tempo
        for i, position in enumerate([0.0] + positions):
            if mask and not mask[(b * 4 + i) % len(mask)]:
                continue  # silence : la note n'est pas jouée
            onset = start + position * duration + rng.gauss(0, jitter_ms / 1000)
            order = strings if i % 2 == 0 else strings[::-1]  # aller puis retour
            gain = 0.9 if i == 1 else 0.55  # 2ᵉ note accentuée
            for k, frequency in enumerate(order):
                first_sample = int((onset + k * 0.003) * SR)  # cordes grattées l'une après l'autre
                step = 2 * math.pi * frequency / SR
                for n in range(note_length):
                    decay = math.exp(-n / (0.035 * SR))
                    click = rng.uniform(-1, 1) * math.exp(-n / (0.002 * SR))
                    signal[first_sample + n] += gain * decay * (
                        math.sin(step * n) + 0.5 * math.sin(2 * step * n) + 0.4 * click
                    )
        start += duration
    peak = max(abs(v) for v in signal) or 1
    pcm = array("h", (int(30000 * v / peak) for v in signal))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        out.writeframes(pcm.tobytes())


def autotest() -> int:
    """Vérifie que le script retrouve un swing connu sur un signal de synthèse."""
    truth = [0.27, 0.44, 0.67]
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "test.wav"
        print("Synthèse d'un signal de test (48 temps à 100 bpm, swing 27 · 44 · 67 %)…")
        synthesize(path, truth, bpm=100, beats=48, jitter_ms=4)
        onsets, kept, rejected, lost_at = analyse(str(path), None, None, None, 0, 1.0, 0.05, 0.12)
    if len(kept) < 2:
        print("ÉCHEC : presque aucun temps reconnu.")
        return 1
    summary = summarize(kept)
    print_report(summary, rejected, len(onsets), lost_at)
    print()
    errors = [abs(m - t) for m, t in zip(summary["moyenne"], truth)]
    ok = max(errors) < 0.01 and len(kept) >= 40 and summary["niveau_db"][1] == max(summary["niveau_db"])
    print("Attendu : 27,0 · 44,0 · 67,0   erreur maximale : " + f"{max(errors) * 100:.2f}".replace(".", ",") + " % du temps")
    print("TEST 1 RÉUSSI" if ok else "TEST 1 EN ÉCHEC")

    # Second test : un motif à trous sur 16 cases, dont deux temps sans note.
    mask = [1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 0, 1, 1, 0]
    print()
    print("Synthèse d'un motif à trous (40 temps à 96 bpm, même swing), mode --cycle 16…")
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "cycle.wav"
        synthesize(path, truth, bpm=96, beats=40, jitter_ms=4, mask=mask)
        onsets, anchors, cycle_summary, off_grid = analyse_cycle(str(path), None, None, None, 0, 1.0, 0.05, 0.12, 16, 4)
    print_cycle_report(cycle_summary, len(onsets), off_grid, 4)
    found = [1 if c["jouee"] >= 2 / 3 else 0 for c in cycle_summary["cases"]]
    pooled = [p["moyenne"] for p in cycle_summary["regroupe"]]
    cycle_errors = [abs(m - t) for m, t in zip(pooled, truth)] if None not in pooled else [1.0]
    ok_cycle = found == mask and max(cycle_errors) < 0.012 and abs(cycle_summary["tempo_bpm"] - 96) < 1.5
    print()
    print("Motif attendu : " + " ".join("x" if v else "." for v in mask))
    print("Erreur maximale sur les positions regroupées : " + f"{max(cycle_errors) * 100:.2f}".replace(".", ",") + " % du temps")
    print("TEST 2 RÉUSSI" if ok_cycle else "TEST 2 EN ÉCHEC")
    print()
    print("AUTOTEST RÉUSSI" if ok and ok_cycle else "AUTOTEST EN ÉCHEC")
    return 0 if ok and ok_cycle else 1


def parse_time(text: str) -> float:
    """Lit un instant en secondes (72.5) ou en minutage (1:12.5, 1:02:03)."""
    try:
        parts = [float(part.replace(",", ".")) for part in text.strip().split(":")]
    except ValueError:
        raise argparse.ArgumentTypeError(f"instant illisible : {text!r} (exemples : 72.5 ou 1:12.5)")
    if not 1 <= len(parts) <= 3 or any(part < 0 for part in parts) or any(part >= 60 for part in parts[1:]):
        raise argparse.ArgumentTypeError(f"instant illisible : {text!r} (exemples : 72.5 ou 1:12.5)")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return seconds


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fichier", nargs="?", help="fichier audio ou vidéo (tout format lu par ffmpeg)")
    parser.add_argument("--debut", type=parse_time, help="début du passage : secondes (72.5) ou minutage (1:12.5)")
    parser.add_argument("--fin", type=parse_time, help="fin du passage : secondes (125) ou minutage (2:05)")
    parser.add_argument("--bpm", type=float, help="tempo approximatif ; estimé automatiquement sinon")
    parser.add_argument("--premiere", type=int, default=1, help="numéro de la première attaque qui tombe sur un temps (défaut : 1)")
    parser.add_argument("--phases", action="store_true", help="affiche le résultat pour les quatre calages possibles")
    parser.add_argument("--sensibilite", type=float, default=1.0, help="plus grand = détecte des notes plus faibles (défaut : 1)")
    parser.add_argument("--ecart-min", type=float, default=0.05, help="écart minimal entre deux attaques, en secondes (défaut : 0,05)")
    parser.add_argument("--tolerance", type=float, default=0.12, help="écart maximal à la grille, en fraction du temps (défaut : 0,12)")
    parser.add_argument("--cycle", type=int, help="motif avec silences : nombre de doubles-croches du cycle (16 = 4 temps)")
    parser.add_argument("--trou-max", type=int, default=4, help="mode cycle : n'utilise pas les notes mesurées dans un trou plus long, en temps (défaut : 4)")
    parser.add_argument("--json", help="écrit le détail et un bloc de groove dans ce fichier JSON")
    parser.add_argument("--labels", help="écrit les attaques dans une piste de marqueurs Audacity")
    parser.add_argument("--autotest", action="store_true", help="vérifie le script sur un signal de synthèse")
    args = parser.parse_args()

    if args.autotest:
        return autotest()
    if not args.fichier:
        parser.error("indique un fichier, ou --autotest")
    if args.debut is not None and args.fin is not None and args.fin <= args.debut:
        parser.error("--fin doit être après --debut")
    if not Path(args.fichier).is_file():
        sys.exit(f"Fichier introuvable : {args.fichier}")

    offset = args.debut or 0.0
    if args.cycle:
        if args.cycle % 4 or args.cycle < 4:
            parser.error("--cycle doit être un multiple de 4 (4, 8, 16…)")
        onsets, anchors, summary, off_grid = analyse_cycle(
            args.fichier, args.debut, args.fin, args.bpm, args.premiere - 1,
            args.sensibilite, args.ecart_min, args.tolerance, args.cycle, args.trou_max,
        )
        print_cycle_report(summary, len(onsets), off_grid, args.trou_max)
        if args.labels:
            anchor_indices = {j for _, j in anchors}
            with open(args.labels, "w", encoding="utf-8") as out:
                for index, t in enumerate(onsets):
                    label = "T" if index in anchor_indices else "x"
                    out.write(f"{t + offset:.6f}\t{t + offset:.6f}\t{label}\n")
            print(f"\nMarqueurs Audacity écrits dans {args.labels}")
        if args.json:
            pooled = [p["moyenne"] for p in summary["regroupe"]]
            payload = {"fichier": Path(args.fichier).name, "passage_s": [args.debut, args.fin], **summary}
            if None not in pooled:
                payload["groove"] = {"grid": [0, 0.25, 0.5, 0.75], "target": [0] + [round(v, 3) for v in pooled]}
            Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\nDétail écrit dans {args.json}")
        return 0
    if args.phases:
        for first in range(4):
            onsets, kept, rejected, _ = analyse(
                args.fichier, args.debut, args.fin, args.bpm, first, args.sensibilite, args.ecart_min, args.tolerance
            )
            if len(kept) < 2:
                print(f"--premiere {first + 1} : trop peu de temps reconnus")
                continue
            s = summarize(kept)
            print(
                f"--premiere {first + 1} : {len(kept):3d} temps, positions "
                + " · ".join(pct(v).strip() for v in s["moyenne"])
                + "   force "
                + " ".join(f"{v:+.1f}".replace(".", ",") for v in s["niveau_db"])
            )
        return 0

    onsets, kept, rejected, lost_at = analyse(
        args.fichier, args.debut, args.fin, args.bpm, args.premiere - 1, args.sensibilite, args.ecart_min, args.tolerance
    )
    if args.labels:
        beat_starts = {round(b["debut"], 6) for b in kept}
        with open(args.labels, "w", encoding="utf-8") as out:
            for t in onsets:
                label = "T" if round(t, 6) in beat_starts else "x"
                out.write(f"{t + offset:.6f}\t{t + offset:.6f}\t{label}\n")
        print(f"Marqueurs Audacity écrits dans {args.labels}")
    if len(kept) < 2:
        print(f"Attaques détectées : {len(onsets)}. Temps reconnus : {len(kept)}, rejetés : {rejected}.")
        print("Pas assez de temps exploitables. Pistes : --bpm, --premiere, --sensibilite, ou un passage plus régulier.")
        return 1
    summary = summarize(kept)
    print_report(summary, rejected, len(onsets), None if lost_at is None else lost_at + offset)
    if args.json:
        payload = {
            "fichier": Path(args.fichier).name,
            "passage_s": [args.debut, args.fin],
            "temps_rejetes": rejected,
            **summary,
            "groove": {
                "grid": [0, 0.25, 0.5, 0.75],
                "target": [0] + [round(v, 3) for v in summary["moyenne"]],
            },
            "par_temps": [
                {"debut_s": round(b["debut"] + offset, 4), "positions": [round(v, 4) for v in b["positions"]]}
                for b in kept
            ],
        }
        Path(args.json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nDétail écrit dans {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

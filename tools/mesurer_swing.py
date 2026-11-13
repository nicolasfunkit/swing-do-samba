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
    python3 tools/mesurer_swing.py cavaco.mp4 --debut 12 --fin 45 --json cavaco.json --labels cavaco.txt
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


def synthesize(path: Path, positions: list[float], bpm: float, beats: int, jitter_ms: float) -> None:
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
    print("AUTOTEST RÉUSSI" if ok else "AUTOTEST EN ÉCHEC")
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fichier", nargs="?", help="fichier audio ou vidéo (tout format lu par ffmpeg)")
    parser.add_argument("--debut", type=float, help="début du passage à analyser, en secondes")
    parser.add_argument("--fin", type=float, help="fin du passage à analyser, en secondes")
    parser.add_argument("--bpm", type=float, help="tempo approximatif ; estimé automatiquement sinon")
    parser.add_argument("--premiere", type=int, default=1, help="numéro de la première attaque qui tombe sur un temps (défaut : 1)")
    parser.add_argument("--phases", action="store_true", help="affiche le résultat pour les quatre calages possibles")
    parser.add_argument("--sensibilite", type=float, default=1.0, help="plus grand = détecte des notes plus faibles (défaut : 1)")
    parser.add_argument("--ecart-min", type=float, default=0.05, help="écart minimal entre deux attaques, en secondes (défaut : 0,05)")
    parser.add_argument("--tolerance", type=float, default=0.12, help="écart maximal à la grille, en fraction du temps (défaut : 0,12)")
    parser.add_argument("--json", help="écrit le détail et un bloc de groove dans ce fichier JSON")
    parser.add_argument("--labels", help="écrit les attaques dans une piste de marqueurs Audacity")
    parser.add_argument("--autotest", action="store_true", help="vérifie le script sur un signal de synthèse")
    args = parser.parse_args()

    if args.autotest:
        return autotest()
    if not args.fichier:
        parser.error("indique un fichier, ou --autotest")
    if not Path(args.fichier).is_file():
        sys.exit(f"Fichier introuvable : {args.fichier}")

    offset = args.debut or 0.0
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

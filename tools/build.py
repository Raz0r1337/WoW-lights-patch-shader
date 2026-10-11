"""Baut aus den eigenen WoW-Shadern die 8-Lichter-Fassung als Ordner im MPQ-Aufbau.

Aufruf:
    python3 tools/build.py QUELLE ZIEL [--name patch-5.MPQ]

QUELLE  Ordner mit den ausgepackten MPQs, je MPQ ein Unterordner, der wie das
        MPQ heißt, z. B. QUELLE/patch.MPQ/Shaders/..., QUELLE/patch-3.MPQ/...
        (Groß-/Kleinschreibung egal). Es zählt wie im Spiel jeweils die Datei
        aus dem MPQ mit dem höchsten Rang (patch-3 vor patch-2 vor patch vor
        den Grund-MPQs).
ZIEL    Hier entsteht ZIEL/<name>/Shaders/Vertex/vs_2_0|vs_3_0/*.bls.
        Für das Spiel ist ZIEL der Data-Ordner.

Es werden nur Dateien geschrieben, die sich ändern (Modell- und Gebäude-
Shader mit 4-Lichter-Varianten), und nur für vs_2_0 und vs_3_0.
"""

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bls      # noqa: E402
import lights8  # noqa: E402

PROFILES = ('vs_2_0', 'vs_3_0')
BASE_ORDER = ['common', 'common-2', 'expansion', 'lichking']


def mpq_rank(name):
    """Ladereihenfolge des Spiels: höherer Rang überschreibt niedrigeren."""
    n = name.lower()
    n = re.sub(r'\.(mpq|mq)$', '', n)
    m = re.fullmatch(r'patch(?:-(.))?', n)
    if m:
        c = m.group(1)
        return 1000 + (0 if c is None else ord(c))
    if n in BASE_ORDER:
        return 100 + BASE_ORDER.index(n)
    return 0


def find_ci(root, *parts):
    """Pfad unterhalb root ohne Rücksicht auf Groß-/Kleinschreibung finden."""
    cur = root
    for p in parts:
        try:
            names = {e.lower(): e for e in os.listdir(cur)}
        except OSError:
            return None
        if p.lower() not in names:
            return None
        cur = os.path.join(cur, names[p.lower()])
    return cur


def effective_files(src):
    """{(profil, dateiname_klein): (pfad, mpq)} – jeweils die gewinnende Datei."""
    archives = sorted((d for d in os.listdir(src) if os.path.isdir(os.path.join(src, d))),
                      key=mpq_rank)
    eff = {}
    for a in archives:
        for prof in PROFILES:
            d = find_ci(os.path.join(src, a), 'shaders', 'vertex', prof)
            if not d:
                continue
            for f in os.listdir(d):
                if f.lower().endswith('.bls'):
                    eff[(prof, f.lower())] = (os.path.join(d, f), a)
    return eff


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('quelle')
    ap.add_argument('ziel')
    ap.add_argument('--name', default='patch-5.MPQ')
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--debug', action='store_const', const='magenta', dest='debug',
                   help='Testfassung: Licht 5–8 leuchten Magenta statt in ihrer Farbe')
    g.add_argument('--ladetest', action='store_const', const='ladetest', dest='debug',
                   help='Ladetest: alle Lichter 1–8 leuchten Magenta (zeigt, ob die Shader geladen werden)')
    args = ap.parse_args(argv)

    eff = effective_files(args.quelle)
    if not eff:
        print('Keine Shader gefunden. Erwartet: QUELLE/<MPQ-Name>/Shaders/Vertex/vs_3_0/...')
        return 1
    out_root = os.path.join(args.ziel, args.name, 'Shaders', 'Vertex')
    written = 0
    errors = 0
    for (prof, _), (path, mpq) in sorted(eff.items()):
        fname = os.path.basename(path)
        data = open(path, 'rb').read()
        if not data:
            print(f'  übersprungen (leere Datei in {mpq}): {prof}/{fname}')
            continue
        try:
            f = bls.parse(data)
        except ValueError as e:
            print(f'  übersprungen ({e}): {mpq} {prof}/{fname}')
            continue
        changed = 0
        try:
            for v in f.variants:
                new = lights8.patch_variant_code(v.code, args.debug)
                if new is not None:
                    v.code = new
                    changed += 1
        except lights8.PatchError as e:
            print(f'  FEHLER {mpq} {prof}/{fname}: {e}')
            errors += 1
            continue
        if not changed:
            continue
        out = bls.build(f)
        bls.parse(out)  # Gegenprobe: Ergebnis muss sich wieder lesen lassen
        d = os.path.join(out_root, prof)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, fname), 'wb') as fh:
            fh.write(out)
        written += 1
        print(f'  {prof}/{fname}: {changed} Varianten erweitert (aus {mpq})')
    print(f'{written} Dateien geschrieben nach {os.path.join(args.ziel, args.name)}, {errors} Fehler')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())

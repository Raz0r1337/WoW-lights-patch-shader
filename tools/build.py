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
Shader mit 4-Lichter-Varianten sowie Terrain.bls, Boden 3 -> 8 Lichter), und
nur für vs_2_0 und vs_3_0. Der Boden setzt den Exe-Teil für den Boden voraus
(Patch Nr. 69 ab 2026-10-12, siehe docs/BODEN.de.md); --ohne-boden lässt
Terrain.bls weg, etwa für eine Exe mit einem älteren Stand des Patches.
--nur modelle|gebaeude|boden (mehrfach erlaubt) baut nur diese Gruppe(n),
zum Eingrenzen von Fehlern: modelle = Diffuse_*/CDiffuse_T1 (M2),
gebaeude = MapObj* (WMO), boden = Terrain.bls.
"""

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bls       # noqa: E402
import lights8   # noqa: E402
import terrain8  # noqa: E402

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


GRUPPEN = ('modelle', 'gebaeude', 'boden')


def gruppe(fname):
    """Gruppe einer Shader-Datei: boden (Terrain.bls), gebaeude (MapObj*), sonst modelle."""
    n = fname.lower()
    if n == 'terrain.bls':
        return 'boden'
    if n.startswith('mapobj'):
        return 'gebaeude'
    return 'modelle'


def collect_bls(paths):
    """Shader-Dateien für die Tests.

    Jeder Pfad ist entweder ein Ordner mit vs_2_0/ und vs_3_0/ darunter (dann alle
    .bls darin) oder ein QUELLE-Ordner wie beim Bauen (dann nur die wirksamen
    Dateien, also genau die, aus denen build.py baut; überdeckte Fassungen aus
    älteren MPQs bleiben außen vor).
    """
    out = []
    for p in paths:
        eff = effective_files(p) if os.path.isdir(p) else {}
        if eff:
            out.extend(path for _, (path, _) in sorted(eff.items()))
        else:
            out.extend(sorted(glob.glob(os.path.join(p, 'vs_[23]_0', '*.bls'))))
    return out


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
    ap.add_argument('--ohne-boden', action='store_false', dest='boden',
                    help='den Boden-Shader (Terrain.bls) nicht erweitern, nur Modelle und Gebäude '
                         '(für eine Exe, deren Patch Nr. 69 den Boden-Teil noch nicht hat)')
    ap.add_argument('--boden', action='store_true', dest='boden', help=argparse.SUPPRESS)  # alter Schalter, heute Standard
    ap.add_argument('--nur', action='append', choices=sorted(GRUPPEN), metavar='GRUPPE',
                    help='nur diese Gruppe bauen (mehrfach erlaubt): modelle (Diffuse_*, CDiffuse_T1), '
                         'gebaeude (MapObj*), boden (Terrain.bls); zum Eingrenzen von Fehlern')
    args = ap.parse_args(argv)
    if args.nur and 'boden' in args.nur and not args.boden:
        print('--nur boden und --ohne-boden schließen sich aus')
        return 2

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
        is_terrain = fname.lower() == 'terrain.bls'
        if args.nur and gruppe(fname) not in args.nur:
            continue
        try:
            for v in f.variants:
                if is_terrain:
                    new = terrain8.patch_variant_code(v.code) if args.boden else None
                else:
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

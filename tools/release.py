"""Baut das Release-Paket aus der Quelle und prüft es.

Aufruf:
    python3 tools/release.py QUELLE AUSGABE [--version v1.0.0]
                             [--summen-schreiben] [--ohne-tests]

QUELLE   Zip oder Ordner mit den Original-Shadern, je MPQ ein Unterordner wie
         bei build.py (QUELLE/patch.MPQ/Shaders/Vertex/vs_3_0/... usw.). Bei
         einem Zip darf darüber noch ein Ordner liegen, er wird gefunden.
AUSGABE  Hier entstehen patch-5.MPQ.zip, patch-5.MPQ_ohne_Boden.zip,
         patch-5.MPQ_Testfassung_Magenta.zip, SHA256SUMS.txt und
         RELEASE_NOTES.md (dazu die Arbeitsordner quelle/ und bau/).

Schritte, jeweils mit Abbruch bei Fehlern:
  1. Quelle entpacken und ihren Wurzelordner finden; Prüfsummen der Quelle mit
     tests/pruefsummen/quelle.sha256 vergleichen (nur Hinweis).
  2. Die drei Fassungen mit build.py bauen.
  3. Emulator-Tests (tests/test_lights8.py, auch --debug, tests/test_terrain8.py)
     auf genau den wirksamen Quelldateien.
  4. Prüfsummen der gebauten Dateien mit tests/pruefsummen/<Fassung>.sha256
     vergleichen: Die Ausgabe muss bitgleich der im Spiel bestätigten Fassung
     sein. --summen-schreiben schreibt die Dateien stattdessen neu (nur nach
     einer bewussten Änderung an Quelle oder Werkzeug, danach neu im Spiel
     testen).
  5. Zips packen (tools/paket.py), SHA256SUMS.txt und RELEASE_NOTES.md aus
     .github/release-notizen.de.md schreiben.

Dieselben Schritte laufen im GitHub-Lauf (.github/workflows/release.yml).
"""

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import build    # noqa: E402
import paket    # noqa: E402

ORDNER = 'patch-5.MPQ'
FASSUNGEN = [
    # (Zip-Name ohne .zip, build.py-Schalter, Testaufruf-Schalter für test_lights8)
    ('patch-5.MPQ', [], None),
    ('patch-5.MPQ_ohne_Boden', ['--ohne-boden'], None),
    ('patch-5.MPQ_Testfassung_Magenta', ['--debug'], '--debug'),
]
SUMMEN_DIR = os.path.join(REPO, 'tests', 'pruefsummen')
VORLAGE = os.path.join(REPO, '.github', 'release-notizen.de.md')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def summen_lesen(path):
    out = {}
    if not os.path.exists(path):
        return None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip('\n')
        if not line or line.startswith('#'):
            continue
        digest, name = line.split('  ', 1)
        out[name] = digest
    return out


def summen_schreiben(path, summen):
    with open(path, 'w', encoding='utf-8', newline='\n') as fh:
        for name in sorted(summen):
            fh.write(f'{summen[name]}  {name}\n')


def ordner_summen(root):
    """{relativer Pfad mit /: sha256} aller Dateien unter root."""
    out = {}
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            out[os.path.relpath(p, root).replace(os.sep, '/')] = sha256(p)
    return out


def quelle_schluessel(root):
    """Prüfsummen der Quelle mit vereinheitlichten Namen (Kleinschreibung,
    MPQ-Endung .mpq), damit Groß-/Kleinschreibung keine Rolle spielt."""
    out = {}
    for rel, digest in ordner_summen(root).items():
        parts = rel.lower().split('/')
        parts[0] = re.sub(r'\.(mpq|mq)$', '.mpq', parts[0])
        out['/'.join(parts)] = digest
    return out


def vergleich(ist, soll):
    """Gibt (fehlend, zusätzlich, abweichend) zurück."""
    fehlend = sorted(k for k in soll if k not in ist)
    zusaetzlich = sorted(k for k in ist if k not in soll)
    abweichend = sorted(k for k in soll if k in ist and ist[k] != soll[k])
    return fehlend, zusaetzlich, abweichend


def quelle_bereitstellen(quelle, arbeit):
    """Entpackt ein Zip nach arbeit/quelle und liefert den Wurzelordner, der
    die MPQ-Unterordner enthält."""
    if os.path.isdir(quelle):
        root = quelle
    else:
        ziel = os.path.join(arbeit, 'quelle')
        shutil.rmtree(ziel, ignore_errors=True)
        os.makedirs(ziel)
        with zipfile.ZipFile(quelle) as z:
            for info in z.infolist():
                name = info.filename.replace('\\', '/')
                if name.startswith('/') or '..' in name.split('/'):
                    raise SystemExit(f'Unzulässiger Pfad im Zip: {info.filename}')
            z.extractall(ziel)
        root = ziel
    # Wurzel = der Ordner, dessen Unterordner <MPQ>/Shaders/Vertex enthalten
    kandidaten = {}
    for d, dirs, _ in os.walk(root):
        for sub in dirs:
            if sub.lower() == 'shaders' and build.find_ci(os.path.join(d, sub), 'vertex'):
                wurzel = os.path.dirname(d)
                kandidaten[wurzel] = kandidaten.get(wurzel, 0) + 1
    if not kandidaten:
        raise SystemExit('In der Quelle wurde kein Ordner <MPQ>/Shaders/Vertex gefunden.')
    wurzel = max(kandidaten, key=lambda k: (kandidaten[k], -len(k)))
    mpqs = sorted(e for e in os.listdir(wurzel) if os.path.isdir(os.path.join(wurzel, e)))
    print(f'Quelle: {wurzel}\n  MPQ-Ordner: {", ".join(mpqs)}')
    return wurzel


def lauf(cmd, name):
    print(f'\n== {name}: python3 {" ".join(os.path.relpath(c, REPO) if c.startswith(REPO) else c for c in cmd[1:])}')
    r = subprocess.run(cmd, cwd=REPO, text=True, capture_output=True)
    zeilen = (r.stdout + r.stderr).strip().splitlines()
    for z in zeilen[-15:]:
        print('  ' + z)
    if r.returncode:
        raise SystemExit(f'{name} fehlgeschlagen (Rückgabe {r.returncode})')
    return zeilen[-1] if zeilen else ''


def commit_hash():
    sha = os.environ.get('GITHUB_SHA')
    if sha:
        return sha
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True,
                              capture_output=True, check=True).stdout.strip()
    except Exception:
        return 'unbekannt'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('quelle')
    ap.add_argument('ausgabe')
    ap.add_argument('--version', default='', help='Versions-Tag für die Release-Notizen, z. B. v1.0.0')
    ap.add_argument('--summen-schreiben', action='store_true',
                    help='Prüfsummen-Dateien unter tests/pruefsummen/ neu schreiben statt vergleichen')
    ap.add_argument('--ohne-tests', action='store_true', help='Emulator-Tests überspringen (nur zum Ausprobieren)')
    args = ap.parse_args(argv)

    ausgabe = os.path.abspath(args.ausgabe)
    os.makedirs(ausgabe, exist_ok=True)
    epoch = int(os.environ.get('SOURCE_DATE_EPOCH') or time.time())  # Zeitstempel im Zip
    datum = time.strftime('%Y-%m-%d', time.gmtime())                  # Tag des Laufs
    os.makedirs(SUMMEN_DIR, exist_ok=True)

    # 1. Quelle
    print('== Quelle bereitstellen')
    quelle = quelle_bereitstellen(os.path.abspath(args.quelle), ausgabe)
    ist = quelle_schluessel(quelle)
    pfad = os.path.join(SUMMEN_DIR, 'quelle.sha256')
    if args.summen_schreiben:
        summen_schreiben(pfad, ist)
        print(f'  Prüfsummen der Quelle geschrieben: {os.path.relpath(pfad, REPO)} ({len(ist)} Dateien)')
    else:
        soll = summen_lesen(pfad)
        if soll is None:
            print('  Hinweis: keine Prüfsummen der Quelle hinterlegt')
        else:
            fehlend, zusaetzlich, abweichend = vergleich(ist, soll)
            if not (fehlend or abweichend):
                print(f'  Quelle stimmt mit den hinterlegten Prüfsummen überein ({len(soll)} Dateien'
                      + (f', {len(zusaetzlich)} zusätzliche)' if zusaetzlich else ')'))
            else:
                print('  HINWEIS: Quelle weicht von den hinterlegten Prüfsummen ab:')
                for k in fehlend[:20]:
                    print(f'    fehlt:      {k}')
                for k in abweichend[:20]:
                    print(f'    verändert:  {k}')
                print('  Die Ausgabe wird darum vermutlich nicht bitgleich sein (siehe Schritt 4).')

    # 2. Bauen
    bau = os.path.join(ausgabe, 'bau')
    shutil.rmtree(bau, ignore_errors=True)
    gebaut = {}
    for name, schalter, _ in FASSUNGEN:
        ziel = os.path.join(bau, name)
        print(f'\n== Bauen: {name} {" ".join(schalter)}')
        rc = build.main([quelle, ziel, '--name', ORDNER] + schalter)
        if rc:
            raise SystemExit(f'Bauen von {name} fehlgeschlagen')
        gebaut[name] = os.path.join(ziel, ORDNER)

    # 3. Tests
    if args.ohne_tests:
        print('\n== Tests übersprungen (--ohne-tests)')
    else:
        py = sys.executable
        ergebnisse = [
            lauf([py, os.path.join(REPO, 'tests', 'test_lights8.py'), quelle], 'Test Modelle/Gebäude'),
            lauf([py, os.path.join(REPO, 'tests', 'test_lights8.py'), '--debug', quelle], 'Test Testfassung (Magenta)'),
            lauf([py, os.path.join(REPO, 'tests', 'test_terrain8.py'), quelle], 'Test Boden'),
        ]

    # 4. Prüfsummen der Ausgabe
    print('\n== Prüfsummen der gebauten Dateien')
    for name, _, _ in FASSUNGEN:
        ist = {f'{ORDNER}/{k}': v for k, v in ordner_summen(gebaut[name]).items()}
        pfad = os.path.join(SUMMEN_DIR, name + '.sha256')
        if args.summen_schreiben:
            summen_schreiben(pfad, ist)
            print(f'  geschrieben: {os.path.relpath(pfad, REPO)} ({len(ist)} Dateien)')
            continue
        soll = summen_lesen(pfad)
        if soll is None:
            raise SystemExit(f'Keine Prüfsummen für {name} unter {os.path.relpath(pfad, REPO)}; '
                             f'einmal mit --summen-schreiben laufen lassen.')
        fehlend, zusaetzlich, abweichend = vergleich(ist, soll)
        if fehlend or zusaetzlich or abweichend:
            print(f'  FEHLER {name}: Ausgabe weicht von der bestätigten Fassung ab')
            for k in fehlend:
                print(f'    fehlt:      {k}')
            for k in zusaetzlich:
                print(f'    zusätzlich: {k}')
            for k in abweichend:
                print(f'    verändert:  {k}')
            raise SystemExit('Prüfsummen stimmen nicht. Wenn die Abweichung gewollt ist (neue Quelle oder '
                             'geändertes Werkzeug): lokal mit --summen-schreiben neu erzeugen, im Spiel '
                             'testen und die Dateien unter tests/pruefsummen/ einchecken.')
        print(f'  {name}: {len(ist)} Dateien bitgleich mit der bestätigten Fassung')

    # 5. Packen
    print('\n== Packen')
    zips = []
    for name, _, _ in FASSUNGEN:
        zip_path = os.path.join(ausgabe, name + '.zip')
        n = paket.pack(gebaut[name], zip_path, epoch)
        zips.append((name + '.zip', n, sha256(zip_path), os.path.getsize(zip_path)))
        print(f'  {name}.zip: {n} Dateien, {os.path.getsize(zip_path)} Byte')
    with open(os.path.join(ausgabe, 'SHA256SUMS.txt'), 'w', encoding='utf-8', newline='\n') as fh:
        for zname, _, digest, _ in zips:
            fh.write(f'{digest}  {zname}\n')

    vorlage = open(VORLAGE, encoding='utf-8').read()
    n = {name: cnt for (name, cnt, _, _) in ((z[0][:-4], z[1], z[2], z[3]) for z in zips)}
    commit = commit_hash()
    notizen = vorlage.format(
        version=args.version or '(Probelauf)',
        datum=datum,
        commit=commit,
        commit_kurz=commit[:7],
        repo=os.environ.get('GITHUB_REPOSITORY', 'Raz0r1337/WoW-lights-patch-shader'),
        n_standard=n['patch-5.MPQ'],
        n_ohne_boden=n['patch-5.MPQ_ohne_Boden'],
        n_testfassung=n['patch-5.MPQ_Testfassung_Magenta'],
    )
    with open(os.path.join(ausgabe, 'RELEASE_NOTES.md'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(notizen)
    print(f'\nFertig: {ausgabe}')
    for zname, cnt, digest, size in zips:
        print(f'  {digest}  {zname}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

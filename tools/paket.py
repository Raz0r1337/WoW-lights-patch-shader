"""Packt einen gebauten Ordner (z. B. patch-5.MPQ) in ein Zip.

Aufruf:
    python3 tools/paket.py ORDNER [ZIP]

Das Zip hat denselben Aufbau wie das im Projekt angebotene patch-5.MPQ.zip:
oberste Ebene ist der Ordner selbst (patch-5.MPQ/Shaders/Vertex/...), Ordner
haben eigene Einträge, Dateien sind deflate-gepackt, Reihenfolge sortiert.
Entpackt im Data-Ordner des Spiels ergibt es direkt Data\\patch-5.MPQ\\...

Die Zeitstempel im Zip kommen aus SOURCE_DATE_EPOCH (Sekunden seit 1970),
sonst aus der Uhr. Mit festem SOURCE_DATE_EPOCH ist das Zip bei gleichem
Inhalt bitgleich reproduzierbar.
"""

import argparse
import os
import sys
import time
import zipfile


def pack(folder, zip_path, epoch=None):
    """Packt folder nach zip_path. Gibt die Zahl der Dateien zurück."""
    folder = os.path.abspath(folder)
    name = os.path.basename(folder)
    if epoch is None:
        epoch = int(os.environ.get('SOURCE_DATE_EPOCH') or time.time())
    date_time = time.gmtime(max(epoch, 315532800))[:6]  # ZIP kennt nichts vor 1980
    entries = []
    for root, dirs, files in os.walk(folder):
        dirs.sort()
        files.sort()
        rel = os.path.relpath(root, folder)
        arc = name if rel == '.' else name + '/' + rel.replace(os.sep, '/')
        entries.append((arc + '/', None))
        for f in files:
            entries.append((arc + '/' + f, os.path.join(root, f)))
    count = 0
    with zipfile.ZipFile(zip_path, 'w') as z:
        for arc, path in entries:
            zi = zipfile.ZipInfo(arc, date_time)
            zi.create_system = 3  # Unix: Rechte in external_attr gelten
            if path is None:
                zi.external_attr = (0o40755 << 16) | 0x10
                zi.compress_type = zipfile.ZIP_STORED
                z.writestr(zi, b'')
            else:
                zi.external_attr = 0o100644 << 16
                zi.compress_type = zipfile.ZIP_DEFLATED
                with open(path, 'rb') as fh:
                    z.writestr(zi, fh.read())
                count += 1
    return count


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('ordner')
    ap.add_argument('zip', nargs='?', help='Zieldatei (Standard: ORDNER.zip daneben)')
    args = ap.parse_args(argv)
    folder = os.path.abspath(args.ordner)
    if not os.path.isdir(folder):
        print(f'Kein Ordner: {folder}')
        return 1
    zip_path = args.zip or folder + '.zip'
    n = pack(folder, zip_path)
    print(f'{n} Dateien gepackt nach {zip_path}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

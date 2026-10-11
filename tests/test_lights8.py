"""Prüft gepatchte 4-Lichter-Varianten im Emulator.

Aufruf:  python3 tests/test_lights8.py [--debug | --ladetest] <Shader-Ordner> [...]
(ein Ordner mit vs_2_0/ und vs_3_0/ darunter, z. B. <MPQ>/shaders/Vertex)

Test 1: Licht 5–8 leer (Farbe 0, Rest beliebig) -> alle Ausgaben bitgleich
        zum Original.
Test 2: Lichter A in Platz 1–4, Lichter B in Platz 5–8 -> Farbe muss
        Original(A) + Original(B in Platz 1–4) - Original(ohne Lichter)
        sein (Farben klein gewählt, damit nichts sättigt).
Mit --debug (Testfassung, Licht 5–8 in Magenta): Test 1 wie oben, dazu muss
Grün bitgleich zum Original mit Licht 1–4 bleiben und Rot/Blau heller werden.
Mit --ladetest (alle Lichter in Magenta): Grün muss dem Original ohne
Punktlichter gleichen, Rot/Blau heller sein.
Beides einmal mit IEEE-Multiplikation und einmal mit der D3D9-Regel 0*x=0.
"""

import os
import sys
import glob
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import bls, sm3, lights8, emu  # noqa: E402

N = 512
F = np.float32


def inputs_for(sh, rng):
    ins = {}
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 1:
            usage = i.params[0] & 0x1F
            num = i.params[1].num
            if usage == 0:        # position
                v = np.concatenate([rng.uniform(-2, 2, (N, 3)), np.ones((N, 1))], 1)
            elif usage == 2:      # blendindices
                v = rng.integers(0, 20, (N, 4)).astype(F)
            elif usage == 1:      # blendweight
                w = rng.uniform(0, 1, (N, 4))
                v = w / w.sum(1, keepdims=True)
            elif usage == 3:      # normal
                v = rng.normal(size=(N, 4))
                v[:, 3] = 0
            elif usage == 10:     # color: klein halten, damit nichts sättigt
                v = rng.uniform(0, 0.3, (N, 4))
            else:
                v = rng.uniform(0, 1, (N, 4))
            ins[num] = v.astype(F)
    return ins


def base_consts(rng):
    c = {k: rng.uniform(-1, 1, 4).astype(F) for k in range(0, 236)}
    # Matrizen (Modell->Kamera, Knochen) nahe Einheitsmatrix, damit Abstände sinnvoll
    for base in range(31, 223, 3):
        m = np.eye(4, dtype=F)[:3] + rng.uniform(-0.2, 0.2, (3, 4)).astype(F)
        m[:, 3] = rng.uniform(-1, 1, 3)
        for j in range(3):
            c[base + j] = m[j]
    c[10] = F([0.05, 0.05, 0.05, 1])      # Sonne
    c[11] = F([0.05, 0.05, 0.05, 1])      # Umgebung
    c[28] = F([1, 1, 1, 1])
    c[29] = F([0, 0, 0, 0])
    c[30] = F([0.1, 0.5, 1.0, 0])         # Nebel
    return c


def lights(rng):
    col = rng.uniform(0, 0.08, (4, 4)).astype(F)
    col[:, 3] = 1
    pos = rng.uniform(-3, 3, (4, 4)).astype(F)
    pos[:, 3] = 1
    a0 = rng.uniform(0.5, 1.5, 4)
    a1 = rng.uniform(0, 0.5, 4)
    a2 = rng.uniform(0, 0.5, 4)
    return col, pos, np.stack([a0, a1, a2]).astype(F)


def put(c, base_col, base_pos, base_att, L):
    col, pos, att = L
    for j in range(4):
        c[base_col + j] = col[j]
        c[base_pos + j] = pos[j]
    for j in range(3):
        c[base_att + j] = att[j]


def color_key(sh):
    """Ausgaberegister der Vertexfarbe: vs_2_0 oD0, vs_3_0 das o mit dcl_color."""
    if sh.major == 2:
        return (5, 0)
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 6:
            u = i.params[0]
            if u & 0x1F == 10 and (u >> 16) & 0xF == 0:
                return (6, i.params[1].num)
    raise KeyError('keine Farbausgabe')


def check(path, code, new, rng, d3d9, debug=False):
    orig = emu.Emu(sm3.parse(code), d3d9)
    pat = emu.Emu(sm3.parse(new), d3d9)
    ins = inputs_for(orig.sh, rng)
    c = base_consts(rng)
    A, B = lights(rng), lights(rng)
    put(c, 17, 21, 25, A)
    # Test 1: Platz 5–8 leer, Positionen/Abschwächung beliebig (alt)
    stale = lights(rng)
    stale[0][:] = 0
    c1 = dict(c)
    put(c1, 236, 240, 244, stale)
    o = orig.run(c1, ins, N)
    p = pat.run(c1, ins, N)
    for k in o:
        if debug != 'ladetest' and not np.array_equal(o[k].view(np.uint32), p[k].view(np.uint32)):
            return f'Test 1: Ausgabe {k} weicht ab'
    # Test 2
    c2 = dict(c)
    put(c2, 236, 240, 244, B)
    p = pat.run(c2, ins, N)
    cB = dict(c)
    put(cB, 17, 21, 25, B)
    c0 = dict(c)
    c0.update({17 + j: F([0, 0, 0, 0]) for j in range(4)})
    oA = orig.run(c, ins, N)
    oB = orig.run(cB, ins, N)
    o0 = orig.run(c0, ins, N)
    k = color_key(orig.sh)
    if not np.all(np.isfinite(p[k])):
        return 'Test 2: NaN/Inf'
    if debug == 'ladetest':
        # alle Lichter Magenta -> Grün wie ohne Punktlichter, Rot/Blau heller
        if not np.array_equal(p[k][:, 1], o0[k][:, 1]):
            return 'Test L: Grün weicht vom Original ohne Lichter ab'
        if (p[k][:, [0, 2]] < o0[k][:, [0, 2]]).any():
            return 'Test L: Rot/Blau dunkler als ohne Lichter'
        if (p[k][:, [0, 2]] - o0[k][:, [0, 2]]).max() < 1e-3:
            return 'Test L: Magenta ohne Wirkung'
        return None
    if debug:
        # Testfassung: Licht 5–8 nur Magenta -> Grün bitgleich, Rot/Blau heller
        if not np.array_equal(p[k][:, 1], oA[k][:, 1]):
            return 'Test D: Grün verändert'
        if (p[k][:, [0, 2]] < oA[k][:, [0, 2]]).any():
            return 'Test D: Rot/Blau dunkler'
        if (p[k][:, [0, 2]] - oA[k][:, [0, 2]]).max() < 1e-3:
            return 'Test D: Magenta ohne Wirkung'
        return None
    ref = oA[k] + oB[k] - o0[k]
    err = np.abs(p[k][:, :3] - ref[:, :3]).max()
    if err > 1e-4:
        return f'Test 2: Farbabweichung {err:g}'
    contrib = np.abs(p[k][:, :3] - oA[k][:, :3]).max()
    if contrib < 1e-3:
        return 'Test 2: Licht 5-8 ohne Wirkung'
    for kk in oA:
        if kk != k and not np.array_equal(oA[kk], p[kk]):
            return f'Test 2: andere Ausgabe {kk} verändert'
    return None


def main(args):
    debug = 'ladetest' if '--ladetest' in args else ('magenta' if '--debug' in args else None)
    dirs = [a for a in args if not a.startswith('--')]
    rng = np.random.default_rng(1234)
    total = fails = 0
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, 'vs_[23]_0', '*.bls'))):
            try:
                f = bls.load(path)
            except ValueError:
                continue
            for i, v in enumerate(f.variants):
                new = lights8.patch_variant_code(v.code, debug)
                if new is None:
                    continue
                for d3d9 in (False, True):
                    total += 1
                    err = check(path, v.code, new, rng, d3d9, debug)
                    if err:
                        fails += 1
                        print(f'FEHLER {path} Variante {i} d3d9={d3d9}: {err}')
    print(f'{total} Prüfungen, {fails} Fehler')
    return 1 if fails or not total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

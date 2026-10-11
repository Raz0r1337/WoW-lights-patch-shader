"""Prüft die auf 8 Lichter erweiterten Boden-Shader (Terrain.bls) im Emulator.

Aufruf:  python3 tests/test_terrain8.py <Shader-Ordner> [...]
(ein Ordner mit vs_2_0/ und vs_3_0/ darunter, z. B. <MPQ>/shaders/Vertex)

Test 1: Licht 4–8 leer (wie von der Exe gesetzt: alles 0, Abschwächung x = 1)
        -> alle Ausgaben bitgleich zum Original.
Test 2: Lichter A in Platz 1–3, B in 4–6, C in 7–8 -> Farbe muss
        Original(A) + Original(B in 1–3) + Original(C in 1–3) - 2 * Original(leer)
        sein (Farben klein, damit die Begrenzung auf 1 nicht greift); alle
        anderen Ausgaben unverändert.
Test 3: c236–c250 alle 0 (Exe ohne Patch) -> bitgleich zum Original.
Alles mit IEEE-Multiplikation und mit der D3D9-Regel 0*x=0.
"""

import os
import sys
import glob
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import bls, sm3, terrain8, emu  # noqa: E402

N = 512
F = np.float32
EMPTY = (F([0, 0, 0, 0]), F([0, 0, 0, 0]), F([1, 0, 0, 0]))


def inputs_for(sh, rng):
    ins = {}
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 1:
            usage = i.params[0] & 0x1F
            num = i.params[1].num
            if usage == 0:
                v = np.concatenate([rng.uniform(-20, 20, (N, 3)), np.ones((N, 1))], 1)
            elif usage == 3:
                v = rng.normal(size=(N, 4))
                v[:, :3] /= np.linalg.norm(v[:, :3], axis=1, keepdims=True)
                v[:, 3] = 0
            else:
                v = rng.uniform(0, 1, (N, 4))
            ins[num] = v.astype(F)
    return ins


def base_consts(rng):
    c = {k: rng.uniform(-1, 1, 4).astype(F) for k in range(0, 49)}
    m = np.eye(4, dtype=F) + rng.uniform(-0.2, 0.2, (4, 4)).astype(F)   # Welt->Kamera
    m[3] = [0, 0, 0, 1]
    m[:3, 3] = rng.uniform(-5, 5, 3)
    for j in range(4):
        c[j] = m[:, j].astype(F)     # Spalten: r0 = x*c0 + y*c1 + z*c2 + c3
    c[24] = F([0.3, -0.5, 0.8, 0])
    c[25] = F([0.05, 0.05, 0.05, 1])
    c[26] = F([0.05, 0.05, 0.05, 1])
    return c


def light(rng):
    pos = np.concatenate([rng.uniform(-30, 30, 3), [1]]).astype(F)
    col = np.concatenate([rng.uniform(0, 0.08, 3), [0]]).astype(F)
    att = F([rng.uniform(0.5, 1.5), rng.uniform(0, 0.05), rng.uniform(0, 0.005), 0])
    return pos, col, att


def put(c, base, lights):
    for j, (pos, col, att) in enumerate(lights):
        c[base + 3 * j], c[base + 3 * j + 1], c[base + 3 * j + 2] = pos, col, att


def color_key(sh):
    if sh.major == 2:
        return (5, 0)
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 6:
            u = i.params[0]
            if u & 0x1F == 10 and (u >> 16) & 0xF == 0:
                return (6, i.params[1].num)
    raise KeyError('keine Farbausgabe')


def check(code, new, rng, d3d9):
    orig = emu.Emu(sm3.parse(code), d3d9)
    pat = emu.Emu(sm3.parse(new), d3d9)
    ins = inputs_for(orig.sh, rng)
    c = base_consts(rng)
    A = [light(rng) for _ in range(3)]
    B = [light(rng) for _ in range(3)]
    C = [light(rng) for _ in range(2)] + [EMPTY]
    put(c, 28, A)
    c1 = dict(c)
    put(c1, 236, [EMPTY] * 5)
    o = orig.run(c1, ins, N)
    p = pat.run(c1, ins, N)
    for k in o:
        if not np.array_equal(o[k].view(np.uint32), p[k].view(np.uint32)):
            return f'Test 1: Ausgabe {k} weicht ab'
    # Test 3: Exe ungepatcht, c236–c250 nie gesetzt (alles 0) -> bitgleich
    c3 = dict(c)
    c3.update({k: F([0, 0, 0, 0]) for k in range(236, 251)})
    p = pat.run(c3, ins, N)
    for k in o:
        if not np.array_equal(o[k].view(np.uint32), p[k].view(np.uint32)):
            return f'Test 3 (alles 0): Ausgabe {k} weicht ab'
    c2 = dict(c)
    put(c2, 236, B + C[:2])
    p = pat.run(c2, ins, N)
    k = color_key(orig.sh)
    if not np.all(np.isfinite(p[k])):
        return 'Test 2: NaN/Inf'
    cB, cC, c0 = dict(c), dict(c), dict(c)
    put(cB, 28, B)
    put(cC, 28, C)
    put(c0, 28, [EMPTY] * 3)
    oA, oB, oC, o0 = (orig.run(x, ins, N) for x in (c, cB, cC, c0))
    ref = oA[k] + oB[k] + oC[k] - 2 * o0[k]
    err = np.abs(p[k][:, :3] - ref[:, :3]).max()
    if err > 1e-4:
        return f'Test 2: Farbabweichung {err:g}'
    if np.abs(p[k][:, :3] - oA[k][:, :3]).max() < 1e-3:
        return 'Test 2: Licht 4-8 ohne Wirkung'
    for kk in oA:
        if kk != k and not np.array_equal(oA[kk], p[kk]):
            return f'Test 2: andere Ausgabe {kk} verändert'
    return None


def main(args):
    rng = np.random.default_rng(4321)
    total = fails = 0
    for d in args:
        for path in sorted(glob.glob(os.path.join(d, 'vs_[23]_0', '*.bls'))):
            if os.path.basename(path).lower() != 'terrain.bls':
                continue
            f = bls.load(path)
            for i, v in enumerate(f.variants):
                new = terrain8.patch_variant_code(v.code)
                if new is None:
                    continue
                for d3d9 in (False, True):
                    total += 1
                    err = check(v.code, new, rng, d3d9)
                    if err:
                        fails += 1
                        print(f'FEHLER {path} Variante {i} d3d9={d3d9}: {err}')
    print(f'{total} Prüfungen, {fails} Fehler')
    return 1 if fails or not total else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

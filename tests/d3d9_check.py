"""Gegenprobe der gepatchten Shader mit einer echten D3D9-Laufzeit (Wine).

Jede erweiterte Variante wird von D3D9 angelegt (CreateVertexShader) und mit
Licht 1–8 gezeichnet: ein Punkt pro Vertex, gelesen wird die Farbe. Die muss
zum Emulator (tools/emu.py) passen, der in test_lights8.py gegen den
Original-Shader geprüft ist.

Aufruf (Linux, Wine + mingw + Xvfb):
    x86_64-w64-mingw32-gcc -O2 -o runner.exe tests/d3d9/runner.c -ld3d9
    python3 tests/d3d9_check.py <patch-5.MPQ-Ordner> runner.exe
Der Aufruf von Wine (Programm über WINE= wählbar) läuft über xvfb-run,
wenn kein DISPLAY gesetzt ist.
"""

import os
import struct
import subprocess
import sys
import tempfile
import glob
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))
import bls, sm3, emu  # noqa: E402

F = np.float32
GRID = 16                    # 16 x 16 Punkte
W = H = GRID * 2

PS20 = [0xFFFF0200, 0x0200001F, 0x80000000, 0x900F0000,
        0x02000001, 0x800F0800, 0x90E40000, 0x0000FFFF]
PS30 = [0xFFFF0300, 0x0200001F, 0x8000000A, 0x900F0000,
        0x02000001, 0x800F0800, 0x90E40000, 0x0000FFFF]


def decls(sh):
    out = []
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 1:
            u = i.params[0]
            out.append((i.params[1].num, u & 0x1F, (u >> 16) & 0xF))
    return out


def make_case(sh, rng, terrain=False):
    n = GRID * GRID
    a, b = np.meshgrid(np.arange(GRID), np.arange(GRID))
    sx = 2 * a.ravel() + 0.25
    sy = 2 * b.ravel() + 0.25
    inputs = {}
    for reg, usage, idx in decls(sh):
        if usage == 0:
            v = np.stack([2 * sx / W - 1, 1 - 2 * sy / H, np.full(n, 0.5), np.ones(n)], 1)
        elif usage == 2:
            v = rng.integers(0, 20, (n, 4))
        elif usage == 1:
            w = rng.uniform(0, 1, (n, 4))
            v = w / w.sum(1, keepdims=True)
        elif usage == 3:
            v = rng.normal(size=(n, 4))
            v[:, 3] = 0
        elif usage == 10:
            v = rng.uniform(0, 0.5, (n, 4))
        else:
            v = rng.uniform(0, 1, (n, 4))
        inputs[reg] = v.astype(F)
    c = np.zeros((256, 4), F)
    if terrain:
        return make_terrain_case(sh, rng, inputs, c, sx, sy)
    c[2:6] = np.eye(4)                           # Projektion = Einheit
    for base in range(31, 223, 3):               # Modell/Knochen = Einheit
        c[base:base + 3] = np.eye(4)[:3]
    c[10] = [0.1, 0.1, 0.1, 1]
    c[11] = [0.1, 0.1, 0.1, 1]
    c[12] = [0.3, -0.5, 0.8, 0]
    c[28] = [1, 1, 1, 1]
    c[30] = [0.1, 0.5, 1.0, 0]
    for base_col, base_pos, base_att in ((17, 21, 25), (236, 240, 244)):
        for j in range(4):
            c[base_col + j] = list(rng.uniform(0, 0.3, 3)) + [1]
            c[base_pos + j] = list(rng.uniform(-2, 2, 3)) + [1]
        c[base_att] = rng.uniform(0.3, 1.0, 4)
        c[base_att + 1] = rng.uniform(0, 0.5, 4)
        c[base_att + 2] = rng.uniform(0, 0.5, 4)
    return inputs, c, sx, sy


def make_terrain_case(sh, rng, inputs, c, sx, sy):
    """Boden: r0 = x*c0 + y*c1 + z*c2 + c3, o0 = r0 * [c4..c7]; Lichter c28–c36
    und c236–c250 je Position, Farbe, Abschwächung."""
    c[0:4] = np.eye(4)
    c[4:8] = np.eye(4)
    c[12] = [0, 0.5, 1, 0]
    c[18:23] = [1, 1, 0, 0]
    c[24] = [0.3, -0.5, 0.8, 0]
    c[25] = [0.1, 0.1, 0.1, 1]
    c[26] = [0.1, 0.1, 0.1, 1]
    c[27] = [0.2, 0.2, 0.2, 2]
    for base in list(range(28, 37, 3)) + list(range(236, 251, 3)):
        c[base] = list(rng.uniform(-2, 2, 3)) + [1]
        c[base + 1] = list(rng.uniform(0, 0.3, 3)) + [0]
        c[base + 2] = [rng.uniform(0.3, 1.0), rng.uniform(0, 0.5), rng.uniform(0, 0.5), 0]
    c[37:49] = rng.uniform(-1, 1, (12, 4))
    return inputs, c, sx, sy


def color_key(sh):
    if sh.major == 2:
        return (5, 0)
    for i in sh.instrs:
        if i.raw is None and i.opcode == 31 and i.params[1].type == 6:
            u = i.params[0]
            if u & 0x1F == 10 and (u >> 16) & 0xF == 0:
                return (6, i.params[1].num)


def main(folder, runner):
    rng = np.random.default_rng(7)
    cases = []
    for path in sorted(glob.glob(os.path.join(folder, 'Shaders', 'Vertex', 'vs_[23]_0', '*.bls'))):
        terrain = os.path.basename(path).lower() == 'terrain.bls'
        for i, v in enumerate(bls.load(path).variants):
            if terrain:
                if i < 64:               # nur die Lichter-Varianten
                    continue
            elif i % 10 != 9:
                continue
            sh = sm3.parse(v.code)
            cases.append((path, i, v.code, sh) + make_case(sh, rng, terrain))
    blob = bytearray(struct.pack('<3I', W, H, len(cases)))
    for path, i, code, sh, inputs, c, sx, sy in cases:
        ps = PS30 if sh.major == 3 else PS20
        blob += struct.pack('<I', len(code)) + code
        blob += struct.pack('<I', 4 * len(ps)) + struct.pack(f'<{len(ps)}I', *ps)
        blob += c.astype('<f4').tobytes()
        ds = decls(sh)
        blob += struct.pack('<I', len(ds))
        for reg, usage, idx in ds:
            blob += struct.pack('<2I', usage, idx)
        verts = np.stack([inputs[reg] for reg, _, _ in ds], 1)
        blob += struct.pack('<I', len(verts)) + verts.astype('<f4').tobytes()
    tmp = tempfile.mkdtemp()
    cin, cout = os.path.join(tmp, 'cases.bin'), os.path.join(tmp, 'result.bin')
    open(cin, 'wb').write(blob)
    cmd = [os.environ.get('WINE', 'wine'), runner, cin, cout]
    if not os.environ.get('DISPLAY'):
        cmd = ['xvfb-run', '-a'] + cmd
    env = dict(os.environ, WINEDEBUG='-all')
    p = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(p.stdout.strip())
    res = open(cout, 'rb').read()
    o = 0
    fails = 0
    worst = 0
    mean = []
    for path, i, code, sh, inputs, c, sx, sy in cases:
        hc, hd = struct.unpack_from('<2i', res, o)
        o += 8
        img = np.frombuffer(res, np.uint8, W * H * 4, o).reshape(H, W, 4)
        o += W * H * 4
        name = f'{os.path.basename(os.path.dirname(path))}/{os.path.basename(path)} #{i}'
        if hc or hd:
            print(f'FEHLER {name}: CreateVertexShader 0x{hc & 0xffffffff:08x}, Draw 0x{hd & 0xffffffff:08x}')
            fails += 1
            continue
        consts = {k: c[k] for k in range(256)}
        out = emu.Emu(sh).run(consts, inputs, len(sx))
        ref = np.clip(out[color_key(sh)][:, :3], 0, 1)
        px = img[(sy - 0.25).astype(int), (sx - 0.25).astype(int)][:, [2, 1, 0]] / 255.0
        err = np.abs(px - ref).max()
        mean.append(px.mean())
        worst = max(worst, err)
        if err > 2.5 / 255:
            print(f'FEHLER {name}: Farbabweichung {err * 255:.1f}/255')
            fails += 1
    print(f'{len(cases)} Varianten unter D3D9 gezeichnet, größte Abweichung {worst * 255:.2f}/255, '
          f'mittlere Helligkeit {np.mean(mean) * 255:.0f}/255, {fails} Fehler')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))

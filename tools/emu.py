"""Einfacher Emulator für die in den WoW-Vertex-Shadern benutzten SM2/3-Befehle.

Rechnet in float32 (numpy), viele Vertices auf einmal. Gedacht für Tests:
Original gegen gepatchten Shader, und gepatchten Shader gegen eine
CPU-Referenz. `d3d9_mul=True` bildet die D3D9-Regel 0 * x = 0 nach
(entspricht DXVK d3d9.floatEmulation), sonst gilt IEEE.
"""

import numpy as np
import struct
import sm3

F = np.float32


class Emu:
    def __init__(self, sh: sm3.Shader, d3d9_mul=False):
        self.sh = sh
        self.d3d9_mul = d3d9_mul

    def _mul(self, a, b):
        p = a * b
        if self.d3d9_mul:
            p = np.where((a == 0) | (b == 0), F(0), p)
        return p

    def run(self, consts, inputs, n):
        """consts: dict num -> (4,), inputs: dict num -> (n,4). Gibt dict der Ausgaben."""
        C = np.zeros((256, 4), F)
        for k, v in consts.items():
            C[k] = v
        r = np.zeros((32, n, 4), F)
        a = np.zeros((n, 4), np.int32)
        out = {}
        decl_out = {}
        for i in self.sh.instrs:
            if i.raw is not None:
                continue
            op = i.opcode
            if op == 31:
                d = i.params[1]
                if d.type == 6 or (d.type == 4):
                    decl_out[(d.type, d.num)] = i.params[0]
                continue
            if op == 81:
                vals = struct.unpack('<4f', struct.pack('<4I', *i.params[1:]))
                C[i.params[0].num] = vals
                continue

            def rd(p):
                t, num = p.type, p.num
                if t == 0:
                    v = r[num]
                elif t == 1:
                    v = inputs[num]
                elif t == 2:
                    if p.rel is not None:
                        rp = sm3.Param(p.rel)
                        comp = (rp.token >> 16) & 3
                        idx = a[:, comp] + num
                        v = C[np.clip(idx, 0, 255)]
                    else:
                        v = np.broadcast_to(C[num], (n, 4))
                else:
                    raise NotImplementedError(f'Quelltyp {t}')
                sw = (p.token >> 16) & 0xFF
                v = v[:, [(sw >> (2 * k)) & 3 for k in range(4)]]
                mod = (p.token >> 24) & 0xF
                if mod == 1:
                    v = -v
                elif mod == 10:
                    v = np.abs(v)
                elif mod == 11:
                    v = -np.abs(v)
                elif mod:
                    raise NotImplementedError(f'Quellmodifikator {mod}')
                return v.astype(F)

            d = i.params[0]
            s = [rd(p) for p in i.params[1:]]
            rep = lambda x: np.repeat(x[:, None], 4, axis=1)
            with np.errstate(all='ignore'):
                if op == 1:
                    res = s[0]
                elif op == 2:
                    res = s[0] + s[1]
                elif op == 3:
                    res = s[0] - s[1]
                elif op == 4:
                    res = self._mul(s[0], s[1]) + s[2]
                elif op == 5:
                    res = self._mul(s[0], s[1])
                elif op == 6:
                    res = rep(F(1) / s[0][:, 0])
                elif op == 7:
                    res = rep(F(1) / np.sqrt(np.abs(s[0][:, 0])))
                elif op == 8:
                    res = rep(self._mul(s[0][:, :3], s[1][:, :3]).sum(1, dtype=F))
                elif op == 9:
                    res = rep(self._mul(s[0], s[1]).sum(1, dtype=F))
                elif op == 10:
                    res = np.minimum(s[0], s[1])
                elif op == 11:
                    res = np.maximum(s[0], s[1])
                elif op == 12:
                    res = (s[0] < s[1]).astype(F)
                elif op == 13:
                    res = (s[0] >= s[1]).astype(F)
                elif op == 32:
                    res = rep(np.power(np.abs(s[0][:, 0]), s[1][:, 0]))
                elif op == 36:
                    v = s[0][:, :3]
                    l = F(1) / np.sqrt((v * v).sum(1, dtype=F))
                    res = np.concatenate([v * l[:, None], np.zeros((n, 1), F)], 1)
                elif op == 46:
                    res = None
                    av = np.floor(s[0] + F(0.5)).astype(np.int32)
                    m = (d.token >> 16) & 0xF
                    for k in range(4):
                        if m >> k & 1:
                            a[:, k] = av[:, k]
                    continue
                else:
                    raise NotImplementedError(sm3.OPCODES.get(op, op))
            res = res.astype(F)
            if (d.token >> 20) & 1:
                res = np.clip(res, 0, 1)
            m = (d.token >> 16) & 0xF
            if d.type == 0:
                tgt = r[d.num]
            else:
                key = (d.type, d.num)
                tgt = out.setdefault(key, np.zeros((n, 4), F))
            for k in range(4):
                if m >> k & 1:
                    tgt[:, k] = res[:, k]
        return out

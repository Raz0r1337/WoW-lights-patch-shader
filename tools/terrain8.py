"""Erweitert die Boden-Shader (Terrain.bls) von 3 auf 8 Punktlichter.

Die Exe (Funktion VA 0x7D0050) rechnet dem Boden je Bodenstück höchstens
3 Punktlichter zu und legt sie in c28–c36 ab, je Licht drei Vektoren:

    c28 / c31 / c34  Position (Welt minus Kamera, w = 1)
    c29 / c32 / c35  Farbe (rgb, w = 0)
    c30 / c33 / c36  Abschwächung (x = a0, y = a1, z = a2)
    leerer Platz: alles 0, Abschwächung x = 1

Die Varianten 64–127 von Terrain.bls lesen das. Dieses Modul hängt hinter die
dritte Lichtaddition fünf weitere Lichter im selben Format aus

    c236–c238  Licht 4      c239–c241  Licht 5     c242–c244  Licht 6
    c245–c247  Licht 7      c248–c250  Licht 8

Diese Konstanten muss ein Exe-Teil liefern (siehe docs/BODEN.de.md). Ohne
ihn stehen dort Reste der Modell-Lichter (anderes Format), und der Boden
wird falsch beleuchtet. Darum baut build.py den Boden nur mit --boden.

Formel je Licht wie im Original (Variante 64):

    Lpos = c0 * pos.x + c1 * pos.y + c2 * pos.z     (nur Drehung)
    L = Lpos - P ; d2 = dot(L, L) ; r = rsq(d2) ; d = rcp(r) ; L *= r
    ndl = sat(dot(L, N)) ; att = rcp(a0 + a1 * d + a2 * d2)
    Summe += ndl * Farbe * att

Licht 1–3 bleiben Befehl für Befehl unverändert. Vertexposition P und
Normale N werden vorher in freie Temps gesichert (vor dem ersten
Lichtbefehl bzw. vor dem Sonnenterm mit c24), weil Licht 3 sie in manchen
Varianten überschreibt.
"""

import struct
import sm3
from lights8 import (PatchError, dst, src, r, c, used_temps, live_after,
                     const_reads, T_TEMP, T_CONST, X, Y, Z, W, LIMITS)

C_BASE = 236            # Licht 4: c236..c238, Licht 5: c239..c241, ...
N_EXTRA = 5
C_LAST = C_BASE + 3 * N_EXTRA - 1      # c250

OP = {'mov': 1, 'add': 2, 'mad': 4, 'mul': 5, 'rcp': 6, 'rsq': 7,
      'dp3': 8, 'min': 10, 'max': 11}


def ins(op, *params):
    length = sum(len(p.tokens()) for p in params)
    return sm3.Instr(OP[op] | (length << 24), list(params))


def find_def_value(sh, value):
    """(Konstante, Replikations-Swizzle) einer def-Komponente mit diesem Wert."""
    for i in sh.instrs:
        if i.raw is None and i.opcode == 81:
            vals = struct.unpack('<4f', struct.pack('<4I', *i.params[1:]))
            for k, v in enumerate(vals):
                if v == value:
                    return i.params[0].num, (X, Y, Z, W)[k]
    raise PatchError(f'kein def mit {value} gefunden')


def is_terrain_three_light(sh: sm3.Shader):
    """Boden-Variante mit 3 Punktlichtern: liest c28–c36 und c24 (Sonne),
    bildet die Vertexposition mit `add rP, rP, c3`."""
    used = set()
    for i in sh.instrs:
        used.update(const_reads(i))
    return sh.is_vs and all(n in used for n in range(28, 37)) and 24 in used and 3 in used


def patch_shader(sh: sm3.Shader, max_temps: int) -> sm3.Shader:
    instrs = list(sh.instrs)

    def find(pred, what, which='only'):
        hits = [k for k, i in enumerate(instrs) if i.raw is None and pred(i)]
        if not hits or (which == 'only' and len(hits) != 1):
            raise PatchError(f'{what}: {len(hits)} Treffer')
        return hits[-1] if which == 'last' else hits[0]

    def wmask(i):
        return (i.params[0].token >> 16) & 0xF

    # Vertexposition P:  add rP, rP, c3
    k_p = find(lambda i: i.opcode == 2 and const_reads(i) == [3]
               and any(p.type == T_TEMP and p.num == i.params[0].num for p in i.params[1:]),
               'add mit c3')
    rP0 = instrs[k_p].params[0].num
    # erster Lichtbefehl (liest c28..c36)
    k_first = find(lambda i: any(28 <= n <= 36 for n in const_reads(i)), 'c28–c36', 'first')
    # Normale N:  dp3 rX, c24, N  (Sonnenterm)
    k_sun = find(lambda i: i.opcode == 8 and const_reads(i) == [24], 'dp3 mit c24')
    n_src = next(p for p in instrs[k_sun].params[1:] if p.type == T_TEMP)
    rN = n_src.num
    # Ende Licht 3:  mad rW, rD, c36.z, rW ; rcp rW, rW ; mad rA.xyz, rL, rW, rA
    k36 = find(lambda i: 36 in const_reads(i), 'c36', 'last')
    k_end = k36 + 2
    if not (instrs[k36 + 1].opcode == 6 and instrs[k_end].opcode == 4):
        raise PatchError('Ende von Licht 3 nicht erkannt')
    end = instrs[k_end]
    acc = end.params[0]
    if acc.type != T_TEMP or wmask(end) != 7 or (acc.token >> 20) & 0xF:
        raise PatchError('Lichtsumme ist kein rN.xyz ohne Modifikator')
    A = acc.num
    if not (k_p < k_first < k_end and k_sun < k_end):
        raise PatchError('unerwartete Reihenfolge')
    # P darf zwischen Berechnung und Sicherung nicht (xyz) überschrieben werden
    for k in range(k_p + 1, k_first):
        i = instrs[k]
        if i.raw is None and i.opcode not in sm3.NO_DST and i.opcode not in (31, 81) \
                and i.params[0].type == T_TEMP and i.params[0].num == rP0 and wmask(i) & 7:
            raise PatchError('P wird vor der Sicherung überschrieben')

    # P und N in Temps sichern, die die Variante nicht benutzt; Arbeitsregister
    # aus Temps, die nach Licht 3 nicht mehr gelesen werden (wie lights8)
    free = [n for n in range(max_temps) if n not in used_temps(sh)]
    if len(free) < 2:
        raise PatchError(f'zu wenig freie Temp-Register ({len(free)})')
    rP, rNs = free[:2]
    live = live_after(sh, k_end)
    live.setdefault(A, 7)
    work = [n for n in range(max_temps) if n not in live and n not in (rP, rNs)]
    if len(work) < 4:
        raise PatchError(f'zu wenig Arbeitsregister ({len(work)})')
    rL, rM0, rM1, rM2 = work[:4]
    sat_ok = sh.major >= 3
    if not sat_ok:
        zc, zs = find_def_value(sh, 0.0)
        oc, os_ = find_def_value(sh, 1.0)

    save_p = ins('mov', dst(T_TEMP, rP, 'xyz'), r(rP0))
    save_n = ins('mov', dst(T_TEMP, rNs, 'xyz'), sm3.Param(n_src.token & ~(0xFF << 16) | (0xE4 << 16) & ~(0xF << 24)))
    rN = rNs
    block = [ins('mov', dst(T_TEMP, rM0, 'xyz'), c(0)),
             ins('mov', dst(T_TEMP, rM1, 'xyz'), c(1)),
             ins('mov', dst(T_TEMP, rM2, 'xyz'), c(2))]
    for j in range(N_EXTRA):
        b = C_BASE + 3 * j
        block += [
            ins('mul', dst(T_TEMP, rL, 'xyz'), r(rM1), c(b, Y)),
            ins('mad', dst(T_TEMP, rL, 'xyz'), c(b, X), r(rM0), r(rL)),
            ins('mad', dst(T_TEMP, rL, 'xyz'), c(b, Z), r(rM2), r(rL)),
            ins('add', dst(T_TEMP, rL, 'xyz'), r(rP, neg=True), r(rL)),     # L = Lpos - P
            ins('dp3', dst(T_TEMP, rL, 'w'), r(rL), r(rL)),                 # d2
            ins('rsq', dst(T_TEMP, rL, 'w'), r(rL, W)),                     # r
            ins('rcp', dst(T_TEMP, rP, 'w'), r(rL, W)),                     # d
            ins('mul', dst(T_TEMP, rL, 'xyz'), r(rL), r(rL, W)),            # L normiert
        ]
        if sat_ok:
            block.append(ins('dp3', dst(T_TEMP, rL, 'w', sat=True), r(rL), r(rN)))
        else:
            block += [ins('dp3', dst(T_TEMP, rL, 'w'), r(rL), r(rN)),
                      ins('max', dst(T_TEMP, rL, 'w'), r(rL, W), c(zc, zs)),
                      ins('min', dst(T_TEMP, rL, 'w'), r(rL, W), c(oc, os_))]
        block += [
            ins('mul', dst(T_TEMP, rL, 'xyz'), r(rL, W), c(b + 1)),          # ndl * Farbe
            ins('mad', dst(T_TEMP, rL, 'w'), c(b + 2, Y), r(rP, W), c(b + 2, X)),   # a0 + a1*d
            ins('mul', dst(T_TEMP, rP, 'w'), r(rP, W), r(rP, W)),            # d2
            ins('mad', dst(T_TEMP, rL, 'w'), r(rP, W), c(b + 2, Z), r(rL, W)),      # + a2*d2
            ins('rcp', dst(T_TEMP, rL, 'w'), r(rL, W)),                      # att
            ins('mad', dst(T_TEMP, A, 'xyz'), r(rL), r(rL, W), r(A)),        # Summe
        ]
    out = []
    for k, i in enumerate(instrs):
        if k == k_first:
            out.append(save_p)
        if k == k_sun:
            out.append(save_n)
        out.append(i)
        if k == k_end:
            out += block
    return sm3.Shader(sh.version, out)


def patch_variant_code(code: bytes):
    sh = sm3.parse(code)
    if not is_terrain_three_light(sh):
        return None
    temps, slots = LIMITS[sh.major]
    new = patch_shader(sh, temps)
    n = sum(i.slots for i in new.instrs)
    if n > slots:
        raise PatchError(f'{n} Befehlsslots > {slots}')
    return new.to_bytes()

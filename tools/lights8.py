"""Erweitert die 4-Lichter-Varianten der WoW-Vertex-Shader um Licht 5–8.

Patch Nr. 66 (St0nys AIO WoW EXE Patcher) lädt Licht 5–8 im selben Format
wie Licht 1–4 in die Vertex-Shader-Konstanten:

    c236–c239  Farbe Licht 5–8 (rgb; freier Platz = 0)
    c240–c243  Position in Kamerasicht (xyz)
    c244–c246  Abschwächung 0/1/2 (x..w = Licht 5..8)

Das Original rechnet für Licht 1–4 (c17–c27):

    L    = Lichtposition - P            P = Vertexposition (Kamerasicht)
    d2   = dot(L, L)
    ndl  = max(dot(L, N) * rsq(d2), 0)  N = normierte Normale
    att  = 1 / (a0 + a1 * d2 * rsq(d2) + a2 * d2)
    Summe += Farbe * ndl * att

Der Zusatzblock rechnet dasselbe mit c236–c246 und hängt sich direkt hinter
die letzte Lichtaddition (c20) des Originals. Die Sättigung (_sat) dieser
Addition wandert auf die letzte Addition des Zusatzblocks. Licht 1–4 bleiben
Befehl für Befehl unverändert. Ist Licht 5–8 leer (Farbe 0), kommt exakt
dieselbe Summe heraus.

P und N werden an den Stellen gesichert, an denen das Original sie selbst
zuletzt liest (vor `add rL.xyz, -P, c21` bzw. vor dem Sonnenterm mit c12),
in Temp-Register, die die Variante sonst nicht benutzt.

Ist die Exe nicht gepatcht, schreibt sie c236–c246 nie; dort steht dann 0.
Farbe 0 ergibt keinen Beitrag, aber Abschwächung 0 wäre eine Division durch 0
(0 * unendlich ist nach IEEE NaN, nach D3D9-Regel 0). Darum wird der Nenner
der Abschwächung per `max` auf EPS (def c247.w) begrenzt; so bleibt das
Ergebnis auch dann bitgleich zum Original.
"""

import struct
import sm3

C_COLOR, C_POS, C_ATT = 236, 240, 244
C_DEF = 247                                    # eigener def: xyz Magenta (Testfassung), w = EPS
C_DEBUG = C_DEF
EPS = 1e-6                                     # Untergrenze für den Nenner der Abschwächung
DEF_VALUES = (1.0, 0.0, 1.0, EPS)
X, Y, Z, W = 0x00, 0x55, 0xAA, 0xFF          # Replikations-Swizzles
SWZ_ID = 0xE4
MASK = {'x': 1, 'y': 2, 'z': 4, 'w': 8, 'xyz': 7, 'xyzw': 15}
COMP_SWZ = [X, Y, Z, W]

OP = {'mov': 1, 'add': 2, 'mad': 4, 'mul': 5, 'rcp': 6, 'rsq': 7,
      'dp3': 8, 'max': 11}

T_TEMP, T_CONST = 0, 2


class PatchError(Exception):
    pass


def _reg(t, n):
    return (1 << 31) | ((t & 7) << 28) | ((t & 0x18) << 8) | n


def dst(t, n, mask='xyzw', sat=False):
    return sm3.Param(_reg(t, n) | (MASK[mask] << 16) | ((1 if sat else 0) << 20))


def src(t, n, swz=SWZ_ID, neg=False):
    return sm3.Param(_reg(t, n) | (swz << 16) | ((1 if neg else 0) << 24))


def ins(op, *params):
    length = sum(len(p.tokens()) for p in params)
    return sm3.Instr(OP[op] | (length << 24), list(params))


def r(n, swz=SWZ_ID, neg=False):
    return src(T_TEMP, n, swz, neg)


def c(n, swz=SWZ_ID):
    return src(T_CONST, n, swz)


# ------------------------------------------------------------------ Analyse

def reads(i: sm3.Instr):
    """Gelesene Temp-Register: Liste (num, Komponentenmaske)."""
    if i.raw is not None or i.opcode in (31, 81, 47, 48):
        return []
    out = []
    params = i.params if i.opcode in sm3.NO_DST else i.params[1:]
    wmask = 0xF if i.opcode in sm3.NO_DST else (i.params[0].token >> 16) & 0xF
    for p in params:
        if p.type != T_TEMP:
            continue
        sw = (p.token >> 16) & 0xFF
        op = i.opcode
        if op in (8,):                 # dp3: liest xyz
            comps = [0, 1, 2]
        elif op in (9,):               # dp4
            comps = [0, 1, 2, 3]
        elif op == 36:                 # nrm liest xyz
            comps = [0, 1, 2]
        elif op in (6, 7, 14, 15, 32):  # skalare Befehle: Komponente laut Swizzle .x
            comps = [0]
        elif op == 46:                 # mova
            comps = [k for k in range(4) if wmask >> k & 1]
        else:
            comps = [k for k in range(4) if wmask >> k & 1]
        m = 0
        for k in comps:
            m |= 1 << ((sw >> (2 * k)) & 3)
        out.append((p.num, m))
    return out


def writes(i: sm3.Instr):
    if i.raw is not None or i.opcode in sm3.NO_DST or i.opcode in (31, 81, 47, 48):
        return None
    d = i.params[0]
    if d.type != T_TEMP:
        return None
    return d.num, (d.token >> 16) & 0xF


def used_temps(sh: sm3.Shader):
    s = set()
    for i in sh.instrs:
        for n, _ in reads(i):
            s.add(n)
        w = writes(i)
        if w:
            s.add(w[0])
    return s


def live_after(sh: sm3.Shader, k: int):
    """Temp-Register (Komponenten), die nach Befehl k noch gelesen werden."""
    live = {}
    written = {}
    for i in sh.instrs[k + 1:]:
        for n, m in reads(i):
            m &= ~written.get(n, 0)
            if m:
                live[n] = live.get(n, 0) | m
        w = writes(i)
        if w:
            written[w[0]] = written.get(w[0], 0) | w[1]
    return live


def find_zero(sh: sm3.Shader):
    """Konstante mit einer Komponente 0.0 aus einem def suchen."""
    for i in sh.instrs:
        if i.raw is None and i.opcode == 81:
            vals = struct.unpack('<4f', struct.pack('<4I', *i.params[1:]))
            for k, v in enumerate(vals):
                if v == 0.0:
                    return i.params[0].num, COMP_SWZ[k]
    raise PatchError('kein def mit 0.0 gefunden')


def const_reads(i: sm3.Instr):
    if i.raw is not None or i.opcode in (31, 81, 47, 48):
        return []
    return [p.num for p in i.params[1:] if p.type == T_CONST and p.rel is None]


def is_four_light(sh: sm3.Shader):
    """Modell-/Gebäude-Variante mit 4 Punktlichtern (c17–c27)?

    Erkennungszeichen: liest c17–c27, bildet den Lichtvektor mit
    `add rL.xyz, -P, c21` und addiert Lichtfarbe c17 mit mad auf.
    Boden (Terrain) und DetailDoodad nutzen c17–c27 für anderes und fallen
    hier heraus.
    """
    used = set()
    mad17 = add21 = False
    for i in sh.instrs:
        cr = const_reads(i)
        used.update(cr)
        if i.raw is None and i.opcode == 4 and cr[:1] == [17]:
            mad17 = True
        if i.raw is None and i.opcode == 2 and cr == [21] and any(
                p.type == T_TEMP and (p.token >> 24) & 0xF == 1 for p in i.params[1:]):
            add21 = True
    return mad17 and add21 and all(n in used for n in range(17, 28))


# ------------------------------------------------------------------ Patch

def def_instr(num, values):
    bits = struct.unpack('<4I', struct.pack('<4f', *values))
    return sm3.Instr(81 | (5 << 24), [dst(T_CONST, num)] + list(bits))


def patch_shader(sh: sm3.Shader, max_temps: int, debug=None) -> sm3.Shader:
    """debug='magenta': Licht 5–8 leuchten statt in ihrer Farbe in Magenta
    (Testfassung). Leere Plätze (Farbe.w = 0) bleiben auch dann ohne Beitrag.
    debug='ladetest': zusätzlich leuchten auch Licht 1–4 in Magenta. Damit ist
    im Spiel zu sehen, ob die neuen Shader überhaupt geladen werden, auch wenn
    die Exe kein Licht 5–8 liefert."""
    instrs = list(sh.instrs)

    def find(pred, what):
        hits = [k for k, i in enumerate(instrs) if i.raw is None and pred(i)]
        if len(hits) != 1:
            raise PatchError(f'{what}: {len(hits)} Treffer statt 1')
        return hits[0]

    # Lichtvektor 1:  add rL.xyz, -P, c21
    k_p = find(lambda i: i.opcode == 2 and 21 in const_reads(i)
               and any(p.type == T_TEMP and (p.token >> 24) & 0xF == 1 for p in i.params[1:]),
               'add mit c21')
    p_src = next(p for p in instrs[k_p].params[1:] if p.type == T_TEMP)
    # Sonnenterm:  dp3 rX, -c12, N
    k_n = find(lambda i: i.opcode == 8 and 12 in const_reads(i), 'dp3 mit c12')
    n_src = next(p for p in instrs[k_n].params[1:] if p.type == T_TEMP)
    # Letzte Lichtaddition:  mad rA.xyz, c20, rW.w, rA
    k_end = find(lambda i: i.opcode == 4 and 20 in const_reads(i), 'mad mit c20')
    end = instrs[k_end]
    acc = end.params[0]
    if (acc.token >> 16) & 0xF != 7 or acc.type != T_TEMP:
        raise PatchError('Lichtsumme ist kein rN.xyz')
    if not (k_p < k_end and k_n < k_end):
        raise PatchError('unerwartete Reihenfolge')

    used = used_temps(sh)
    free = [n for n in range(max_temps) if n not in used]
    if len(free) < 2:
        raise PatchError(f'zu wenig freie Temp-Register ({len(free)})')
    rP, rN = free[0], free[1]

    live = live_after(sh, k_end)
    live.setdefault(acc.num, 7)
    work = [n for n in range(max_temps) if n not in live and n not in (rP, rN)]
    if len(work) < 4:
        raise PatchError(f'zu wenig Arbeitsregister ({len(work)})')
    rL, rD, rK, rT = work[:4]
    zc, zs = find_zero(sh)
    A = acc.num
    sat = bool((acc.token >> 20) & 1)
    other_mod = (acc.token >> 20) & 0xE
    if other_mod:
        raise PatchError('unerwarteter Ergebnismodifikator')

    def keep(p):           # Quelle ohne Vorzeichen, Swizzle unverändert
        return sm3.Param(p.token & ~(0xF << 24))

    save_p = ins('mov', dst(T_TEMP, rP, 'xyz'), keep(p_src))
    save_n = ins('mov', dst(T_TEMP, rN, 'xyz'), keep(n_src))

    block = []
    comp = 'xyzw'
    for j in range(4):
        block += [
            ins('add', dst(T_TEMP, rL, 'xyz'), r(rP, neg=True), c(C_POS + j)),
            ins('dp3', dst(T_TEMP, rD, comp[j]), r(rL), r(rL)),
            ins('dp3', dst(T_TEMP, rK, comp[j]), r(rL), r(rN)),
        ]
    for j in range(4):
        block.append(ins('rsq', dst(T_TEMP, rT, comp[j]), r(rD, COMP_SWZ[j])))
    block += [
        ins('mul', dst(T_TEMP, rK), r(rK), r(rT)),                  # dot * rsq
        ins('max', dst(T_TEMP, rK), r(rK), c(zc, zs)),              # ndl
        ins('mul', dst(T_TEMP, rT), r(rD), r(rT)),                  # d
        ins('mul', dst(T_TEMP, rT), r(rT), c(C_ATT + 1)),           # a1 * d
        ins('mad', dst(T_TEMP, rT), r(rD), c(C_ATT + 2), r(rT)),    # + a2 * d2
        ins('add', dst(T_TEMP, rT), r(rT), c(C_ATT)),               # + a0
        ins('max', dst(T_TEMP, rT), r(rT), c(C_DEF, W)),            # Nenner >= EPS (Exe ungepatcht: alles 0)
    ]
    for j in range(4):
        block.append(ins('rcp', dst(T_TEMP, rL, comp[j]), r(rT, COMP_SWZ[j])))
    block.append(ins('mul', dst(T_TEMP, rK), r(rK), r(rL)))         # ndl * att
    if debug:
        for j in range(4):                                          # leerer Platz: w = 0
            block.append(ins('mul', dst(T_TEMP, rK, comp[j]), r(rK, COMP_SWZ[j]), c(C_COLOR + j, W)))
    for j in range(4):
        block.append(ins('mad', dst(T_TEMP, A, 'xyz', sat and j == 3),
                         c(C_DEBUG if debug else C_COLOR + j), r(rK, COMP_SWZ[j]), r(A)))

    new_end = sm3.Instr(end.token, [sm3.Param(acc.token & ~(1 << 20))] + end.params[1:])
    if debug == 'ladetest':
        # Farbe von Licht 1–4 (c17–c20) in den vier Lichtadditionen durch Magenta ersetzen
        for k in range(k_end - 3, k_end + 1):
            i = instrs[k]
            if i.raw is not None or i.opcode != 4 or const_reads(i)[:1] != [17 + k - (k_end - 3)]:
                raise PatchError('Lichtadditionen c17–c20 nicht am Stück')
            new = new_end if k == k_end else sm3.Instr(i.token, list(i.params))
            new.params[1] = c(C_DEBUG)
            if k == k_end:
                new_end = new
            else:
                instrs[k] = new
    out = [def_instr(C_DEF, DEF_VALUES)]
    for k, i in enumerate(instrs):
        if k == k_p:
            out.append(save_p)
        if k == k_n:
            out.append(save_n)
        if k == k_end:
            out.append(new_end)
            out += block
        else:
            out.append(i)
    return sm3.Shader(sh.version, out)


LIMITS = {2: (12, 256), 3: (32, 512)}   # Temps, Befehlsslots


def patch_variant_code(code: bytes, debug=None):
    sh = sm3.parse(code)
    if not sh.is_vs or not is_four_light(sh):
        return None
    temps, slots = LIMITS[sh.major]
    new = patch_shader(sh, temps, debug)
    n = sum(i.slots for i in new.instrs)
    if n > slots:
        raise PatchError(f'{n} Befehlsslots > {slots}')
    return new.to_bytes()

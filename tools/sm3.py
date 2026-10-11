"""Kleiner Disassembler und Token-Werkzeug für D3D9-Shader-Bytecode (SM 1–3).

Liefert eine Liste von Instruktionen, die sich wieder bitgleich zu Tokens
zusammensetzen lassen. Text-Ausgabe angelehnt an D3DXDisassembleShader.
"""

import struct
from dataclasses import dataclass, field

OPCODES = {
    0: 'nop', 1: 'mov', 2: 'add', 3: 'sub', 4: 'mad', 5: 'mul', 6: 'rcp',
    7: 'rsq', 8: 'dp3', 9: 'dp4', 10: 'min', 11: 'max', 12: 'slt', 13: 'sge',
    14: 'exp', 15: 'log', 16: 'lit', 17: 'dst', 18: 'lrp', 19: 'frc',
    20: 'm4x4', 21: 'm4x3', 22: 'm3x4', 23: 'm3x3', 24: 'm3x2', 25: 'call',
    26: 'callnz', 27: 'loop', 28: 'ret', 29: 'endloop', 30: 'label',
    31: 'dcl', 32: 'pow', 33: 'crs', 34: 'sgn', 35: 'abs', 36: 'nrm',
    37: 'sincos', 38: 'rep', 39: 'endrep', 40: 'if', 41: 'ifc', 42: 'else',
    43: 'endif', 44: 'break', 45: 'breakc', 46: 'mova', 47: 'defb',
    48: 'defi', 64: 'texcoord', 65: 'texkill', 66: 'tex', 67: 'texbem',
    68: 'texbeml', 69: 'texreg2ar', 70: 'texreg2gb', 71: 'texm3x2pad',
    72: 'texm3x2tex', 73: 'texm3x3pad', 74: 'texm3x3tex', 76: 'texm3x3spec',
    77: 'texm3x3vspec', 78: 'expp', 79: 'logp', 80: 'cnd', 81: 'def',
    82: 'texreg2rgb', 83: 'texdp3tex', 84: 'texm3x2depth', 85: 'texdp3',
    86: 'texm3x3', 87: 'texdepth', 88: 'cmp', 89: 'bem', 90: 'dp2add',
    91: 'dsx', 92: 'dsy', 93: 'texldd', 94: 'setp', 95: 'texldl',
    96: 'breakp',
}

# Opcodes ohne Ziel-Register (nur Quellen)
NO_DST = {25, 26, 27, 28, 29, 30, 38, 39, 40, 41, 42, 43, 44, 45, 65, 96}

REGTYPES = {
    0: 'r', 1: 'v', 2: 'c', 3: 'a', 4: 'o_rast', 5: 'oD', 6: 'o', 7: 'i',
    8: 'oC', 9: 'oDepth', 10: 's', 11: 'c', 12: 'c', 13: 'c', 14: 'b',
    15: 'aL', 16: 'h', 17: 'misc', 18: 'l', 19: 'p',
}
RASTOUT = {0: 'oPos', 1: 'oFog', 2: 'oPts'}

USAGES = {
    0: 'position', 1: 'blendweight', 2: 'blendindices', 3: 'normal',
    4: 'psize', 5: 'texcoord', 6: 'tangent', 7: 'binormal', 8: 'tessfactor',
    9: 'positiont', 10: 'color', 11: 'fog', 12: 'depth', 13: 'sample',
}

SRCMOD = {
    0: '{}', 1: '-{}', 2: '{}_bias', 3: '-{}_bias', 4: '{}_bx2',
    5: '-{}_bx2', 6: '{}_x2', 7: '-{}_x2', 8: '{}_dz', 9: '{}_dw',
    10: '{}_abs', 11: '-{}_abs', 12: '!{}',
}

COMP = 'xyzw'


def regtype(tok):
    return ((tok >> 28) & 7) | ((tok >> 8) & 0x18)


def regnum(tok):
    return tok & 0x7FF


@dataclass
class Param:
    token: int
    rel: int = None          # Zusatz-Token bei relativer Adressierung

    @property
    def type(self):
        return regtype(self.token)

    @property
    def num(self):
        return regnum(self.token)

    def tokens(self):
        return [self.token] if self.rel is None else [self.token, self.rel]


@dataclass
class Instr:
    token: int
    params: list = field(default_factory=list)   # Param oder rohe ints
    raw: list = None          # komplette Tokens bei Kommentar/Sonderfall
    offset: int = 0           # Token-Index im Shader

    @property
    def opcode(self):
        return self.token & 0xFFFF

    @property
    def name(self):
        if self.raw is not None and (self.token & 0xFFFF) == 0xFFFE:
            return 'comment'
        return OPCODES.get(self.opcode, f'op{self.opcode}')

    def tokens(self):
        if self.raw is not None:
            return list(self.raw)
        out = [self.token]
        for p in self.params:
            out += p.tokens() if isinstance(p, Param) else [p]
        return out

    @property
    def slots(self):
        """Grobe Befehlsslot-Zahl wie bei D3DX (Makrobefehle zählen mehrfach)."""
        if self.raw is not None or self.opcode in (31, 81, 47, 48):
            return 0
        return {20: 4, 21: 3, 22: 4, 23: 3, 24: 2, 36: 3, 37: 8, 16: 3,
                14: 1, 15: 1, 32: 3, 33: 2, 34: 3, 18: 2}.get(self.opcode, 1)


@dataclass
class Shader:
    version: int
    instrs: list

    @property
    def major(self):
        return (self.version >> 8) & 0xFF

    @property
    def is_vs(self):
        return (self.version >> 16) == 0xFFFE

    def tokens(self):
        out = [self.version]
        for i in self.instrs:
            out += i.tokens()
        out.append(0x0000FFFF)
        return out

    def to_bytes(self):
        return struct.pack(f'<{len(self.tokens())}I', *self.tokens())


def parse(code: bytes) -> Shader:
    if len(code) % 4:
        raise ValueError('Bytecode-Länge nicht durch 4 teilbar')
    t = list(struct.unpack(f'<{len(code) // 4}I', code))
    ver = t[0]
    major = (ver >> 8) & 0xFF
    if major < 2:
        raise ValueError('nur Shader-Modell 2 und 3 werden unterstützt')
    i = 1
    instrs = []
    while i < len(t):
        tok = t[i]
        if tok == 0x0000FFFF:
            if i != len(t) - 1:
                raise ValueError('Daten nach dem Ende-Token')
            return Shader(ver, instrs)
        if (tok & 0xFFFF) == 0xFFFE:
            n = (tok >> 16) & 0x7FFF
            instrs.append(Instr(tok, raw=t[i:i + 1 + n], offset=i))
            i += 1 + n
            continue
        op = tok & 0xFFFF
        length = (tok >> 24) & 0xF
        body = t[i + 1:i + 1 + length]
        ins = Instr(tok, offset=i)
        if op == 31:                                   # dcl
            ins.params = [body[0], Param(body[1])]
        elif op in (81, 48, 47):                       # def, defi, defb
            ins.params = [Param(body[0])] + body[1:]
        else:
            j = 0
            while j < len(body):
                p = Param(body[j])
                j += 1
                if (p.token >> 13) & 1:                # relative Adressierung
                    p.rel = body[j]
                    j += 1
                ins.params.append(p)
        if len(ins.tokens()) != 1 + length:
            raise ValueError(f'Token {i}: Länge passt nicht')
        instrs.append(ins)
        i += 1 + length
    raise ValueError('kein Ende-Token')


def fmt_reg(p: Param, shader_vs=True):
    t, n = p.type, p.num
    if t == 4:
        return RASTOUT.get(n, f'oRast{n}')
    if t == 3:
        return f'a{n}' if shader_vs else f't{n}'
    if t == 6:
        return f'o{n}' if shader_vs else f'oT{n}'
    return f'{REGTYPES.get(t, "?" + str(t))}{n}'


def fmt_dst(p: Param, vs=True):
    s = fmt_reg(p, vs)
    mask = (p.token >> 16) & 0xF
    if mask != 0xF:
        s += '.' + ''.join(COMP[k] for k in range(4) if mask >> k & 1)
    return s


def fmt_swz(sw):
    comps = [COMP[(sw >> (2 * k)) & 3] for k in range(4)]
    if comps == list('xyzw'):
        return ''
    if len(set(comps)) == 1:
        return '.' + comps[0]
    return '.' + ''.join(comps)


def fmt_src(p: Param, vs=True):
    s = fmt_reg(p, vs)
    if p.rel is not None:
        r = Param(p.rel)
        idx = fmt_reg(r, vs) + '.' + COMP[(r.token >> 16) & 3]
        s = f'{s[0]}[{idx} + {p.num}]' if p.type == 2 else f'{s}[{idx}]'
    s += fmt_swz((p.token >> 16) & 0xFF)
    return SRCMOD.get((p.token >> 24) & 0xF, '?{}').format(s)


def fmt_instr(ins: Instr, vs=True):
    if ins.raw is not None:
        return f'// comment ({len(ins.raw) - 1} dwords)'
    op = ins.opcode
    name = ins.name
    if op == 31:
        u = ins.params[0]
        dst = ins.params[1]
        if dst.type in (1, 6, 3) and vs or dst.type == 6:
            use = USAGES.get(u & 0x1F, f'usage{u & 0x1F}')
            idx = (u >> 16) & 0xF
            return f'dcl_{use}{idx if idx else ""} {fmt_dst(dst, vs)}'
        return f'dcl {fmt_dst(dst, vs)}'
    if op == 81:
        vals = struct.unpack('<4f', struct.pack('<4I', *ins.params[1:]))
        return f'def {fmt_dst(ins.params[0], vs)}, ' + ', '.join(f'{v:g}' for v in vals)
    if op in (48, 47):
        return f'{name} {fmt_dst(ins.params[0], vs)}, ' + ', '.join(str(v) for v in ins.params[1:])
    mod = (ins.token >> 16) & 0xFF
    if op in (41, 45, 94):
        name += {1: '_gt', 2: '_eq', 3: '_ge', 4: '_lt', 5: '_ne', 6: '_le'}.get(mod & 7, '')
    params = ins.params
    if op in NO_DST:
        args = [fmt_src(p, vs) for p in params]
    else:
        dst = params[0]
        rmod = (dst.token >> 20) & 0xF
        if rmod & 1:
            name += '_sat'
        if rmod & 2:
            name += '_pp'
        args = [fmt_dst(dst, vs)] + [fmt_src(p, vs) for p in params[1:]]
    return f'{name} ' + ', '.join(args) if args else name


def disasm(sh: Shader):
    vs = sh.is_vs
    lines = [f'{"vs" if vs else "ps"}_{sh.major}_{sh.version & 0xFF}']
    for ins in sh.instrs:
        lines.append(fmt_instr(ins, vs))
    return lines

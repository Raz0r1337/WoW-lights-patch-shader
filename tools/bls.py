"""Lesen und Schreiben von WoW-3.3.5a-Shaderdateien (.bls, D3D-Profile).

Aufbau (aus den Dateien ermittelt):

    u32 magic        0x47585348 "GXSH" (patch*.MPQ, Vertex und Pixel),
                     älter in common-2.MPQ: 0x47585653 "GXVS" / 0x47585053 "GXPS"
    u32 version      0x00010003
    u32 count        Anzahl Varianten
    count x:
        u32 flags     (bei Vertex-Shadern z. B. 0x9 / 0x801 ...)
        u32 inputs    Eingabemaske der Variante
        u32 unknown   bisher immer 0
        u32 size      Länge des Bytecodes in Byte
        u8  code[size]  D3D9-Shader-Bytecode (beginnt mit 0xFFFExxxx/0xFFFFxxxx)

Die ARB-Profile (arbvp1, arbfp1, ...) haben Text statt Bytecode und
zusätzliche Auffüllbytes. Sie werden hier nicht unterstützt.
"""

import struct
from dataclasses import dataclass, field

MAGIC_SH = 0x47585348
MAGIC_VS = 0x47585653
MAGIC_PS = 0x47585053
MAGICS = (MAGIC_SH, MAGIC_VS, MAGIC_PS)
VERSION = 0x00010003


@dataclass
class Variant:
    flags: int
    inputs: int
    unknown: int
    code: bytes


@dataclass
class BlsFile:
    magic: int
    version: int
    variants: list = field(default_factory=list)


def parse(data: bytes) -> BlsFile:
    if len(data) < 12:
        raise ValueError('Datei zu kurz (leer?)')
    magic, version, count = struct.unpack_from('<3I', data, 0)
    if magic not in MAGICS:
        raise ValueError(f'unbekannte Magic 0x{magic:08X}')
    if version != VERSION:
        raise ValueError(f'unbekannte Version 0x{version:08X}')
    f = BlsFile(magic, version)
    o = 12
    for i in range(count):
        if o + 16 > len(data):
            raise ValueError(f'Variante {i}: Kopf hinter Dateiende')
        flags, inputs, unknown, size = struct.unpack_from('<4I', data, o)
        o += 16
        if o + size > len(data):
            raise ValueError(f'Variante {i}: Code hinter Dateiende')
        f.variants.append(Variant(flags, inputs, unknown, data[o:o + size]))
        o += size
    if o != len(data):
        raise ValueError(f'{len(data) - o} Byte nach der letzten Variante')
    return f


def build(f: BlsFile) -> bytes:
    out = bytearray(struct.pack('<3I', f.magic, f.version, len(f.variants)))
    for v in f.variants:
        out += struct.pack('<4I', v.flags, v.inputs, v.unknown, len(v.code))
        out += v.code
    return bytes(out)


def load(path) -> BlsFile:
    with open(path, 'rb') as fh:
        return parse(fh.read())


def save(f: BlsFile, path):
    with open(path, 'wb') as fh:
        fh.write(build(f))

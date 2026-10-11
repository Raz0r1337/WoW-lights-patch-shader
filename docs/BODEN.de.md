# Boden (Terrain) und Punktlichter – Analyse und Vorschlag (2026-10-11)

Beobachtung von Sascha: Der Lichtschein der Lagerfeuer auf dem Boden sieht seltsam aus
(harte Kanten zwischen Bodenstücken, nicht alle Feuer leuchten den Boden an).
Mit und ohne die neuen Shader (patch-Z.mpq) ist der Boden gleich, gemessen an beiden
Screenshots (Abweichung unter 1/255). Die neuen Shader ändern nur Modelle und Gebäude.

## Ursache

Der Boden geht einen eigenen Weg als Modelle und Gebäude:

- Der Boden-Shader `Shaders\Vertex\vs_2_0|vs_3_0\Terrain.bls` (128 Varianten) rechnet in
  den Varianten 64–127 **höchstens 3 Punktlichter** je Bodenstück (Varianten 0–63 keine).
  Ungerade Varianten haben zusätzlich Schattenkarten (c37–c48).
- Die Exe füllt dafür **eigene Konstanten c28–c36**, nicht c17–c27 wie bei Modellen.
  Lichter-Patch Nr. 66 ändert an dieser Stelle nichts. Jedes Bodenstück bekommt also
  weiter nur die 3 nächsten Lichter. Das ist das Verhalten der Original-Exe; mit 8 Feuern
  fällt es nur stärker auf.

## Format im Shader (c28–c36, je Licht 3 Vektoren)

| Register | Inhalt |
|---|---|
| c28 / c31 / c34 | Position Licht 1 / 2 / 3: Weltposition minus Kameraposition, w = 1 |
| c29 / c32 / c35 | Farbe (rgb), w = 0 |
| c30 / c33 / c36 | Abschwächung x = a0, y = a1, z = a2, w = 0 |

Leerer Platz: alles 0, Abschwächung x = 1 (so setzt es die Exe, siehe unten).

Formel je Licht (aus der Disassemblierung, Variante 64, vs_3_0):

```
Lpos = c0 * pos.x + c1 * pos.y + c2 * pos.z      ; nur Drehung, keine Verschiebung
L    = Lpos - P                                   ; P = Vertex in Kamerasicht (c0..c3)
d2   = dot(L, L) ; r = rsq(d2) ; d = rcp(r)
L    = L * r
ndl  = sat(dot(L, N))                             ; N = Normale, gedreht mit c0..c2
att  = rcp(a0 + a1 * d + a2 * d2)
Summe += ndl * Farbe * att
Farbe = min(Summe + Umgebung + Sonne, 1) * 0.5
```

(vs_2_0 gleich, nur `max`/`min` statt `_sat`.) Budget: größte 3-Lichter-Variante 121
Befehle, 120 Slots, Temps bis r6. vs_2_0 erlaubt 256 Slots und 12 Temps; fünf weitere
Lichter kosten je 15–17 Befehle, passt also.

## Exe-Stellen (Wow.exe 12340, VA; Dateioffset = VA − 0x400C00)

Funktion **VA 0x7D0050** (Dateioffset 0x3CF450) baut die Boden-Konstanten im Shader-Weg:

| VA | Was |
|---|---|
| 0x7D0082 `call 0x790440` | lokale Lichtliste (CM2Lighting, 0xD4 Byte, auf dem Stack bei `[ebp-0x104]`) leeren, Position des Bodenstücks aus `chunk+0x24` |
| 0x7D0094 `call 0x81E400` | alle Lichter des Kartenlichtmanagers (`[0xCD754C]`, Liste ab `+0x20`, Nächster `+0x68`) per **AddLight 0x834F60** anbieten; AddLight behält die 4 nächsten (mit Patch 66: Rest in die Zusatzliste) |
| 0x7D00A2 `call 0x7B7BD0` | weitere Lichter des Bodenstücks (ruft ebenfalls AddLight) |
| 0x7D00BF `mov [ebp-0x1C], 3` | **Schleife über 3 Lichter** |
| 0x7D00E0 `call 0x8349E0` | GetLight(index, &pos, &farbe, &abschw) → 1 wenn vorhanden; liest Licht `+0x0C` Position, `+0x3C` Farbe, `+0x54` Abschwächung |
| 0x7D00E9–0x7D0133 | Position minus Kamera (`[0xCD8F5C/60/64]`), w = 1; Farbe; Abschwächung; `[ebp-0x18] = 1` (mindestens ein Licht) |
| 0x7D0138–0x7D015F | leerer Platz: alles 0, Abschwächung x = 1 |
| Block | 0xD25260 = c28, je Licht 0x30 Byte; c0 liegt bei 0xD250A0 (c_n = 0xD250A0 + 16·n) |
| 0x7D027C `call 0x79E470` | Variantenwahl aus (Lichter ja/nein, Lagen−1, …), Tabelle 0xCE0008 |
| 0x7D028B `push 0x4D; call 0x685F50` | Vertex-Shader setzen |
| 0x7D0292–0x7D02AB | **Upload**: `CGxDevice::vtable[+0x118](0, 0, 0xD250A0, 0x25)` → c0–c36 |

Warum die Schleife nicht einfach auf 8 gestellt werden kann: hinter c36 liegen ab
0xD252F0 die Schattenmatrizen c37–c48. Licht 4–8 brauchen einen eigenen Puffer und
einen eigenen Upload.

## Vorschlag für den Exe-Teil (AIO-Patcher, Patch Nr. 66 erweitern)

1. Nach der 3er-Schleife (z. B. Einsprung bei 0x7D0171, 6 Byte `mov esi,[ebp+8]` +
   `fld`) oder vor dem Upload (0x7D0292, 6 Byte `mov ecx,[0xC5DF88]`) eine Höhle:
   - Licht 4: `GetLight(3, …)` an der lokalen Liste `[ebp-0x104]` (steht dort schon,
     AddLight behält 4).
   - Licht 5–8: aus der Zusatzliste des Patches für genau diese Liste (die lokale Liste
     wird von 0x790440 jedes Mal geleert, auch `+0x14`; prüfen, ob die Zusatzliste dann
     pro Bodenstück und Bild sauber neu belegt wird).
   - Gleiches Format wie oben: Position minus Kamera (w = 1), Farbe (w = 0),
     Abschwächung (w = 0); leere Plätze alles 0 und Abschwächung x = 1.
   - Puffer 15 Vektoren (5 Lichter × 3), dann
     `CGxDevice::vtable[+0x118](0, 236, Puffer, 15)` → **c236–c250**.
   - Nur wenn `[CGxDevice+0x2E0]` ≥ 251 (DXVK meldet 256; vs_2_0 erlaubt bis c255).
2. Den Boden-Teil fest an Nr. 66 koppeln (nicht einzeln aktivierbar): Nr. 66 und
   Boden-Teil schreiben beide ab c236, jeder Shader liest nur direkt nach seinem
   eigenen Upload. Gäbe es den Boden-Teil ohne Nr. 66, läsen die neuen Modell-Shader
   Bodenlichter in falschem Format. Eine Prüfung auf mindestens 251 VS-Konstanten
   reicht für beide Teile.
3. Variantenwahl unverändert lassen: Die Exe wählt die Lichter-Varianten, sobald
   mindestens ein Licht da ist; die neuen Shader rechnen 8 Plätze, leere Plätze
   (Farbe 0) tragen nichts bei.

## Shader-Teil (umgesetzt: tools/terrain8.py)

Varianten 64–127 von Terrain.bls (vs_2_0 und vs_3_0) rechnen Licht 4–8 aus c236–c250
mit derselben Formel wie Licht 1–3 und addieren das Ergebnis vor dem `min … c8.y`.
Vertexposition und Normale werden vorher in freie Temps gesichert (Licht 3
überschreibt sie in manchen Varianten). Prüfung: `tests/test_terrain8.py` (Emulator,
leere Plätze bitgleich, Lichter in 4–8 = Überlagerung) und `tests/d3d9_check.py`
(Wine-D3D9). Bauen mit `python3 tools/build.py QUELLE ZIEL --boden`.

Der Nenner der Abschwächung wird per `max` auf `c251.x` (= 1e-6, eigener `def`)
begrenzt; bei gar nicht gepatchter Exe (c236–c250 = 0) ist das Ergebnis so bitgleich
zum Original (Test 3 in `test_terrain8.py`, `d3d9_check.py` mit Nullen).

**Wichtig:** Diese Boden-Shader erst einsetzen, wenn der Exe-Teil da ist. Ohne ihn
lesen sie in c236–c250 Reste der Modell-Lichter (anderes Format) und der Boden wird
falsch beleuchtet. Darum baut das Werkzeug den Boden nur mit `--boden`.

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
  Der Modell-Teil des Lichter-Patches (heute Nr. 69) ändert an dieser Stelle nichts.
  Jedes Bodenstück bekommt also weiter nur die 3 nächsten Lichter. Das ist das Verhalten der Original-Exe; mit 8 Feuern
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
| 0x7D0094 `call 0x81E400` | alle Lichter des Kartenlichtmanagers (`[0xCD754C]`, Liste ab `+0x20`, Nächster `+0x68`) per **AddLight 0x834F60** anbieten; AddLight behält die 4 nächsten (mit Nr. 69: Rest in die Zusatzliste) |
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

## Exe-Teil: Vorschlag (2026-10-11) und Umsetzung im Patcher (2026-10-12)

Umgesetzt ist der Teil im Patcher-Zweig `st0ny-dev-lights` (Commit `a768c2c`, „No. 69
more lights: ground gets lights 4-8 too“) als fester Bestandteil von Nr. 69, Stand
2026-10-14 noch nicht in `st0ny-dev`/`st0ny-main` und im Spiel ungetestet. Höhle
`cave_ter` vor dem Original-Upload (Hook bei 0x7D0292, 6 Byte `mov ecx,[0xC5DF88]`,
Rücksprung 0x7D0298): nur bei mindestens 251 VS-Konstanten (`[CGxDevice+0x2E0]`); fünf
Plätze à 0x30 Byte werden geleert (Abschwächung x = 1), Platz 0 bekommt Licht 4 aus der
lokalen Liste (wenn mehr als 3 Lichter), Platz 1–4 die Zusatzlichter aus dem
Ring-Eintrag der Liste; je Platz Position minus Kamera (w = 1), Farbe (w = 0),
Abschwächung (w = 0); Upload `vtable[+0x118](0, 236, Puffer, 15)` → c236–c250.
Das entspricht dem Vorschlag unten Punkt für Punkt.

### Lesende Prüfung des Exe-Teils (2026-10-14)

Eigene Byte-Lesung plus zwei unabhängige Gegenprüfungen (Bytes/Sprünge und
Format/Semantik, beide gegen die Exe, nicht nur gegen die Kommentare des Patchers).
Ergebnis: **keine Abweichung, die den Spieltest betrifft.** Im Einzelnen bestätigt:

- Sektion `.lght` zählt genau 0x7B4 Byte, `cave_ter` liegt bei +0x680, `ct_put` bei
  +0x757; alle rel8/rel32-Sprünge und Calls treffen ihre Ziele. Der Hook ersetzt genau
  die 6 Byte `mov ecx,[0xC5DF88]` bei 0x7D0292; 0x7D0298 ist eine Befehlsgrenze, kein
  Sprung in `.text` zielt dazwischen. Der Code ab 0x7D0298 erwartet nur ecx (die Höhle
  lädt es nach `popad` neu), keine Flags; FPU-Tiefe am Hook ist 0.
- Puffer: TBUF 5 × 0x30 Byte bei +0x340–0x42F, keine Überlappung mit Ring-Zeigern,
  EXTBUF (+0x40) oder Gx-Plätzen (+0x100, 8 × 0x48).
- Struktur der lokalen Liste (aus GetLight 0x8349E0 und AddLight 0x834F60): Zeiger bei
  +0x84..+0x90 (aufsteigend nach Abstand), Anzahl bei +0xA4. `[ecx+0x90]` ist also das
  4. Licht, der Vergleich `Anzahl > 3` passt.
- `vtable+0x118` (ShaderConstantsSet 0x6833E0) nimmt (Ziel, Startregister, Daten,
  Anzahl); Original (0, 0, 0xD250A0, 0x25) und Höhle (0, 0xEC, TBUF, 0xF) in derselben
  Reihenfolge → c236–c250. Schattenpuffer 256 Vektoren, Upload zur GPU erst beim
  Zeichnen als ein Bereich [min..max].
- `ct_put`: +0 Position minus Kamera (dieselben Globals 0xCD8F5C/60/64 wie das
  Original bei 0x7D00EC), w = 1; +0x10 Farbe (+0x3C..), w = 0; +0x20 Abschwächung
  (+0x54..), w = 0. Leere Plätze wie im Original (0x7D0138–0x7D015F): alles 0,
  Abschwächung x = 1; die Löschschleife läuft je Bodenstück über alle 5 Plätze.
- Gate: `[dev+0x2E0]` ist `D3DCAPS9.MaxVertexShaderConst`; 236 + 15 = 251 ist die
  exakte Grenze und nötig, weil der verzögerte Upload den ganzen Dirty-Bereich ohne
  eigene Klemmung schickt (ohne Gate würde auf einer Karte mit weniger Konstanten der
  Block c0–c250 samt c28–c36 abgewiesen).
- Die Variantenwahl 0x79E470 hat nur den Aufrufer 0x7D027C: jedes Zeichnen des Bodens
  mit Lichtern geht durch den Hook. Zwischen Höhle und Zeichnen schreibt nichts mehr in
  c236 ff.; Modelle laden c236–c246 vor jedem Zeichnen mit Lichtern neu.
- `get_entry`: Das Wort bei CM2Lighting+0x16 setzt nur `alloc_entry` (über AddLight);
  die lokale Liste wird bei 0x790440 → 0x834900 per `memset` komplett genullt. Ein
  veralteter Eintrag aus einem früheren Bild ist damit nicht erreichbar.

Nur theoretisch, kein Handlungsbedarf:

- Der Boden-Shader deklariert `def c251`, braucht also 252 Konstanten; der Modell-Shader
  `def c247` (248) bei Gate 247. Jede Karte mit Shader-Modell 2 oder 3 meldet 256.
  Ausnahme: GeForce FX wird von der Exe auf 192 geklemmt, dort bleiben beide Höhlen aus
  und die Shader zeigen das Original.
- Unter OpenGL (`gxApi "opengl"`) nimmt das Spiel Text-Shader und begrenzt deren
  Konstanten auf 223; die `.bls`-Shader gelten dort ohnehin nicht.
- `popad` stellt EFLAGS nicht wieder her; ab 0x7D0298 liest nichts die Flags.
- Der Upload beim Zeichnen schickt pro Bodenstück jetzt c0–c250 statt c0–c36 als einen
  Block (bis zu 251 Register): nur Kosten, kein Fehler.

### Vorschlag vom 2026-10-11

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
2. Den Boden-Teil fest an Nr. 69 koppeln (nicht einzeln aktivierbar): Modell-Teil und
   Boden-Teil schreiben beide ab c236, jeder Shader liest nur direkt nach seinem
   eigenen Upload. Gäbe es den Boden-Teil ohne den Modell-Teil, läsen die neuen Modell-Shader
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

**Wichtig:** Diese Boden-Shader nur mit einer Exe einsetzen, deren Nr. 69 den
Boden-Teil hat (Patcher-Stand ab 2026-10-12). Mit einem älteren Stand von Nr. 69 lesen
sie in c236–c250 Reste der Modell-Lichter (anderes Format) und der Boden wird falsch
beleuchtet. Bis der Spieltest den Boden bestätigt, baut das Werkzeug ihn nur mit
`--boden`.

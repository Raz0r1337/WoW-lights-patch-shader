# WoW-lights-patch-shader

Werkzeug für WoW 3.3.5a (12340): baut aus den eigenen Original-Shadern Vertex-Shader,
die bis zu **8 Punktlichter** darstellen. Gegenstück zu Patch **Nr. 66 „Mehr Lichter:
8 statt 4 Punktlichter“** aus St0nys AIO WoW EXE Patcher. Ohne neue Shader liefert die
Exe Licht 5–8 zwar an die Grafik, sichtbar wird es aber nicht.

Das Repo enthält **keine Blizzard-Dateien**. Die neuen Shader entstehen beim Spieler
aus seinen eigenen Dateien.

## Voraussetzungen

- `Wow.exe` 3.3.5a mit Nr. 66, zum Testen am besten auch Nr. 67 („Lichter bleiben an,
  wenn ihre Quelle außerhalb des Bildes ist“).
- Python 3 (nur Standardbibliothek). Für die Tests zusätzlich `numpy`.

## Benutzung

1. Mit Ladik's MPQ Editor aus jedem MPQ, das einen Ordner `Shaders\` hat, diesen Ordner
   exportieren, je MPQ in einen eigenen Unterordner mit dem Namen des MPQ:

   ```
   Quelle\
     common-2.MPQ\Shaders\...
     patch.MPQ\Shaders\...
     patch-2.MPQ\Shaders\...
     patch-3.MPQ\Shaders\...
   ```

   Welche Datei gilt, entscheidet das Werkzeug wie das Spiel: `patch-3` vor `patch-2`
   vor `patch` vor den Grund-MPQs.

2. Shader bauen, Ziel ist der `Data`-Ordner des Spiels:

   ```
   python tools/build.py Quelle "C:\WoW\Data"
   ```

   Ergebnis: `Data\patch-5.MPQ\Shaders\Vertex\vs_2_0\*.bls` und `...\vs_3_0\*.bls`,
   ein **Ordner** mit dem Namen und Aufbau eines MPQ. Mit `--name` lässt sich ein
   anderer Name wählen.

3. Im Spiel testen, siehe nächster Abschnitt.

## Im Spiel testen

### Vorbereitung

- `Wow.exe` mit Nr. 66 und Nr. 67 patchen.
- In `WTF\Config.wtf` muss `SET gxApi "d3d9"` stehen (mit DXVK ohnehin) und
  `fixedFunction` darf nicht `1` sein (`/console fixedFunction 0`, danach Neustart).
  Unter OpenGL (`gxApi "opengl"`) nimmt das Spiel andere Shader, dann wirkt nichts.
- Ordner so ablegen, dass es `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls`
  gibt (nicht doppelt `patch-5.MPQ\patch-5.MPQ`).

### Schritt 1: Testfassung (Magenta)

Mit `--debug` gebaut, leuchten Licht 5–8 nicht in ihrer Farbe, sondern **magenta**.
Licht 1–4 sehen normal aus. So ist sofort zu sehen, ob alles greift.

```
python tools/build.py --debug Quelle "C:\WoW\Data"
```

An einen Ort gehen, an dem viele Lichtquellen dicht beieinander sind (Fackeln,
Laternen, Kohlebecken), z. B. in Sturmwind, Eisenschmiede an der Großen Schmiede
oder Dalaran, am besten nachts oder in Innenräumen. Dann die Kamera auf die eigene
Figur und auf Gebäude in der Nähe richten und langsam herumlaufen.

| Was man sieht | Bedeutung |
|---|---|
| Figur, NPCs oder Gebäude bekommen magentafarbene Lichtflecken, die beim Laufen wandern | Alles greift: Ordner wird geladen, die Exe liefert Licht 5–8, die Shader rechnen sie |
| Alles sieht aus wie immer | Entweder sind dort nicht mehr als 4 Lichter in der Nähe (anderen Ort probieren), oder der Ordner wird nicht geladen (dann den Ordner mit Ladik's MPQ Editor zu einem echten `patch-5.MPQ` packen und nochmal) |
| Modelle fehlen, sind schwarz, flackern, oder das Spiel stürzt ab | Fehler in den Shadern, bitte mit Screenshot melden |

Der Boden bleibt immer ohne Magenta, er hat eigene Shader und bekommt keine
Zusatzlichter.

### Schritt 2: richtige Fassung

Die Testfassung durch die normale ersetzen (ohne `--debug` bauen). Zum Vergleich an
derselben Stelle mit derselben Kamera zwei Bildschirmfotos machen: einmal mit dem
Ordner, einmal ohne (Ordner z. B. in `_patch-5.MPQ` umbenennen, Spiel neu starten).
Mit dem Ordner werden Figur und Gebäude von mehr Lichtquellen gleichzeitig
beleuchtet. Läuft man an einer Reihe Fackeln vorbei, springt das Licht auf der Figur
seltener an und aus, weil erst das 9. Licht wegfällt statt schon das 5.

### Ordner statt MPQ

Der Client öffnet einen Ordner mit MPQ-Namen wie ein Archiv. Belegt in der Original-Exe:
`SFileOpenArchive` (VA `0x45C480`) fragt den Dateityp ab (`0x427170`), ein Ordner
(`FILE_ATTRIBUTE_DIRECTORY`, gesetzt bei `0x435760`) bekommt Typ 2 und wird über
`0x453E30` als Verzeichnis-Archiv geöffnet. Ob die Suche nach `patch-?.MPQ` auch Ordner
findet, zeigt erst der Spieltest. Klappt es nicht, den Ordner mit Ladik's MPQ Editor
1:1 zu einem echten `patch-5.MPQ` packen.

Prüfen lässt sich das unter DXVK mit `DXVK_SHADER_DUMP_PATH`: Die neuen Shader lesen
`c236`–`c246`, die Originale nicht.

## Was geändert wird

- Nur die Varianten mit 4 Lichtern (Nr. 9, 19, …, 89 jeder Datei) der Modell-Shader
  (`Diffuse_*`, `CDiffuse_T1`) und Gebäude-Shader (`MapObj*`), in `vs_2_0` und `vs_3_0`.
  Das Spiel nimmt diese Varianten ab 4 Lichtern.
- Licht 1–4 bleiben Befehl für Befehl unverändert. Hinter der letzten Lichtaddition
  rechnet ein Zusatzblock (31 Befehle, dazu 2 zum Sichern von Position und Normale) Licht 5–8 nach derselben Formel wie das Original:

  ```
  L = Lichtposition - P;  d2 = dot(L, L)
  ndl = max(dot(L, N) * rsq(d2), 0)
  att = 1 / (a0 + a1 * d2 * rsq(d2) + a2 * d2)
  Summe += Farbe * ndl * att
  ```

  mit den Registern, die Nr. 66 belegt: `c236–c239` Farbe, `c240–c243` Position,
  `c244–c246` Abschwächung. Die Sättigung der Summe wandert ans Ende des Zusatzblocks.
- Nicht geändert: Boden und Wasser (eigene Shader, eigener Datenweg), `vs_1_1` (zu wenige
  Konstanten), OpenGL (`arbvp1`).
- Platz: höchstens 138 Befehlsslots (Grenze vs_2_0: 256) und Temp-Register bis `r10`
  (Grenze vs_2_0: `r11`). Kein Original-Shader liest `c236`–`c246`, die höchste benutzte
  Konstante ist `c235`.

## Tests

```
python3 tests/test_lights8.py <Quelle>/patch.MPQ/Shaders/Vertex [...]
```

Emulator-Test für jede erweiterte Variante, mit IEEE-Rechnung und mit der D3D9-Regel
`0 · x = 0` (DXVK `d3d9.floatEmulation`):

- Licht 5–8 leer (Farbe 0, Position und Abschwächung beliebig): alle Ausgaben bitgleich
  zum Original.
- Licht 5–8 belegt: Farbe = Original mit Licht 1–4 + Original mit Licht 5–8 auf den
  Plätzen 1–4 − Original ohne Lichter.

```
x86_64-w64-mingw32-gcc -O2 -o runner.exe tests/d3d9/runner.c -ld3d9
WINE=wine python3 tests/d3d9_check.py <Data>/patch-5.MPQ runner.exe
```

Gegenprobe mit echter D3D9-Laufzeit unter Wine: Jede Variante muss sich anlegen lassen
und gezeichnet dieselbe Farbe liefern wie der Emulator.

## Dateien

- `tools/bls.py` – Lesen/Schreiben der `.bls` (Rundlauf bitgleich über alle Dateien)
- `tools/sm3.py` – Disassembler und Token-Werkzeug für D3D9-Shader (SM 2/3)
- `tools/lights8.py` – Zusatzblock für Licht 5–8
- `tools/build.py` – baut den Ordner `patch-5.MPQ` (`--debug`: Testfassung in Magenta)
- `tools/emu.py`, `tests/` – Emulator und Tests
- `docs/PLAN.de.md` – ursprünglicher Plan mit Risiken

## Bekannt

- In `patch.MPQ` sind `MapObjDiffuse_Comp.bls`, `MapObjDiffuse_T1_Env.bls` und
  `MapObjUDiffuse_T1_Env.bls` leer (0 Byte). Das Werkzeug überspringt sie.

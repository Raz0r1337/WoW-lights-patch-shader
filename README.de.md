# WoW-lights-patch-shader

English version: [README.md](README.md)

Werkzeug für WoW 3.3.5a (12340): baut aus den eigenen Original-Shadern Vertex-Shader,
die bis zu **8 Punktlichter** darstellen. Gegenstück zum Patch **„Mehr Lichter: 8 statt
4 Punktlichter (Grundlage für neue Shader)“** aus
[St0nys AIO WoW EXE Patcher](https://github.com/Raz0r1337/St0nys-AIO-WoW-EXE-Patcher)
([Patch-Beschreibung](https://github.com/Raz0r1337/St0nys-AIO-WoW-EXE-Patcher/blob/HEAD/docs/PATCHES.de.md#patch-lights)).
Ohne neue Shader liefert die Exe Licht 5–8 zwar an die Grafik, sichtbar wird es aber
nicht. Der Patcher nummeriert seine Patches, und die Nummern verschieben sich zwischen
seinen Zweigen (Stand 2026-10-17: Nr. 67 im veröffentlichten Patcher, `st0ny-main`;
Nr. 69 in `st0ny-dev`), darum nennt diese README die Patches bei ihren Kurznamen
„Mehr Lichter“ und „Lichter bleiben an“.

Das Repo enthält **keine Blizzard-Dateien**. Die neuen Shader entstehen beim Spieler
aus seinen eigenen Dateien.

## Fertiges Paket herunterladen

Wer nicht selbst bauen will, nimmt das fertige Zip von der
[Releases-Seite](https://github.com/Raz0r1337/WoW-lights-patch-shader/releases):

| Datei | Wofür |
|---|---|
| `patch-5.MPQ.zip` | **Normalfall**: Modelle, Gebäude und Boden mit 8 Lichtern |
| `patch-5.MPQ_without_terrain.zip` | nur Modelle und Gebäude; für eine Exe, deren „Mehr Lichter“ den Boden-Teil noch nicht hat (Patcher vor 2026-10-12) |
| `patch-5.MPQ_test_build_magenta.zip` | Testfassung, Licht 5–8 leuchten magenta (siehe „Im Spiel testen“) |
| `SHA256SUMS.txt` | Prüfsummen der drei Zips |

Das Zip in den `Data`-Ordner des Spiels entpacken, sodass es
`Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` gibt. Es enthält nur die
neu gebauten Dateien (34 bzw. 32 `.bls`), Aufbau wie ein MPQ, siehe „Ordner statt MPQ“.
Jedes Release baut ein Lauf auf GitHub aus den Original-Shadern und prüft vorher, dass
das Ergebnis bitgleich mit der im Spiel bestätigten Fassung ist (Abschnitt „Release-Lauf“).

## Voraussetzungen

- `Wow.exe` 3.3.5a mit „Mehr Lichter“, zum Testen am besten auch
  [„Lichter bleiben an, wenn ihre Quelle außerhalb des Bildes ist“](https://github.com/Raz0r1337/St0nys-AIO-WoW-EXE-Patcher/blob/HEAD/docs/PATCHES.de.md#patch-lightstay).
  Beide stehen seit 2026-10-17 im
  [veröffentlichten Patcher](https://github.com/Raz0r1337/St0nys-AIO-WoW-EXE-Patcher/releases)
  (v2026.10.17.2, Zweig `st0ny-main`); davor nur in `st0ny-dev`.
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

- `Wow.exe` mit „Mehr Lichter“ und „Lichter bleiben an“ patchen.
- In `WTF\Config.wtf` muss `SET gxApi "d3d9"` stehen (mit DXVK ohnehin) und
  `fixedFunction` darf nicht `1` sein (`/console fixedFunction 0`, danach Neustart).
  Unter OpenGL (`gxApi "opengl"`) nimmt das Spiel andere Shader, dann wirkt nichts.
- Ordner so ablegen, dass es `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls`
  gibt (nicht doppelt `patch-5.MPQ\patch-5.MPQ`). Der Ordnername ist frei, solange der
  Client ihn als Patch-Archiv erkennt, z. B. `patch-Z.mpq`.

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

Der Boden bleibt auch in der Testfassung ohne Magenta: Seine Erweiterung auf 8 Lichter
(seit 2026-10-14 Standard) hat keine Testfarbe, er rechnet immer mit den echten
Lichtfarben. Nahe an mehreren Feuern übersteuert das Magenta auf Modellen und schluckt
das Orange, das ist in der Testfassung so gewollt (volle Stärke 1,0 statt der echten
Lichtfarbe).

Stand 2026-10-11: Testfassung im Spiel bestätigt (Lagerfeuer im Brachland, ab dem
5. Feuer magenta; mit `fixedFunction 1` 8 Lichtquellen sichtbar).

### Wenn kein Magenta zu sehen ist

Dann ist entweder die Exe-Seite nicht aktiv oder die neuen Shader werden nicht
geladen. Zwei Tests trennen das:

**Exe-Seite ohne Shader prüfen.** Im Spiel `/console fixedFunction 1` eingeben und
das Spiel neu starten. In diesem Modus arbeitet das Spiel ohne Shader, und
„Mehr Lichter“ gibt dem Grafikgerät 8 Lichtplätze statt 4. Dann an einem dunklen Ort
nacheinander Lagerfeuer um die Figur stellen (Kochkunst, „Einfaches Lagerfeuer“):

| Was man sieht | Bedeutung |
|---|---|
| Ab dem 4. Feuer geht eins wieder aus (höchstens 3 Feuer leuchten gleichzeitig) | „Mehr Lichter“ ist nicht aktiv (Original: 4 Plätze, einer davon für die Sonne) |
| Bis zu 7 Feuer leuchten gleichzeitig auf die Figur | „Mehr Lichter“ arbeitet, die Exe liefert die Lichter |

Danach wieder `/console fixedFunction 0` und neu starten.

**Laden der Shader prüfen.** Mit `--ladetest` bauen:

```
python tools/build.py --ladetest Quelle "C:\WoW\Data"
```

Darin leuchten **alle** Punktlichter 1–8 in Magenta, auch die ersten vier. Sobald
mindestens 4 Lichtquellen in der Nähe sind (4 Lagerfeuer), muss die Figur magenta
angestrahlt sein, ganz gleich, was die Exe macht.

| Was man sieht | Bedeutung |
|---|---|
| Figur bei 4 Feuern magenta | Die Shader werden geladen. Fehlt in der normalen Testfassung trotzdem das Magenta ab dem 5. Feuer, kommt kein Licht 5–8 von der Exe an |
| Figur bei 4 Feuern normal beleuchtet | Die Shader werden nicht geladen (siehe unten) |

Werden die Shader nicht geladen:

- Pfad prüfen: `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` muss es geben.
- `WTF\Config.wtf`: `SET gxApi "d3d9"`. Unter OpenGL wirkt nichts.
- Den Ordner mit Ladik's MPQ Editor zu einem echten Archiv packen: neues MPQ
  `Data\patch-5.MPQ` anlegen (Ordner vorher umbenennen oder löschen), den Ordner
  `Shaders` hinzufügen, sodass die Pfade im Archiv `Shaders\Vertex\vs_3_0\…` lauten.
  Dann hat der Client keinen Ordner mehr, sondern ein normales Patch-MPQ.
- Mit DXVK lässt sich nachsehen, was wirklich geladen wird: Umgebungsvariable
  `DXVK_SHADER_DUMP_PATH` auf einen Ordner setzen, Spiel starten; die neuen Shader
  lesen `c236`–`c247`, die Originale nicht.

### Schritt 2: richtige Fassung

Die Testfassung durch die normale ersetzen (ohne `--debug` bauen). Zum Vergleich an
derselben Stelle mit derselben Kamera zwei Bildschirmfotos machen: einmal mit dem
Ordner, einmal ohne (Ordner z. B. in `_patch-5.MPQ` umbenennen, Spiel neu starten).
Mit dem Ordner werden Figur und Gebäude von mehr Lichtquellen gleichzeitig
beleuchtet. Läuft man an einer Reihe Fackeln vorbei, springt das Licht auf der Figur
seltener an und aus, weil erst das 9. Licht wegfällt statt schon das 5.

Ergebnis des Spieltests (2026-10-11, acht Lagerfeuer im Kreis, Brachland): Mit dem
Ordner sind die Steine der Lagerfeuer etwas heller und gleichmäßiger angeleuchtet,
weil jedes Feuer nun auch von den Nachbarfeuern Licht bekommt. Der Unterschied ist
klein, da ein Lagerfeuer nur wenige Meter weit leuchtet. Nichts fehlt, nichts ist
schwarz. Deutlicher wird der Unterschied bei einer Figur, die zwischen mehr als vier
nahen Lichtquellen steht, oder bei Fackelreihen in Städten.

Mit dem Boden (seit 2026-10-14 Standard, Exe mit „Mehr Lichter“ ab 2026-10-12):
Spieltest ohne Fehler, der Boden wird von allen acht Feuern beleuchtet statt von dreien
je Bodenstück.

### Ordner statt MPQ

Der Client öffnet einen Ordner mit MPQ-Namen wie ein Archiv. Im Spieltest (2026-10-11)
lief der Ordner direkt, ohne ihn zu packen, mit einer per
[St0nys AIO WoW EXE Patcher](https://github.com/Raz0r1337/St0nys-AIO-WoW-EXE-Patcher)
gepatchten Exe und dem Ordnernamen `patch-Z.mpq` (Buchstaben-Suffix, siehe dort Patch
Nr. 21 „Erweiterte MPQ-Namen erlauben“). Mit `--name patch-Z.mpq` baut das Werkzeug den
Ordner gleich unter diesem Namen.

Zum Hintergrund in der Original-Exe: `SFileOpenArchive` (VA `0x45C480`) fragt den
Dateityp ab (`0x427170`), ein Ordner (`FILE_ATTRIBUTE_DIRECTORY`, gesetzt bei
`0x435760`) bekommt Typ 2 und wird über `0x453E30` als Verzeichnis-Archiv geöffnet.
Lädt eine unveränderte Exe den Ordner nicht, hilft Packen mit Ladik's MPQ Editor zu
einem echten `patch-5.MPQ`.

Prüfen lässt sich das unter DXVK mit `DXVK_SHADER_DUMP_PATH`: Die neuen Shader lesen
`c236`–`c246`, die Originale nicht.

## Was geändert wird

- Nur die Varianten mit 4 Lichtern (Nr. 9, 19, …, 89 jeder Datei) der Modell-Shader
  (`Diffuse_*`, `CDiffuse_T1`) und Gebäude-Shader (`MapObj*`), in `vs_2_0` und `vs_3_0`.
  Das Spiel nimmt diese Varianten ab 4 Lichtern.
- Licht 1–4 bleiben Befehl für Befehl unverändert. Hinter der letzten Lichtaddition
  rechnet ein Zusatzblock (32 Befehle, dazu 2 zum Sichern von Position und Normale und
  ein `def c247`) Licht 5–8 nach derselben Formel wie das Original:

  ```
  L = Lichtposition - P;  d2 = dot(L, L)
  ndl = max(dot(L, N) * rsq(d2), 0)
  att = 1 / (a0 + a1 * d2 * rsq(d2) + a2 * d2)
  Summe += Farbe * ndl * att
  ```

  mit den Registern, die „Mehr Lichter“ belegt: `c236–c239` Farbe, `c240–c243` Position,
  `c244–c246` Abschwächung. Die Sättigung der Summe wandert ans Ende des Zusatzblocks.
  Der Nenner der Abschwächung wird vor dem Kehrwert per `max` auf `c247.w` (= 1e-6,
  eigener `def`) begrenzt, damit bei nie gesetzten Registern keine Division durch 0
  entsteht (siehe „Ohne Exe-Patch“).
- Nicht geändert: Boden und Wasser (eigene Shader, eigener Datenweg), `vs_1_1` (zu wenige
  Konstanten), OpenGL (`arbvp1`).
- Platz: höchstens 139 Befehlsslots (Grenze vs_2_0: 256) und Temp-Register bis `r10`
  (Grenze vs_2_0: `r11`). Kein Original-Shader liest `c236`–`c247`, die höchste benutzte
  Konstante ist `c235`.

### Ohne Exe-Patch

Sind die neuen Shader da, aber die Exe hat „Mehr Lichter“ nicht, schreibt die Exe nie
in `c236`–`c246`; dort steht dann 0 (unter DXVK sicher, da der Konstantenpuffer mit 0
beginnt; unter Windows-D3D9 nach Dokumentation ebenso). Farbe 0 heißt: Licht 5–8
tragen nichts bei, die Shader liefern bitgleich das Original mit 4 Lichtern. Ohne die
`max`-Begrenzung wäre die Abschwächung 1/0; 0 · unendlich ist nach IEEE NaN und nur
nach D3D9-Regel 0 (DXVK bildet die Regel nach, andere Hardware nicht sicher). Mit der
Begrenzung ist der Fall unabhängig davon sauber. Geprüft: `test_lights8.py` Test 3 und
`d3d9_check.py` (jede Variante zusätzlich mit `c236`–`c250` = 0).

Umgekehrt (Exe mit „Mehr Lichter“, Original-Shader): Licht 1–4 schreibt weiterhin die
unveränderte Original-Funktion nach `c17`–`c27`, und AddLight behält dieselben 4
nächsten Lichter wie ohne Patch. Die Exe lädt zusätzlich `c236`–`c246` hoch, was die
Original-Shader nicht lesen. Modelle, Gebäude und Boden sehen also aus wie im Original;
nur `fixedFunction 1` zeigt 8 Lichter. „Lichter bleiben an“ ist ein eigener Patch (im
veröffentlichten Patcher wie „Mehr Lichter“ Teil des Standard-Presets „Reforged“):
Lichter bleiben aktiv, wenn ihr Modell nicht im Bild ist. Das wirkt mit und ohne neue
Shader gleich und hat mit der Zahl der Lichter nichts zu tun.

Der Boden-Shader ist bei gar nicht gepatchter Exe aus demselben Grund
harmlos (eigener `def c251`). Ist aber „Mehr Lichter“ da und der Exe-Teil für den Boden
fehlt (Stand des Patchers vor dem 2026-10-12), stehen in `c236`–`c250` die
Modell-Lichter in anderem Format: der Boden wird falsch beleuchtet. Darum den Boden
nur mit einer Exe einsetzen, deren „Mehr Lichter“ den Boden-Teil hat.

Mit „Mehr Lichter“ **samt** Boden-Teil sind alle Kombinationen sauber, weil jeder Shader
`c236` ff. nur direkt nach seinem eigenen Upload liest („Mehr Lichter“ lädt vor jedem
Modell, der Boden-Teil vor jedem Bodenstück):

| Shader im Ordner | Modelle, Gebäude | Boden |
|---|---|---|
| Original | 4 Lichter (Original) | 3 Lichter (Original) |
| neu, mit `--ohne-boden` | 8 Lichter | 3 Lichter (Original) |
| neu (Standard) | 8 Lichter | 8 Lichter |

So ist es im Patcher umgesetzt (seit 2026-10-12): Der Boden-Teil ist fester Bestandteil
von „Mehr Lichter“, nicht einzeln wählbar. Gäbe es ihn ohne den Modell-Teil, läsen die
neuen Modell-Shader in `c236`–`c246` die Bodenlichter in falschem Format. Seit dem
Spieltest vom 2026-10-14 ist der Boden Standard beim Bauen.

## Tests

```
python3 tests/test_lights8.py <Quelle>
python3 tests/test_lights8.py <Quelle>/patch.MPQ/Shaders/Vertex [...]
```

Mit der `Quelle` von `build.py` prüft der Test genau die wirksamen Dateien, aus denen
auch gebaut wird (ältere, von einem Patch-MPQ überdeckte Fassungen aus `common-2`
bleiben außen vor; sie benutzen Befehle, die der Emulator nicht kennt). Mit einzelnen
`Vertex`-Ordnern werden alle Dateien darin geprüft.

Emulator-Test für jede erweiterte Variante, mit IEEE-Rechnung und mit der D3D9-Regel
`0 · x = 0` (DXVK `d3d9.floatEmulation`), dazu Test 3 mit `c236`–`c246` = 0 (Exe ohne
Patch, muss bitgleich sein):

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
- `tools/lights8.py` – Zusatzblock für Licht 5–8 (Modelle, Gebäude)
- `tools/terrain8.py` – Boden (Terrain.bls) von 3 auf 8 Lichter (siehe unten)
- `tools/build.py` – baut den Ordner `patch-5.MPQ` (`--debug`: Licht 5–8 in Magenta, `--ladetest`: alle Lichter in Magenta, `--ohne-boden`: Boden weglassen, `--nur modelle|gebaeude|boden`: nur eine Gruppe, zum Eingrenzen von Fehlern, siehe `docs/COA-VFOG.de.md`)
- `tools/paket.py` – packt den gebauten Ordner in ein Zip (Aufbau wie die Release-Zips)
- `tools/release.py` – baut die drei Fassungen, lässt die Tests laufen, vergleicht Prüfsummen, packt (siehe „Release-Lauf“)
- `tools/emu.py`, `tests/` – Emulator und Tests (`test_lights8.py`, `test_terrain8.py`, `d3d9_check.py`)
- `tests/pruefsummen/` – SHA-256 der im Spiel bestätigten Ausgabe und der Quelle
- `.github/workflows/release.yml` – der Release-Lauf auf GitHub
- `docs/PLAN.de.md` – ursprünglicher Plan mit Risiken
- `docs/BODEN.de.md` – Boden: Analyse, Exe-Stellen, Exe-Teil des Patchers

## Boden (Terrain)

Der Boden geht einen eigenen Weg: `Terrain.bls` rechnet je Bodenstück höchstens
3 Punktlichter aus eigenen Konstanten (c28–c36), die die Exe füllt (VA `0x7D0050`).
Der Modell-Teil des Lichter-Patches ändert daran nichts, darum bekam der Boden zunächst
weiter nur 3 der 8 Lichter und an den Kanten der Bodenstücke sieht man Sprünge (so auch
im Original). `tools/terrain8.py` erweitert die Boden-Varianten auf 8 Lichter, die
Licht 4–8 aus c236–c250 lesen (je Licht Position, Farbe, Abschwächung wie c28–c36).
Diese Konstanten liefert der Boden-Teil von „Mehr Lichter“ (im Patcher seit 2026-10-12);
Stellen, Format und die lesende Prüfung des Exe-Teils stehen in
[docs/BODEN.de.md](docs/BODEN.de.md). Spieltest 2026-10-14 (Sascha, acht Lagerfeuer):
keine Fehler, der Boden wird von allen Feuern beleuchtet. Seitdem baut das Werkzeug
den Boden standardmäßig mit.

**Ohne diesen Exe-Teil die Boden-Shader nicht einsetzen** (Exe mit einem Stand von
„Mehr Lichter“ vor dem 2026-10-12): Sie lesen dann Reste der Modell-Lichter und der
Boden wird falsch beleuchtet. Für so eine Exe den Boden weglassen:

```
python3 tools/build.py QUELLE ZIEL --ohne-boden
```

Test der Boden-Shader: `python3 tests/test_terrain8.py QUELLE`.

## Release-Lauf

`.github/workflows/release.yml` baut auf GitHub aus den Original-Shadern das fertige
Paket und hängt es an ein Release. Der Lauf ruft `tools/release.py` auf, das lokal
dasselbe tut:

```
python3 tools/release.py QUELLE AUSGABE [--version v1.0.0]
```

Schritte: Quelle entpacken, die drei Fassungen bauen, Emulator-Tests (Modelle/Gebäude,
Testfassung, Boden), Prüfsummen der gebauten Dateien gegen `tests/pruefsummen/`
vergleichen (sie müssen bitgleich mit der im Spiel bestätigten Fassung sein, sonst bricht
der Lauf ab), Zips packen, `SHA256SUMS.txt` und den Release-Text (englisch, Vorlage
`.github/release-notes.md`) schreiben. Die Zips sind reproduzierbar (Zeitstempel aus
`SOURCE_DATE_EPOCH`, im Lauf die Zeit des Commits).

**Auslöser:**

- Push auf einen Zweig: Probelauf, das Paket hängt als Artefakt `patch-5.MPQ` am Lauf.
- Tag `v*` pushen (`git tag v1.0.0 && git push origin v1.0.0`): Release mit diesem Tag.
- Auf der Actions-Seite „Release“ → „Run workflow“: mit `version` (z. B. `v1.0.1`) ein
  Release, leer ein Probelauf; `entwurf` legt das Release erst als Entwurf an. Gibt es die
  Version schon, erneuert der Lauf Text und Anhänge des Releases (etwa nach einer Änderung
  an der Vorlage) und entfernt Pakete, die er nicht mehr baut; der Tag bleibt.

**Woher der Lauf die Originale nimmt.** Blizzard-Dateien kommen nicht in den
Git-Verlauf. Darum liegen die Original-Vertex-Shader (`vs_2_0`, `vs_3_0` aus
`common-2`, `patch`, `patch-2`, `patch-3`, 126 Dateien) als `Shader-Quelle.zip` an einem
**nicht veröffentlichten Release-Entwurf** mit dem Tag `quelle` in diesem Repo. Ein
Entwurf ist nur für Leute mit Schreibzugriff sichtbar, und der Lauf lädt die Datei mit
seinem eigenen Token. Einrichten oder erneuern (einmalig, von Hand):

1. [Neues Release anlegen](https://github.com/Raz0r1337/WoW-lights-patch-shader/releases/new),
   bei „Choose a tag“ `quelle` eintippen (ergibt „Create new tag: quelle on publish“;
   der Tag entsteht erst beim Veröffentlichen, also nie).
2. Titel z. B. „Quelle (Entwurf, nicht veröffentlichen)“, `Shader-Quelle.zip` in das
   Feld für Anhänge ziehen.
3. **„Save draft“** klicken, nicht „Publish release“.

Das Zip hat den Aufbau `Shader-Quelle/<MPQ-Name>/Shaders/Vertex/vs_2_0|vs_3_0/*.bls`
(ein Ordner darüber ist erlaubt, der Lauf sucht die Wurzel); seine Prüfsummen stehen in
`tests/pruefsummen/quelle.sha256`, weicht die Quelle davon ab, meldet es der Lauf.
Ersatzweise nimmt der Lauf das Zip von der Adresse im Repo-Secret `QUELLE_URL`, wenn es
keinen Entwurf gibt.

**Wenn sich Quelle oder Werkzeug bewusst ändern** (die Prüfsummen also zu Recht nicht
mehr stimmen): lokal `python3 tools/release.py QUELLE AUSGABE --summen-schreiben`
laufen lassen, die Ausgabe im Spiel testen, dann `tests/pruefsummen/` mit einchecken.

## Bekannt

- In `patch.MPQ` sind `MapObjDiffuse_Comp.bls`, `MapObjDiffuse_T1_Env.bls` und
  `MapObjUDiffuse_T1_Env.bls` leer (0 Byte); in `common-2.MPQ` sind sie vorhanden.
  Das sind vermutlich Löschmarken des Patch-Archivs (das Spiel benutzt die Dateien
  dann nicht). Das Werkzeug überspringt sie.

# Antworten an das Projekt coa-vfog (Linien auf dem Wasser, Reichweite der Lichter)

Stand 2026-10-16. Fragen aus dem Projekt zu `Raz0r1337/coa-vfog` (version.dll-Proxy,
CoAVolFog.dll wrappt das D3D9-Gerät, schattiert das Wasser nach dem Liquid-Pass neu und
zeichnet volumetrischen Nebel nach der Welt). Tester: Stormhand mit dem CoA/Ascension-Client
und einer Exe aus St0nys AIO WoW EXE Patcher (Patches „Mehr Lichter“ und „Lichter bleiben an“
aus dem Zweig `st0ny-dev`, beide noch BETA).

Grundlage der Antworten: die unveränderte `Wow.exe` 3.3.5a (12340, SHA1
`178f78380affd260cb775d44397ba6b33ac05fdb`), die Original-Shader aus `patch.MPQ`,
`patch-2.MPQ`, `patch-3.MPQ` und `common-2.MPQ` eines unveränderten Clients, das Werkzeug
dieses Repos und der Patcher-Code (`apply_patches.ps1`, Zweig `st0ny-dev`, nur gelesen).
Alle VAs beziehen sich auf die unveränderte Exe (Dateioffset = VA − 0x400C00 für `.text`).
Was sich ohne den CoA-Client oder ohne coa-vfog nicht prüfen lässt, steht unter „Offen“.

## Kurzfassung

**Problem 1, Linien auf dem Wasser.** Die 34 Dateien des Ordners sind reine Vertex-Shader für
Modelle (M2), Gebäude (WMO) und Boden. Keine davon wird für Flüssigkeiten benutzt; der Client hat
dafür eigene Shader (`vsLiquidWater`, `vsLiquidWaterNoSpec`, `vsLiquidProcWater`, `vsLiquidMagma`,
`WaterRipples`), die der Ordner nicht anfasst. Nach dem Liquid-Pass kommen Boden- und Gebäude-Shader
nicht mehr vor, die Modell-Shader (`Diffuse_*`) aber schon: Die Pässe 1 und 2 der M2-Hauptszene
(transparente Modelle, Partikel) werden nach dem Wasser gezeichnet (Abschnitt 1.2). In allen Varianten sind Eingabe- und
Ausgabedeklarationen, die Befehle für `oPos`, Nebel und Texturkoordinaten und alle `def` des
Originals bytegleich; der Zusatzblock schreibt nur Temp-Register und ändert allein die
Vertexfarbe (statisch über alle 416 geänderten Varianten der 34 Dateien geprüft und im Emulator in 2496 Läufen bitgleich für `oPos`, Nebel, Texturkoordinaten und Alpha, Abschnitt 1.3). Ein Muster, das fest im Bildschirmraster liegt (alle 4 Zeilen, über die
ganze Breite gleich), kann ein Vertex-Shader nicht erzeugen; er wirkt je Dreieck in Weltkoordinaten.
Wenn der Ordner die Linien wirklich an- und ausschaltet, bleiben drei Wege, die ich von hier nicht
prüfen kann: (a) der CoA-Client bringt eigene Fassungen dieser Shader mit, die der Ordner
verdrängt oder die den Ordner verdrängen; (b) coa-vfog erkennt seine Durchgänge an den
Vertex-Shadern (Handle, Hash, Länge, gelesene Register) und erkennt die neuen Modell-Shader, die
nach dem Wasser gebunden werden, nicht wieder;
(c) der Ordner wird in dem Client gar nicht geladen und die Beobachtung ist Zufall. Dafür gibt es
die Test-Builds unten (Abschnitt 1.5) und die Rückfragen (Abschnitt 3).

**Problem 2, Lichter nur in der Nähe.** Das ist Verhalten der Original-Exe, nicht der Shader.
Ein Modell bekommt nur Lichter angeboten, die in einem festen Fenster von 2×2 Rasterzellen à
20 Yards um das Modell liegen (je Achse garantiert bis 10 Yards, höchstens bis 30 Yards Abstand,
Höhe egal), und davon die 4 (mit „Mehr Lichter“ 8) nächsten. Die Reichweite aus der M2-Datei
(`attenuation_start`/`attenuation_end`) liest der Client nie; jedes M2-Punktlicht hat die feste
Abschwächung 1/(0,7·d + 0,03·d²), also 10 % bei 10 Yards, 3,8 % bei 20 Yards. Einen Radius um die
Kamera gibt es nicht; stattdessen sind Lichter nur aktiv, wenn ihr Modell in diesem Bild animiert
wird (gezeichnet, Sichtkegel, Zeichendistanz nach Größenklasse, oder näher als 10 Yards an der
Kamera), sonst schaltet sie die Lichtabfrage ab („Lichter bleiben an“ hebt genau das auf). Die
Patch-Stellen, mit denen sich das Fenster und die Abschwächung ändern lassen, stehen in
Abschnitt 2.6 als Notiz für den Patcher.

## 1 Problem 1: Linien auf dem Wasser

### 1.1 Liefert der CoA/Ascension-Client eigene Fassungen der 34 Dateien?

Ohne den Client nicht prüfbar. Der Ordner wurde aus den unveränderten Dateien eines
Standard-Clients gebaut; was der CoA-Client in seinen eigenen Archiven mitbringt, weiß ich
nicht. Prüfweg, den der coa-vfog-Agent oder Stormhand selbst gehen kann:

1. **Prüfsummen vergleichen.** `tests/pruefsummen/quelle.sha256` in diesem Repo enthält die
   SHA-256 aller originalen `Shaders/Vertex/vs_2_0|vs_3_0/*.bls` aus `common-2.MPQ`, `patch.MPQ`,
   `patch-2.MPQ`, `patch-3.MPQ` (Schlüssel in Kleinschreibung, z. B.
   `patch.mpq/shaders/vertex/vs_3_0/diffuse_t1.bls`). Aus jedem Archiv des CoA-Clients, das einen
   Ordner `Shaders\Vertex` enthält, die Dateien exportieren (Ladik's MPQ Editor) und die Summen
   vergleichen. Jede Datei, die in einem CoA-Archiv liegt und nicht in dieser Liste steht, ist
   eine eigene Fassung. Dann zählt die Ladereihenfolge (Abschnitt 1.1a).
2. **Nachsehen, was wirklich geladen wird.** Mit DXVK `DXVK_SHADER_DUMP_PATH=<Ordner>` setzen und
   das Spiel starten; jeder geladene Shader landet dort als Datei. Die Fassungen aus dem Ordner
   lesen `c236`–`c247` (Modelle/Gebäude) bzw. `c236`–`c251` (Boden), die Originale nicht;
   `tools/sm3.py` disassembliert beide. Ein Vertex-Shader im Dump, der weder einem Original noch
   einer Datei des Ordners entspricht, ist eine CoA-Fassung.
3. **Ladetest.** `patch-5.MPQ_load_test_all_magenta.zip` (Abschnitt 1.5): Bei 4 oder mehr
   Lichtquellen in der Nähe muss die Figur magenta angestrahlt sein. Bleibt sie normal, wird der
   Ordner in diesem Client nicht geladen, und die Beobachtung mit/ohne Ordner misst etwas
   anderes.
4. **Aus den eigenen Dateien bauen.** `tools/build.py` arbeitet auf den Dateien des jeweiligen
   Clients. Bringt der CoA-Client eigene Shader mit, liefert ein Bau aus genau diesen Dateien die
   passende Fassung (oder meldet, welche Varianten das Werkzeug nicht erkennt).

#### 1.1a Ladereihenfolge der Patch-Archive

Aus `0x405AB0`/`0x405DD0` gelesen: Zuerst werden die Basisarchive der Tabelle `0xAB6158` geöffnet
(`common`, `common-2`, `expansion`, `lichking`, Locale-Archive usw.), dann in mehreren Durchläufen die
Patches nach den Mustern `patch-%s.MPQ`, `patch-%s-2.MPQ`, `patch-%d.MPQ` (Zeichenketten ab `0x9E26A0`),
jeweils per Verzeichnis-Enumeration `0x462000` und Sortierung mit `qsort` (`0x47B800`, Komparator
`0x401200` = negiertes `_strnicmp`). Jedes geöffnete Archiv bekommt eine höhere Priorität (`+0x1C`) als das
vorige, und die Dateisuche `0x45FA10` nimmt den Treffer mit der höchsten Priorität: **zuletzt geöffnet
gewinnt.** Sicher ist außerdem: Ein **Ordner** namens `patch-X.MPQ` wird wie ein Archiv eingebunden
(`0x45C480` fragt den Typ ab, Verzeichnis → `0x453E30`), darum funktioniert der Ordner `patch-5.MPQ` bzw.
`patch-Z.MPQ` ohne Packen.

Welche Namen in welcher Reihenfolge geöffnet werden (also ob `patch-Z` oder `patch-2` am Ende die höchste
Priorität hat), ist aus der Disassemblierung nur abgeleitet und **nicht im Debugger geprüft**. Die
verbreitete Erfahrung (höhere Buchstaben überdecken niedrigere, `patch-Z` überdeckt alles) und Saschas
Spieltests mit dem Ordner als `patch-Z.mpq` sprechen für Z vor 5. Praktische Regel: Bringt der CoA-Client
eigene Archive mit `Shaders\Vertex` mit, den Ordner als `patch-Z.MPQ` einbinden und mit dem Ladetest
(magenta) prüfen, ob er wirklich greift.

### 1.2 Wird einer der ersetzten Shader für Flüssigkeiten oder danach über dem Wasser benutzt?

Für Flüssigkeiten: nein. Nach dem Liquid-Pass: ja, die Modell-Shader (siehe unten). Die
Original-Shaderordner enthalten eigene Vertex- und Pixel-Shader für Flüssigkeiten:
`vsLiquidWater`, `vsLiquidWaterNoSpec`, `vsLiquidProcWater%s` (das Suffix ist zur Laufzeit
leer, `0x7997F0`), `vsLiquidMagma` und `WaterRipples`, dazu `psLiquid*`. Die Exe baut diese Namen bei
0xA59534, 0xA59564, 0xA59504, 0xA59594 (Zeichenketten) und benutzt sie in der
Flüssigkeits-Zeichenfunktion (Materialkonstruktoren ab `0x8A3DC0`; die Wasser-Zeichenfunktion `0x8A5590` setzt Vertex- und Pixel-Shader als Renderstate `0x4D`/`0x4E` aus eigenen Tabellen `[0xD44C10+idx·4]`/`[0xD44C0C]`). Keiner der 17 Namen des Ordners kommt dort vor.

Die 17 Namen des Ordners lädt die Exe nur an drei Stellen: `0x836500` (M2-Effekte aus `Model2.wfx`),
`0x7AFE80` (WMO) und `0x79E7C0` (Boden, Tabelle `0xCE0008`); in den Flüssigkeitsfunktionen `0x8A48F0`,
`0x8A5590`, `0x8A5900`, `0x8A6090` kommt keine dieser Tabellen vor. Ob Flüssigkeiten überhaupt mit Shader
gezeichnet werden, entscheidet `0x8A2005` (Vertex-Shader-Stufe ≥ 1, Flag `[0xD43AF0]`, Pixel-Shader-Stufe ≥ 3);
sonst nimmt der Client Fixed-Function-Materialien ohne Shader (`0x8A5C70`, `0x8A6350`, `0x8A5170`).
`WaterRipples` ist ein eigenes Shader-Paar für Wellenringe und Kielwasser (`splash.blp`/`wake.blp`), geladen
bei `0x79E23E`, gezeichnet in `0x79D5E0` nach der Welt, nicht Teil des Liquid-Passes; der Ordner ersetzt es
nicht.

**Zeichenreihenfolge** (für die Frage, was *nach* dem Liquid-Pass über dem Wasser liegt):

```
Welt 0x79A870:   Boden 0x798DA0 → Gebäude 0x7964A0 → 0x795F80 → 0x7968D0/0x796C10
                 → M2-Nebenszene 0x7F09B0 → 0x793980 → Flüssigkeiten 0x8A2240 → Debug-Linien 0x7D5610
Bild 0x4F8EA0:   Welt → 0x77F070 → M2-Hauptszene Pass 0 (0x823CB0)
                 → je nach 0x780620:  Pass 2 → WaterRipples → 0x77F030 → 0x77F980
                                oder: 0x77F980 → Pass 1 → 0x77F030 → WaterRipples → Pass 2
```

Das heißt: **Boden- und Gebäude-Shader werden nach dem Liquid-Pass nicht mehr benutzt.** Die
**Modell-Shader** (`Diffuse_*`, `CDiffuse_T1`) dagegen schon: Die Pässe 1 und 2 der M2-Hauptszene
(transparente Modelle, Partikel; welcher Pass was enthält, ist nicht einzeln belegt) werden **nach** dem
Wasser gezeichnet, dazu Detail-Doodads mit eigenem Shader `DetailDoodad` und die `WaterRipples`. Wenn
coa-vfog nach dem Liquid-Pass oder am Ende der Welt ansetzt und dabei die gebundenen Vertex-Shader
auswertet, sieht es dort die geänderten Modell-Shader (längerer Bytecode, `def c247`, Lesezugriffe auf
`c236`–`c247`); das ist der konkreteste Berührungspunkt zwischen dem Ordner und einem Nachbearbeitungsschritt
auf dem Wasser (Rückfrage 1 in Abschnitt 3). Die Test-Builds `models_only` und `buildings_only` trennen genau
diesen Fall.

### 1.3 Sind Ausgaberegister, Semantiken und Nebelausgabe bitgleich zum Original?

Ja, in allen Varianten beider Profile. Das folgt aus dem Aufbau der Änderung und wurde mit einem
Vergleichsskript über alle Varianten geprüft:

- `tools/lights8.py` fügt den Block für Licht 5–8 unmittelbar hinter die letzte Lichtaddition
  des Originals (`mad … c20 …`) ein, `tools/terrain8.py` hinter die dritte Lichtaddition des
  Bodens. Davor und danach stehen die Befehle des Originals unverändert, in gleicher Reihenfolge.
- Der Block schreibt ausschließlich Temp-Register: zwei, die die Variante nie benutzt (Sicherung
  von Position und Normale), und vier, die nach der Einfügestelle nicht mehr gelesen werden. Das
  einzige Register, dessen Wert sich nach dem Block unterscheidet, ist die Lichtsumme, und die
  geht nur in die Vertexfarbe ein.
- Alle `dcl` (Eingaben, bei vs_3_0 auch die Ausgaben `o#` mit ihren Semantiken) und alle `def`
  des Originals bleiben bytegleich; neu ist nur `def c247` (Modelle/Gebäude) bzw. `def c251`
  (Boden). Die Befehle, die `oPos`, `oFog`/Nebel-`o#`, `oD#`, `oT#` schreiben, bleiben bytegleich.
- Einzige Änderung an einem Originalbefehl: Bei Modellen und Gebäuden im Profil vs_3_0 wandert
  die Sättigung (`_sat`) von der letzten Lichtaddition auf die letzte Addition des Blocks, damit
  Licht 5–8 vor der Sättigung dazukommen. In vs_2_0 (dort sättigt das Original später per `min`)
  und beim Boden ändert sich kein Originalbefehl.

**Prüfung (Skript `vergleich.py` über den frischen Bau, Ergebnis identisch zum Release).** Je Profil
(vs_2_0, vs_3_0) 17 Dateien mit 1568 Varianten; davon sind 208 je Profil geändert (16 Modell-/Gebäudedateien ×
9 Vier-Lichter-Varianten + 64 Drei-Lichter-Varianten des Bodens), die übrigen 1360 je Profil sind bytegleich
zum Original, Datei- und Variantenköpfe (Magic, Version, Flags, Eingaben) ebenfalls. Für alle 416 geänderten
Varianten gilt:

| Prüfung | Ergebnis |
|---|---|
| Versions-Token, alle `dcl` (Eingaben, bei vs_3_0 auch `o#` mit Semantik) | 416/416 bytegleich, nichts eingefügt |
| alle `def` des Originals | 416/416 bytegleich und in gleicher Reihenfolge; einziger Zusatz `def c247 = (1, 0, 1, 1e-6)` bzw. `def c251 = (1e-6, 0, 0, 0)` |
| alle Befehle, die ein Ausgaberegister schreiben (`oPos`, `oFog`, `oD#`, `o#`) | 416/416 bytegleich, kein eingefügter Befehl schreibt eine Ausgabe |
| gelesene Konstanten | Original liest höchstens c235; der Block liest c236–c247 bzw. c236–c251 und darunter nur `def`-Nullen/-Einsen (Boden zusätzlich c0–c2) |
| Zusatzblock | schreibt nur Temps; danach lebt davon nur die Lichtsumme; Sicherungsregister für Position/Normale sind in der Variante sonst unbenutzt |
| geänderte Originalbefehle | vs_3_0 Modelle/Gebäude: genau einer (`mad_sat … c20` → `mad`, `_sat` wandert auf den letzten Block-`mad`); vs_2_0 Modelle/Gebäude und Boden beider Profile: keiner |
| Nebel | genau ein Nebel-Schreibbefehl je Variante; seine Rückwärtskette (Temps, `a0` aus `mova`) ist befehlsgleich zum Original. In 206 Varianten steht der Nebel vor dem Block, in 210 Knochen-Varianten danach, aus frisch berechneten Werten |
| Limits | vs_2_0 höchstens 215 von 256 Slots, r10 von r11; vs_3_0 höchstens 197 von 512 Slots |
| Emulator (`tools/emu.py`, float32, Regeln IEEE und D3D9 „0·x = 0“, 3 Saaten × 512 Vertizes) | 2496 Läufe mit belegten Lichtern 5–8 (Boden 4–8): alle Ausgaben außer rgb der Vertexfarbe bitgleich, Alpha bitgleich, kein NaN/Inf; 832 Läufe mit leeren Lichtern 5–8: alles bitgleich inkl. Farbe |

Nicht geprüft: echte GPU/Treiber (der Emulator rechnet float32 je Befehl); strukturell ist die Gleichheit
aber abgesichert, weil kein Befehl, der Position, Nebel oder Texturkoordinaten schreibt, und keine seiner
Eingaben vom Block berührt wird.

### 1.4 Kann der längere Shader unter DXVK das Positionsergebnis ändern? Tiefentest EQUAL?

**Position.** Die Befehle, die `oPos` berechnen, sind in jeder Variante bytegleich und stehen
vor der Einfügestelle; sie lesen nur Eingaben, Konstanten unter c236 und Temps, die der Block
nicht berührt. Unter DXVK übersetzt der D3D9-Shader-Übersetzer (dxso) jeden Befehl einzeln nach
SPIR-V; gleiche Befehle ergeben gleichen SPIR-V-Code, und mit der Standardeinstellung
`d3d9.invariantPosition = True` wird die Positionsausgabe zusätzlich als `Invariant` markiert, was
dem Treiber verbietet, sie je nach Shader unterschiedlich zu optimieren. (`d3d9.longMad`
entscheidet nur, ob `mad` als `fma` oder als `mul`+`add` übersetzt wird, für Original und neue
Fassung gleich.) Diese DXVK-Angaben stammen aus meiner Kenntnis des DXVK-Quelltexts und wurden in
dieser Sitzung nicht erneut nachgelesen. Bei nativem D3D9 (Windows ohne DXVK) gibt es keine
formale Garantie zwischen zwei verschiedenen Shadern, aber derselbe Befehlsvorlauf wird von den
Treibern praktisch identisch übersetzt; die Befehlszahl dahinter spielt dafür keine Rolle.

Unabhängig davon: Ein Positionsunterschied im letzten Bit zeigt sich als Tiefenflimmern entlang
von Dreiecken, in Weltkoordinaten, nicht als waagerechte Linien, die im Bildschirmraster alle 4
Zeilen liegen und über die ganze Breite gleich sind. Das Muster passt zu einem Bildraumeffekt
(Puffer in halber oder viertel Auflösung, Rauschmuster, Zeilenversatz).

**Tiefentest.** Nein, der Client zeichnet weder Boden noch Gebäude in mehreren Pässen mit Tiefentest EQUAL. Der
Tiefenvergleich ist Renderstate `0xE` mit den Werten 0 = LessEqual, 1 = Equal, 2 = GreaterEqual, 3 = Less
(D3D-Tabelle `0xA2FA14` = {4, 3, 7, 2}, GL-Tabelle `0xAD8E80`). Die einzigen Schreiber dieses States sind die
Standardwerte `0x6865B0` (`0x68680A`) und die M2-Szene `0x823827`, beide setzen 0 (LessEqual); EQUAL wird
nirgends gesetzt. Ein Boden-Chunk mit bis zu 4 Texturlagen wird im Shader-Pfad `0x7D2D70` in **einem**
Drawcall gezeichnet (Lagen in Texturstufen 0–3, Alphakarte dahinter, Vertex-Shader-Variante aus `0xCE0008`
über `0x79E470`, Pixel-Shader `Terrain0`–`3` nach Lagenzahl aus `0xD1D080`); nur der Fixed-Function-Pfad
`0x7D0760` (ohne Shader) zeichnet je Lage einen Drawcall, mit Blending statt EQUAL. Gebäude-Gruppen zeichnet
`0x7ABF50` einmal. Ein Positionsunterschied zwischen zwei Shadern könnte also nur dort auffallen, wo
dasselbe Dreieck zweimal gezeichnet wird; das kommt mit den ersetzten Shadern nicht vor.

### 1.5 Test-Builds zum Eingrenzen

Liegen im Projektordner `ausgabe/coa-vfog/` (für Sascha) und sind mit dem neuen Schalter
`tools/build.py --nur modelle|gebaeude|boden` jederzeit nachbaubar. Jede Datei in den
Teilfassungen ist bytegleich zur gleichnamigen Datei des Release v1.0.0 (`patch-5.MPQ.zip`,
geprüft gegen `tests/pruefsummen/patch-5.MPQ.sha256`); die Teilfassungen lassen nur Dateien
weg.

| Zip | Dateien | Inhalt |
|---|---|---|
| `patch-5.MPQ.zip` | 34 | alles (Referenz, = Release v1.0.0) |
| `patch-5.MPQ_without_terrain.zip` | 32 | Modelle + Gebäude, kein `Terrain.bls` |
| `patch-5.MPQ_models_only.zip` | 18 | nur `Diffuse_*.bls`, `CDiffuse_T1.bls` (M2) |
| `patch-5.MPQ_buildings_only.zip` | 14 | nur `MapObj*.bls` (WMO) |
| `patch-5.MPQ_terrain_only.zip` | 2 | nur `Terrain.bls` |
| `patch-5.MPQ_load_test_all_magenta.zip` | 32 | Modelle + Gebäude, alle Lichter 1–8 magenta (Ladetest) |

Testablauf (gleicher Ort, gleiche Kamera, gleiche Exe, nur der Ordner wechselt): Ordner
entpacken, sodass es `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` gibt (bei Bedarf als
`patch-Z.MPQ`, falls ein Archiv des Clients `patch-5` überdeckt, Abschnitt 1.1a), Spiel starten,
flach auf fernes Wasser sehen, Linien ja/nein notieren. Lesart:

| Linien bei … | Verursacher |
|---|---|
| nur `models_only` | Modell-Shader |
| nur `buildings_only` | Gebäude-Shader |
| nur `terrain_only` | Boden-Shader |
| keiner Teilfassung, aber der vollen | nur im Zusammenspiel (bitte melden) |
| auch ohne Ordner | nicht die Shader |
| Ladetest ohne Magenta | der Ordner wird nicht geladen, die anderen Ergebnisse sagen nichts |

Dazu bitte notieren: Exe (Patcher-Zweig, „Mehr Lichter“/„Lichter bleiben an“ an oder aus),
Auflösung, DXVK ja/nein, und ob die Linien mit `/console fixedFunction 1` (dann greift kein
Vertex-Shader) ebenfalls auftreten.

### 1.6 Einschätzung

Das Muster (fest im Bildschirmraster, alle 4 Zeilen bei 1080 Zeilen Höhe, über die volle Breite
gleich, nur im Wasserband) ist ein Bildraumeffekt. Die Vertex-Shader des Ordners rechnen je
Vertex in Welt- bzw. Kamerakoordinaten und schreiben außer der Vertexfarbe dieselben Werte wie das
Original; das Wasser selbst benutzt sie nicht. Eine Kopplung an den Ordner wäre nur über einen
der drei Wege aus der Kurzfassung möglich. Besonders prüfenswert ist (b): Wenn coa-vfog seine
Durchgänge daran erkennt, welche Vertex-Shader gebunden sind (Handle aus `CreateVertexShader`,
Hash oder Länge des Bytecodes, Befehlszahl, gelesene Konstanten), dann erkennt es die 34 neuen
Fassungen nicht als „Welt“ und setzt vielleicht Tiefe oder Nebel an der falschen Stelle an. Die
neuen Fassungen unterscheiden sich vom Original genau so: anderer Bytecode (länger), ein
zusätzlicher `def c247`/`def c251`, Lesezugriffe auf `c236`–`c251`, bei Modellen/Gebäuden in
vs_3_0 das verschobene `_sat`; Deklarationen, Ausgaben und Konstanten unter c236 sind gleich.

## 2 Problem 2: Lichter leuchten nur in der Nähe

Alles in diesem Abschnitt ist aus der Original-Exe 3.3.5a (12340) gelesen (Adressen sind
virtuelle Adressen, Dateioffset = VA − 0x400C00 im `.text`). Die Shader des Ordners ändern an
keiner dieser Stufen etwas; sie bekommen die Lichter fertig ausgewählt in `c17`–`c27` bzw.
`c236`–`c251` geliefert. Die Reichweite entsteht in vier Stufen, die nacheinander greifen:

| Stufe | Wo | Wirkung |
|---|---|---|
| 1 Modell wird in diesem Bild animiert? | `0x828A00`, Animate-Liste der Szene | nein → Licht wird beim nächsten `QueryLights` abgeschaltet („Lichter bleiben an“ hebt das auf) |
| 2 Gitterfenster um das beleuchtete Objekt | `QueryLights 0x81E400`, 64×64 Zellen à 20 Yards | Modelle: 2×2 Zellen = 40×40 Yards; Boden: Zellen um r ≈ 23,6 Yards; Gebäude: Zellen um die WMO-Kugel |
| 3 die 4 nächsten Lichter | `AddLight 0x834F60` | nur 3D-Abstand zum Objekt, keine Reichweite („Mehr Lichter“: 8) |
| 4 Abschwächung im Shader | `c25`–`c27`, fest 0 / 0,7 / 0,03 | 1/(0,7·d + 0,03·d²): 10 Yards → 10 %, 20 → 3,8 %, 30 → 2,1 % |

Einen Radius um die **Kamera**, innerhalb dessen Lichter aktiv wären, gibt es nicht. Stufe 1
ist die einzige, die mit der Kamera zu tun hat, und zwar indirekt: Ein Licht hängt an seinem
Modell, und das Modell wird nur animiert, wenn es gezeichnet wird oder näher als 10 Yards an der
Kamera steht.

### 2.1 Wie wählt der Client je Modell/Chunk die Lichter aus (AddLight)?

**Datenstruktur.** Jedes beleuchtete Objekt hat eine `CM2Lighting` (0xD4 Byte): `+4/+8/+0xC`
Position, `+0x10` Radius, `+0x84..+0x90` vier Zeiger auf gewählte Lichter, `+0x94..+0xA0` deren
Abstandsquadrate (aufsteigend), `+0xA4` Anzahl. Ein Licht (`CLight`, 0x6C Byte innerhalb eines
0xD4-Laufzeiteintrags) hat `+0` Zeiger auf die Szene/den Lichtmanager (nicht auf das Modell),
`+4` Zeitstempel (Bild-Nummer), `+8` Typ (1 = Punktlicht), `+0xC..+0x14` Weltposition,
`+0x3C..+0x44` Farbe, `+0x54/+0x58/+0x5C` Abschwächung a0/a1/a2, `+0x60` aktiv,
`+0x64/+0x68` Kettenzeiger der Gitterzelle.

**Ablauf je Objekt und Bild.**

1. `Initialize 0x834900` (bzw. `0x790440` für Boden/Gebäude) setzt Position und Radius der
   `CM2Lighting` und leert die Auswahl.
2. `QueryLights 0x81E400` (`ecx` = Szene `[0xCD754C]`) übergibt zuerst alle Nicht-Punktlichter
   der Liste `[Szene+0x20]` an `AddLight`, dann läuft es über ein Zellfenster des 64×64-Gitters
   `[Szene+0x24]` (Abschnitt 2.2) und übergibt jedes dort eingehängte Punktlicht an `AddLight`,
   außer sein Zeitstempel `+4` ist nicht die aktuelle Bild-Nummer `[Szene+0x14]`: dann wird es
   per `SetEnabled(0)` (`0x81E54A` → `0x8356F0`) aus dem Gitter ausgehängt und nicht angeboten
   (Abschnitt 2.3).
3. `AddLight 0x834F60` nimmt nur aktive Lichter (`+0x60 ≠ 0`), rechnet für Punktlichter das
   3D-Abstandsquadrat zur Objektposition (`0x834F7E–0x834FB8`) und sortiert das Licht in die
   höchstens 4 Plätze ein; bei 4 belegten Plätzen fliegt es raus, wenn d² ≥ Abstand des vierten
   (`0x834FBC fcom [ecx+0xA0]`). Reichweite, Abschwächung oder Kamera werden nicht geprüft
   (keine Lesezugriffe auf `+0x54..+0x5C`, keine Vergleiche mit `[0xCD8F5C]`).
4. Danach kommen Sonne bzw. das Richtungslicht der Zone dazu (`[0xCE04A8]+0x58`, bei
   Gebäuden über die virtuelle Methode `0x7B3F30`/`0x7C3DB0`, beim Boden `0x7B7BE5`).
5. `0x872900` schreibt die gewählten Lichter in die Shader-Konstanten `c17`–`c27` (Aufrufer
   `0x873E85` Modelle, `0x7A91A9` Gebäude); der Boden nimmt `GetLight 0x8349E0` über
   `0x7D00E0` und schreibt `c28`–`c36` (`0x7D0050`). Leere Plätze bekommen Farbe (0,0,0,0);
   Position und Abschwächung bleiben stehen. „Mehr Lichter“ erweitert genau diese Stufe auf
   8 Plätze und `c236`–`c250`.

Welches Objekt bestimmt das Fenster: Bei **Modellen** (M2) ist es die `CM2Lighting` bei
`Modell+0x1D4`, aufgebaut in `0x831AF0` aus dem transformierten Mittelpunkt der Modellkugel
(`0x831B14 … 0x4C21B0`) und **Radius 0** (`0x831B25 fldz`). Beim **Boden** ist es eine
`CM2Lighting` je `CMapRenderChunk`, Mittelpunkt `chunk+0x24`, Radius `chunk+0x30` = halbe
Diagonale der Chunk-AABB (`0x7B7AF0`), flach ≈ 23,6 Yards, bei zusammengelegten Chunks größer.
Bei **Gebäuden** (WMO) gibt es eine `CM2Lighting` je WMO-Instanz (nicht je Gruppe) aus der
Instanzkugel `+0x3C` (Mittelpunkt) / `+0x48` (Radius), `0x79670B–0x796727`; danach zeichnet
`0x7ABF50` alle Gruppen der Instanz mit dieser einen Auswahl. Im Patcher-Repo werden WMO
deshalb nicht „pro Raum“ beleuchtet, sondern pro Gebäude.

### 2.2 Gibt es einen Radius, innerhalb dessen Lichter überhaupt aktiv sind? Das Gitterfenster

**Gitter.** Beim Einschalten eines Punktlichts (`SetEnabled(1)` → `0x834C70`) wird es in die
Zelle `(floor(y·0,05) & 63)·64 + (floor(x·0,05) & 63)` eingehängt: Zellen von 20 Yards,
64×64 Zellen, Umlauf alle 1280 Yards, `z` wird ignoriert (Skala `[0xAF59D4]` = 0,05).

**Fenster in `QueryLights`.** Aus Position `(x, y)` und Radius `r` des Objekts
(`z` wird nicht gelesen):

```
x_min = floor((x − r)·0,05 − 0,5)      x_max = floor((x + r)·0,05 + 0,5)
y_min = floor((y − r)·0,05 − 0,5)      y_max = floor((y + r)·0,05 + 0,5)
```

(`0x81E431–0x81E4F9`, Skala `[0xAF58A0]` = 0,05, Bias `[0x9E2EC4]` = 0,5, `0x88CE30` ist das
CRT-`floor`, geprüft.) Beide Achsen laufen mit `& 0x3F` um. Daraus folgt je Achse: Ein Licht
wird dem Objekt **sicher** angeboten, wenn `|x_Licht − x| ≤ r + 10`, und **höchstens** bis
`|x_Licht − x| < r + 30` (je nach Lage zum 20er-Raster); in `z` unbegrenzt.

Für Modelle (r = 0) ist das Fenster also immer genau **2×2 Zellen, 40×40 Yards**, um das
nächste 20er-Vielfache von (x, y). Beispiele für die Lichter, die ein Modell bei x angeboten
bekommt (Intervall in x): x = 0 → [−20, 20), x = 10 → [−20, 40), x = 19,99 → [0, 40). Ein
Feuer 25 Yards neben einer Figur wird je nach Rasterlage angeboten oder nicht, eines 31 Yards
daneben nie. Das ist der Teil von „Lichter nur in der Nähe“, der am ehesten wie ein Radius
wirkt, aber es ist ein Fenster um das **beleuchtete Objekt**, nicht um die Kamera.

Boden-Chunks (r ≈ 23,6) sehen je Achse sicher bis ≈ 34 Yards, höchstens ≈ 54; Gebäude je nach
Kugelradius weiter. Einzige echte Entfernungsschranke neben dem Fenster: WMO-**interne**
Lichter (Liste `[Instanz+0x98]`) werden nur angeboten, wenn die Sichttiefe des
Instanz-Mittelpunkts `+0x4C` kleiner ist als `[0xCD7668]` (`0x7B3F4D`; Nebel-Ende aus
`[0xD38B00]+0x94`, Rückfall 100000), wahrscheinlich, nicht bis zur Nebeltabelle verfolgt.

**Abfrage `0x81E400` und „Animationsdistanz“.** Die Lichtabfrage selbst hat keine Distanz zur
Kamera. Was coa-vfog als „Lichter nur in der Nähe“ sieht, ist die Summe aus dem Fenster (2.2)
und der Animate-Kopplung (2.3), und für Lichter, die coa-vfog aus einer `CM2Lighting` oder aus
den Shader-Konstanten liest, zusätzlich die 4er-Auswahl (2.1).

### 2.3 Warum Lichter ferner Modelle abgeschaltet werden: Animate-Liste und Zeitstempel

Die Lichter eines M2-Modells werden nur in `0x828A00` (Modell-Lichtaktualisierung)
bearbeitet: Position aus Knochen- und Modellmatrix (`0x828ADB/0x828AE8 → SetPosition 0x835690`),
`SetEnabled(Sichtbarkeitsspur ≠ 0 && Freigabe ≠ 0)` (`0x828B83`) und Zeitstempel
`CLight+4 = [Szene+0x14]` (`0x828B9C`). `0x828A00` läuft aus `0x821A20` (Szene-Animate,
erhöht `[Szene+0x14]` bei `0x821A2D`) für jedes Wurzelmodell der **Animate-Liste**
`[Szene+0x28]`, plus Rekursion in angehängte Modelle und Partikel-Kindmodelle. Ein Modell, das
in einem Bild nicht in dieser Liste steht, bekommt keinen neuen Zeitstempel; beim nächsten
`QueryLights` eines beliebigen Objekts gilt sein Licht als veraltet und wird per
`SetEnabled(0)` ausgehängt (`0x81E545 cmp eax,[edx+0x14]; 0x81E548 je`). Es bleibt aus, bis
`0x828A00` es wieder einschaltet.

Wann ein **Kartendoodad** (Lagerfeuer, Laterne usw.) in die Animate-Liste kommt
(`0x823F10(1)`), entscheidet je Chunk `0x7987A0` (gleich in `0x799A4A` ff. und `0x799BDA` ff.):

- es wird gezeichnet: Sichtkegel `0x983D20`, Verdeckungs-/Horizonttest `0x7CCE00`/`0x78FC40`,
  dann `0x791CB0` mit Zeichendistanz nach Größenklasse (`Doodad+0x24`): Basis 30 / 100 / 200 /
  750 / 1250 Yards (Tabelle `0xADF364`), mit CVar `environmentDetail` (0,5..1,5) multipliziert
  und quadriert nach `0xADF3B4`; jenseits davon kein Einhängen (`0x791E8B`); ohne Kartenflag
  `[0xCD774C] & 0x4000` oder mit Doodad-Flag 0x800 ohne Distanzprüfung;
- oder es hat Doodad-Flag 0x400 (`0x7988CB`);
- oder es ist näher als **10 Yards** an der Kamera: `d² < [0x9E8CC8]` = 100
  (`0x7988FC`, `0x799A79`, `0x799C18`, Kameraposition `[0xCD8F5C..0x64]`);
- sonst `0x823F10(0)`: aushängen, Lichter erlöschen beim nächsten `QueryLights`.

Das ist die eigentliche Antwort auf „Radius um die Kamera“: Es gibt ihn nur für
**nicht gezeichnete** Doodads (10 Yards), für gezeichnete gilt die Zeichendistanz ihrer
Größenklasse. Ein kleines Lagerfeuer (Klasse 0, 30 Yards × `environmentDetail`) hinter der
Kamera oder außerhalb des Sichtkegels verliert sein Licht, sobald es mehr als 10 Yards weg ist,
auch wenn es die Figur vor der Kamera noch beleuchten müsste. Ein Lagerfeuer im Bild verliert
sein Licht, wenn es jenseits seiner Zeichendistanz liegt, bei `environmentDetail 1.0` also ab
30 Yards bei Klasse 0 (die Klasse hängt von der Modellgröße ab, Grenzen `0xADF350`: 1 / 4 /
15 / 100 Yards).

Patch **„Lichter bleiben an“** (Datei `0x41D948` = VA `0x81E548`, `je` → `jmp`) macht
`QueryLights` zeitstempelblind: Lichter nicht animierter Modelle bleiben mit der letzten
Position, Farbe und Sichtbarkeit im Gitter (eingefroren, die M2-Spuren laufen nicht weiter).
Er ändert nichts an Fenster, 4er-Auswahl und Abschwächung. Beim Entladen eines Modells werden
seine Lichter weiterhin sauber abgemeldet (`0x823DE0`, `0x824DE0`), es bleiben keine Waisen.
`M2Faster` hat auf diesen Weg keinen Einfluss (`0x81C060` setzt nur Batch-Flags).

Offen (nicht gelesen): die weiteren Aufrufer von `0x823F10` für WMO-Innendoodads und
Spielobjekte (`0x4D979F`, `0x597553`, `0x601907`, `0x619907`, `0x6F84B9` ff., `0x701ED7`,
`0x7823EB`, `0x782459`, `0x7F0903`, `0x9601A1`, `0x9ABD68`); ob dort dieselben Distanzregeln
gelten, ist nicht geprüft.

### 2.4 Abschwächung: fest in der Exe, nicht aus der M2-Datei

Der Lichtkonstruktor `0x834A40` setzt a0 = 0 (`fldz`, `0x834A7C`), a1 = `[0x9E2EC0]` = 0,7
(`0x834A81`), a2 = `[0x9F23C8]` = 0,03 (`0x834A94`); das sind die einzigen Schreiber von
`CLight+0x54/+0x58/+0x5C` im ganzen `.text`. Die M2-Spuren `attenuation_start` (Def `+0x60`)
und `attenuation_end` (Def `+0x74`) werden nirgends ausgewertet (Lichtschleife
`0x830401–0x830624` liest nur Typ, Knochen, Farben, Intensitäten und Sichtbarkeit). Die
Lichtfarbe `+0x3C` = Diffusfarbe × Diffusintensität × Modellalpha (`0x8305B9–0x8305FE`).

Im Shader (Original `Diffuse_T1`, Variante 13, geprüft): `d²` per `dp3`, `d = d²·rsq(d²)`,
`att = 1/(c25 + c26·d + c27·d²)` (`rcp`), dann `max(N·L, 0)·att·Lichtfarbe`. Mit den festen
Werten: 1/(0,7·d + 0,03·d²).

| Abstand d (Yards) | Faktor |
|---|---|
| 2 | 0,65 |
| 5 | 0,24 |
| 10 | 0,10 |
| 20 | 0,038 |
| 30 | 0,021 |

Ein Licht, das den Weg durch Stufe 1–3 schafft, wirkt also auch in 30 Yards noch mit 2 %
seiner Farbe; eine „harte Kante“ gibt es in der Abschwächung nicht. Der Zusatzblock für
Licht 5–8 benutzt dieselbe Formel mit `c248`–`c250`, die „Mehr Lichter“ aus denselben Feldern
`+0x54..+0x5C` füllt.

### 2.5 Wo greifen die beiden Patches des Patchers?

| Patch | Stelle | ändert | ändert nicht |
|---|---|---|---|
| „Mehr Lichter“ | `AddLight 0x834FC7/0x834FCD`, `0x83510E`, `0x873E85`, `0x7A91A9`, `0x7D0292` u. a. | Stufe 3: 8 statt 4 Plätze, `c236`–`c250` | Fenster, Animate-Kopplung, Abschwächung |
| „Lichter bleiben an“ | `0x81E548` (`je` → `jmp`) | Stufe 1 in `QueryLights`: veraltete Lichter bleiben an | Fenster, 4er/8er-Auswahl, Abschwächung, Animate-Liste selbst |

Keiner der beiden Patches berührt `0x828A00`, `0x821A20`, `0x823F10`, `0x7987A0`, `0x791CB0`
oder den Lichtkonstruktor.

### 2.6 Patch-Notizen für den Patcher (nur Notizen, nichts davon ist eingebaut oder getestet)

Alles Folgende sind Stellen, die sich aus der Lesung ergeben; keine ist in einer Exe
ausprobiert. Adressen: VA und (Dateioffset). Die Exe-Änderungen macht der Patcher-Agent mit
Sascha; dieses Repo liefert nur die Notiz.

**A. Gitterfenster vergrößern (kleinste Änderung, 4 × 4 Byte).** In `QueryLights` zeigen vier
Adressoperanden auf die Konstante 0,5 bei `0x9E2EC4` (Bytes `C4 2E 9E 00`):
`0x81E440` (Datei `0x41D842`, x_max), `0x81E47B` (`0x41D87D`, y_min), `0x81E4B6` (`0x41D8B8`,
y_max), `0x81E4F1` (`0x41D8F3`, x_min). Alle vier auf eine andere vorhandene
`.rdata`-Float-Konstante b umbiegen:

| b | Adresse | neue Operandenbytes | Fenster bei r = 0 | je Achse sicher / höchstens |
|---|---|---|---|---|
| 1,5 | `0x9E3084` (0 Verweise) | `84 30 9E 00` | 4×4 Zellen | ±30 / < ±50 Yards |
| 2,5 | `0x9EDCE8` (10 lesende Verweise) | `E8 DC 9E 00` | 6×6 Zellen | ±50 / < ±70 Yards |
| 3,0 | `0x9E3078` | `78 30 9E 00` | 7×7 Zellen | ±60 / < ±80 Yards |

`0x9E2EC4` selbst darf **nicht** geändert werden (~560 Verweise, darunter die Chunk-Kugel
`0x7B7B89`). Kosten: besuchte Zellen wachsen quadratisch, je Licht in einer Zelle ein
`AddLight` mit Sortierung; das Fenster muss unter 64 Zellen je Achse bleiben (`r + 20·b` <
≈ 620 Yards). Durch den Umlauf (1280 Yards) kommen Lichter im Abstand k·1280 als Kandidaten
dazu, die der 3D-Abstand aber aussortiert, solange nähere Lichter da sind.

**B. Alternative: Zellgröße verdoppeln.** Beide Skalen 0,05 (`CD CC 4C 3D`) gemeinsam auf
0,025 (`CD CC CC 3C`) setzen: `0xAF58A0` (Datei `0x6F38A0`, nur `QueryLights`) und `0xAF59D4`
(Datei `0x6F39D4`, nur `0x834C70`). Dann 40-Yard-Zellen, Umlauf 2560 Yards, Fenster bei r = 0
80×80 Yards (±20 sicher, < ±60). Beide Werte müssen gleich sein, sonst passen Einfüge- und
Suchzelle nicht zusammen; nur als Dateipatch, nicht zur Laufzeit umschalten.

**C. Animationsradius für nicht gezeichnete Kartendoodads (10 Yards) erhöhen.** Die drei
`fcomp`-Operanden auf `[0x9E8CC8]` (100,0 = 10²; 43 Nutzer, nicht direkt patchbar) auf eine
größere vorhandene Konstante umlenken, z. B. `[0xADF3B4]` (= (30 Yards × `environmentDetail`)²,
Zeichendistanz der Größenklasse 0): VA `0x7988FE` / `0x799A7B` / `0x799C1A` (Datei
`0x397CFE` / `0x398E7B` / `0x39901A`), je 4 Byte `C8 8C 9E 00` → `B4 F3 AD 00` (Befehl bleibt
`D8 1D imm32`). Nebenwirkung: mehr Modelle werden je Bild animiert (CPU). Radikaler: alle
nicht sichtbaren Doodads animieren: `0x798907` (`0x397D07`) `7B 14` → `EB 14`, `0x799A84`
(`0x398E84`) `7B 1C` → `EB 1C`, `0x799C23` (`0x399023`) `7B 04` → `EB 04` (`jnp` → `jmp` zur
Einhängeseite); Doodads jenseits der Zeichendistanz bleiben auch dann unberührt.

**D. Ohne Exe-Patch.** `/console environmentDetail 1.5` hebt die Zeichen- und damit
Animationsdistanz aller Größenklassen um 50 % (Klemmung 0,5..1,5 in `0x78DC60`); „Lichter
bleiben an“ verhindert das Abschalten, löst aber das Einfrieren der Spuren nicht.

**E. Abschwächung flacher machen (betrifft alle M2-Punktlichter, auch Zauber).** Operanden im
Konstruktor: `0x834A83` (Datei `0x433E83`, zeigt auf 0,7 bei `0x9E2EC0`, 17 Nutzer) und
`0x834A96` (Datei `0x433E96`, zeigt auf 0,03 bei `0x9F23C8`, 4 Nutzer) auf andere
`.rdata`-Konstanten umlenken; `0x9E2EC0`/`0x9F23C8` selbst nicht ändern. Kleinere a1/a2
machen Lichter in 20–30 Yards deutlich sichtbarer, aber auch alle Lichter in der Nähe heller
(Überstrahlen, besonders mit 8 Lichtern). Alternativ nur im Shader-Ordner: der Zusatzblock könnte
eigene Abschwächungswerte für Licht 5–8 benutzen (`def c247` ist frei dafür). Das wäre eine
Shader-Änderung in diesem Repo und bräuchte einen neuen Spieltest.

**Reihenfolge, wenn man es ausprobieren will:** erst A mit b = 1,5 (vier Bytes, nur Fenster),
dazu „Lichter bleiben an“ und `environmentDetail 1.5`; erst dann C, erst dann E.

## 3 Offen und Rückfragen an den coa-vfog-Agenten

Nicht von hier prüfbar oder nicht gelesen:

- CoA/Ascension-Client: welche Archive er mitbringt und ob darin `Shaders\Vertex` liegt
  (Abschnitt 1.1, Prüfweg dort).
- Ob die Exe aus dem Patcher, mit der Stormhand testet, noch den Original-`.text` an den oben
  genannten Stellen hat (alle Adressen gelten für 12340 unverändert außer den genannten
  Patches).
- Die Aufrufer von `0x823F10` außerhalb der Kartendoodads (2.3).
- Die DXVK-Angaben in 1.4 stammen aus der Erinnerung an den Quelltext, nicht aus einer neuen
  Lesung.

Rückfragen, deren Antwort die Analyse weiterbringt:

1. **Woran erkennt coa-vfog den Flüssigkeitsdurchgang und das Ende der Welt?** Am gebundenen
   Vertex-/Pixel-Shader (Handle aus `CreateVertexShader`, Hash oder Länge des Bytecodes,
   gelesene Konstanten), an Texturen, an Render-States oder an Draw-Call-Zählern? Nach dem
   Liquid-Pass bindet der Client die Modell-Shader (`Diffuse_*`) für die M2-Pässe 1 und 2
   (Abschnitt 1.2). Die 34 neuen Fassungen unterscheiden sich vom Original durch längeren Bytecode,
   `def c247`/`def c251`, Lesezugriffe auf `c236`–`c251` und das verschobene `_sat`. Ein
   Fingerabdruck, der auf Länge oder Hash geht, erkennt sie nicht mehr; ein Hook, der „Ende des
   Liquid-Passes“ am Wechsel zu einem bekannten Shader erkennt, würde dann anders feuern.
2. **Welche „M2-Punktlichttabelle“ liest coa-vfog?** Das Gitter `[[0xCD754C]+0x24]`
   (4096 Zellköpfe, Kette über `+0x68`), die Liste `[Szene+0x20]`, eine `CM2Lighting`
   (`+0x84..`, höchstens 4 bzw. 8 Lichter eines Objekts) oder die Shader-Konstanten
   `c17`–`c27`/`c236`–`c250` (das sind die Lichter des zuletzt gezeichneten Objekts)? Je nach
   Quelle gilt eine andere Stufe aus Abschnitt 2 als Grenze: Gitter → nur Stufe 1,
   `CM2Lighting`/Konstanten → Stufen 1–3.
3. **Ergebnis der Test-Builds** aus 1.5 mit Exe, Auflösung, DXVK ja/nein und dem Test mit
   `/console fixedFunction 1`.
4. **Zeigt der Ladetest Magenta?** Sonst wird der Ordner im CoA-Client nicht geladen.
5. Falls coa-vfog selbst Vertex-Shader-Konstanten ab `c236` setzt oder liest: welche? Der Ordner
   belegt `c236`–`c251` (Modelle/Gebäude bis `c247`, Boden bis `c251`), und die Exe mit „Mehr
   Lichter“ schreibt sie nur, wenn der Shader ≥ 251 Konstanten meldet.

## Anhang: Adressen (Wow.exe 3.3.5a 12340, VA; Datei = VA − 0x400C00 im .text)

| Was | VA |
|---|---|
| Szene/Lichtmanager | `[0xCD754C]`; `+0x14` Bild-Nr., `+0x20` Liste Nicht-Punktlichter, `+0x24` Gitter 64×64, `+0x28` Animate-Liste |
| Kameraposition | `[0xCD8F5C..0xCD8F64]` (Schreiber `0x7954AB`) |
| QueryLights | `0x81E400`; Fenster `0x81E431–0x81E4F9`; Zeitstempeltest `0x81E545/0x81E548`; SetEnabled(0) `0x81E54A` |
| Gitter einfügen | `0x834C70` (Skala `[0xAF59D4]`); Fensterskala `[0xAF58A0]`; Bias `[0x9E2EC4]` = 0,5 |
| AddLight / GetLight | `0x834F60` / `0x8349E0`; 4er-Grenze `0x835026 cmp [ecx+0xA4],4` |
| CM2Lighting Initialize / Reset | `0x834900` / `0x790440`; Modell-Lighting `Modell+0x1D4`, Radius 0 bei `0x831B25` |
| Lichtkonstruktor | `0x834A40`; a1 `0x834A81` (`[0x9E2EC0]` = 0,7), a2 `0x834A94` (`[0x9F23C8]` = 0,03) |
| SetPosition / SetEnabled / SetDirection / SetScene | `0x835690` / `0x8356F0` / `0x834AE0` / `0x8348D0` |
| Modell-Lichtaktualisierung | `0x828A00` (Zeitstempel `0x828B9C`); Szene-Animate `0x821A20`; Einhängen `0x823F10` |
| Lichtspuren (Farbe, Sichtbarkeit) | `CM2Model::Animate 0x82F0F0`, Schleife `0x830401–0x830624` |
| Kartendoodads je Chunk | `0x7987A0` (`0x7988CB` Flag 0x400, `0x7988FC` 10-Yard-Test), `0x799A4A` ff., `0x799BDA` ff.; Zeichendistanz `0x791CB0`, Tabellen `0xADF364`/`0xADF3B4`/`0xADF350`; CVar `environmentDetail` `0x78DC60` |
| Sichtkegel / Horizont | `0x983D20` / `0x7CCE00`, `0x78FC40` |
| Shader-Konstanten | `0x872900` (c17–c27; Aufrufer `0x873E85` M2, `0x7A91A9` WMO); Boden `0x7D0050`/`0x7D00E0` (c28–c36) |
| Boden-Chunk-Kugel | `0x7B7AF0` (`chunk+0x24` Mitte, `+0x30` Radius); Lighting `0x7D0072–0x7D00A2` |
| WMO-Instanz | `0x7964A0`: Lighting `0x79670B–0x796727`, Innenlichter `0x7B3F30`/`0x7C3DB0` (Tiefe `+0x4C` < `[0xCD7668]`), Gruppen `0x7ABF50` |
| Flüssigkeits-Shader-Namen | `0xA59534` vsLiquidWater, `0xA59564` NoSpec, `0xA59504` ProcWater, `0xA59594` Magma |
| MPQ-Namen | `0x9E26A0` ff. (`patch-%s.MPQ`, `patch-2/3/4.MPQ`, `patch-?.MPQ`) |
| Patcher | „Mehr Lichter“ Nr. 69 (`lights`), „Lichter bleiben an“ Nr. 70 (`lightstay`, Datei `0x41D948`), `apply_patches.ps1` auf `st0ny-dev` |


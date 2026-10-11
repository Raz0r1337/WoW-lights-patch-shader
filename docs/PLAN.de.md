# Plan: Vertex-Shader für 8 Punktlichter (WoW 3.3.5a, 12340, mit DXVK)

Stand: 2026-10-11. Grundlage: `Uebergabe_Lichter_Shader.md`, Zweig
`st0ny-dev-lights` (`d83df5c`) im Patcher-Repo, Upstream-Stand des DXVK-Forks
(`c7d8aa1`). Nichts committet, nichts gepusht.

## 1. Kurzfassung

- Die Exe-Seite (Nr. 66) ist fertig und liefert Licht 5–8 nach VS `c236–c246`.
  Es fehlt nur Shader-Code, der diese Register liest.
- Geändert werden nur die **4-Lichter-Varianten** (9, 19, …, 89) der
  Modell-Shader `Diffuse_*.bls`, in **vs_3_0 und vs_2_0**. Danach die
  Gebäude-Shader.
- **DXVK braucht keine Änderung.** Es meldet 256 VS-Konstanten, lädt
  `c236–c246` korrekt in den Shader und hat keine Befehlsgrenze, die stört
  (Belege in Abschnitt 4).
- Lieferweg: ein eigenes Werkzeug, das beim User aus seinen Original-`.bls`
  die neuen Dateien baut. Der Zusatzcode ist unser eigener Bytecode-Baustein,
  es landen keine Blizzard-Daten im Repo.
- **Eigenes Arbeitsrepo** (Wunsch von Sascha, 2026-10-11): Werkzeug, Tests und
  Doku kommen in ein neues Repo, **nicht** ins Patcher-Repo. Vorgeschlagener
  Name `WoW-Lichter-Shader`, privat.
- **Ausgabeformat** (Wunsch von Sascha): ein Ordner, der wie ein MPQ heißt und
  innen wie ein MPQ aufgebaut ist, z. B.
  `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls`.
- **Blocker für die eigentliche Arbeit:** die Original-Shader-Dateien des Users
  (`Shaders\Vertex\vs_2_0\`, `vs_3_0\`, besser alle Profile und `Pixel\`).
  Ohne sie lassen sich Formel, Register und Platzreserve nicht bestimmen.

## 2. Was am Shader-Code zu tun ist

Licht 1–4 sind im Original vektorisiert: Farben in c17–c20, Positionen in
c21–c24, die drei Abschwächungsparameter für alle 4 Lichter je in einem
Register (c25–c27, x/y/z/w = Licht 1–4). Der Zusatzblock für Licht 5–8 ist
dieselbe Rechnung mit c236–c246:

```
// Platzhalter-Register, echte Namen ergeben sich aus der Disassembly
// P = Vertexposition (Kamerasicht), N = Normale (Kamerasicht), ACC = Lichtsumme
for i in 0..3:
    L_i   = c(240+i).xyz - P            // sub
    d2[i] = dot(L_i, L_i)               // dp3
    inv   = rsq(d2[i])                  // rsq
    d[i]  = d2[i] * inv                 // Abstand
    ndl[i]= max(dot(N, L_i) * inv, 0)   // dp3, mul, max
att = f(c244, c245, c246, d, d2)        // Formel genau wie für c25–c27 im Original
w   = ndl * att                         // mul (vec4)
ACC += c236.rgb*w.x + c237.rgb*w.y + c238.rgb*w.z + c239.rgb*w.w   // 4× mad
```

- Grob 30–35 Befehle je Variante. Das passt in vs_3_0 (≥ 512 Slots)
  sicher und in vs_2_0 (256 Slots), wenn das Original nicht schon nahe an
  der Grenze ist (prüfen).
- **Einfügepunkt:** dort, wo das Original Licht 1–4 in die Lichtsumme
  addiert, und **vor** einer eventuellen Sättigung (`min`/`sat`) und vor dem
  Zusammenfassen mit Umgebungs- und Sonnenlicht. Sonst sättigt das
  Original zu früh oder Licht 5–8 landet am falschen Ort.
- **Temp-Register:** vs_2_0 hat nur 12 (`r0–r11`). Der Block braucht 3–4
  freie Temps zur Einfügestelle. Lebensdauer im Original auswerten, sonst
  Register wiederverwenden, die dort schon tot sind.
- Licht 1–4 bleiben Befehl für Befehl unverändert. Der Block wird nur
  eingefügt, nie umsortiert.

### Abschwächungsformel

Ist noch offen und wird aus der Disassembly abgelesen. Zwei Kandidaten:
`1 / (a0 + a1·d + a2·d²)` (D3D-Stil, dazu passt der Startwert 1.0 für c244,
den die Exe setzt) oder ein linearer Abfall zwischen Start- und Endradius.
Der Zusatzblock übernimmt genau die Formel des Originals.

## 3. Ablauf

1. **Eingaben vom User holen:** Original-`.bls` aller Profile (höchstes
   Patch-MPQ zählt) in den Projektordner `uploads/`.
2. **BLS-Leser/-Schreiber** (Python, Prüfskript): Kopf `HSXG`, Version
   `0x10003`, Variantenblöcke. Rundlauf über alle Dateien muss bitgleich
   sein. Aufbau je Variante (Bytecode-Länge, Konstanten-Infos) am Ladecode
   bei VA `0x684A2B` und an den Dateien klären.
3. **Analyse:** alle Varianten disassemblieren (Wine-`d3dx9`, gegenprüfen mit
   `vkd3d-compiler`). Ergebnisse:
   - Formel und Einfügepunkt in den Varianten 9, 19, …, 89;
   - Befehlszahl und Temp-Belegung je Variante;
   - Variantenschema bestätigen (Index mod 10 = 9 heißt 4 Lichter);
   - höchstes Konstantenregister aller Originale, auch über `a0`
     (Knochenpalette), muss unter c236 bleiben;
   - die `.bls`-Namen der Gebäude-Shader (Upload bei VA `0x7A91A9`).
4. **Zusatzblock als eigener Token-Baustein:** einmal assemblieren, dann im
   Werkzeug nur Register einsetzen (Temp-Nummern, Lichtsumme, P, N). So
   braucht der User keinen D3DX-Assembler.
5. **Testen unter Wine D3D9 und unter DXVK** (Testprogramm, mingw-Build):
   - neuer Shader mit Licht 5–8 = 0 muss pixelgleich zum Original sein;
   - mit Testlichtern muss das Ergebnis zur CPU-Referenz passen;
   - unter DXVK zusätzlich mit `d3d9.floatEmulation = False`, damit kein
     NaN-Fall versteckt bleibt (Abschnitt 4).
6. **Werkzeug ausliefern:** Skript, das beim User aus seinen Dateien die
   neuen `.bls` erzeugt (vs_3_0 und vs_2_0) und sie in einen Ordner
   `patch-5.MPQ\` mit MPQ-Innenaufbau legt (siehe Abschnitt 3a).
7. **Doku** im neuen Arbeitsrepo (README, DE und EN gleich). Im Patcher-Repo
   bei Nr. 66 höchstens später ein Verweis, nur nach Freigabe.

### 3a. Ordner statt MPQ: was zu klären ist

- **Noch nicht belegt:** ob der Client 3.3.5a einen *Ordner* namens
  `patch-5.MPQ` wie ein Archiv lädt. Das prüfe ich am Lade-Code der Exe
  (Archivliste, Öffnen per Storm). Bis dahin ist es eine Annahme.
- Der Ordner ist in jedem Fall nützlich:
  - Ladik's MPQ Editor packt ihn 1:1 zu einem echten `patch-5.MPQ`
    (Ordner hinzufügen, Pfade bleiben gleich).
  - Der Inhalt des Ordners (`Shaders\…`) funktioniert direkt im
    `Data`-Ordner mit Nr. 22, wenn Nr. 22 auch den Shader-Ladeweg
    (`0x424B50`) abdeckt.
- Lädt der Client den Ordner nicht von sich aus, sind die Wege: (a) echtes
  MPQ daraus packen, (b) Nr. 22, (c) ein kleiner eigener Exe-Patch, der
  Ordner mit MPQ-Namen als Archiv behandelt. (c) wäre Arbeit im Patcher-Repo
  und nur nach Freigabe.
8. **Spieltest** durch den User: `fixedFunction 0`, Nr. 66 + 67 an, Ort mit
   vielen Fackeln (Sturmwind, Dalaran). Zum Gegencheck vorher einmal
   `fixedFunction 1`: dort muss die Exe-Seite schon 8 Lichter zeigen.

Reihenfolge der Familien: erst Modelle (`Diffuse_*`), dann Gebäude. Boden und
Wasser bleiben außen vor (eigener Datenweg, spätere Stufe), `arbvp1` ebenso.

## 4. DXVK: was geprüft wurde

Fork `Raz0r1337/dxvk`, Stand `c7d8aa1` (reiner Upstream-Merge).

- **256 VS-Konstanten:** `caps::MaxFloatConstantsVS = 256`
  (`src/d3d9/d3d9_caps.h:14`), gemeldet in `d3d9_adapter.cpp:702`. Die
  Prüfung der Exe (`[Gx+0x2E0] >= 0xF7`) greift also, c236–c246 werden
  hochgeladen.
- **Die Register kommen im Shader an:** DXVK lädt nur Konstanten, die der
  Shader liest. Die Shader-Analyse sammelt statisch gelesene Register in
  einer Maske (`d3d9_shader_analysis.cpp:129–143`). Ein neuer Shader, der
  c236–c246 liest, bekommt sie also. Bei Shadern mit `a0`-Zugriff
  (Knochen) lädt DXVK zusätzlich bis zum höchsten je gesetzten Register
  (`changedFloatCount`, `d3d9_device.cpp:8282`), auch das deckt c246 ab.
- **Keine störenden Grenzen:** `MaxVertexShader30InstructionSlots = 32768`,
  DXVK prüft die Befehlszahl nicht. Die harte Grenze für vs_2_0 (256) gilt
  trotzdem, weil echte D3D9-Treiber und Wine sie prüfen. Wir halten sie ein.
- **Float-Verhalten:** `d3d9.floatEmulation` steht per Voreinstellung auf
  `Auto` und schaltet damit die D3D9-Regel `0 · ∞ = 0` ein
  (`d3d9_options.cpp:90–104`). Darauf verlassen wir uns nicht, siehe
  Risiko R3.
- **WoW-Profil:** DXVK hat für `Wow.exe` nur `dxvk.hideIntegratedGraphics`
  (`src/util/config/config.cpp:44–48`), nichts, was Konstanten oder
  Shader betrifft.
- **Hilfreich zum Testen:** `DXVK_SHADER_DUMP_PATH` speichert jeden
  geladenen Shader. Damit lässt sich im Spiel nachweisen, dass die neuen
  `.bls` wirklich geladen werden und c236–c246 lesen.
- `d3d9.shaderModel = 2` in der `dxvk.conf` lässt WoW `vs_2_0` laden.
  Deshalb beide Profile liefern, und darüber lässt sich vs_2_0 auch gezielt
  im Spiel testen.

### Alternative: Einbau in DXVK statt in die `.bls`

DXVK könnte beim `CreateVertexShader` die 4-Lichter-Varianten erkennen und den
Block selbst anhängen. Vorteil: keine Shader-Dateien, kein MPQ. Nachteile:
wirkt nur mit DXVK (nicht mit nativem D3D9 oder wined3d), Bytecode-Umbau im
Treiber, und jeder Upstream-Merge kann ihn brechen. **Empfehlung: nicht so,**
sondern Werkzeug für die `.bls`. DXVK bleibt unverändert und dient nur zum
Testen.

## 5. Risiken

| Nr. | Risiko | Folge | Gegenmaßnahme |
|---|---|---|---|
| R1 | vs_2_0-Variante ist schon nah an 256 Befehlen oder 12 Temps | Shader lässt sich nicht laden, Modell unsichtbar oder Absturz | In Schritt 3 messen. Notfalls Block kürzen (z. B. `ndl` ohne `max`, Abstand aus `d2` statt eigenem `rsq`) oder vs_2_0 bei 4 Lichtern lassen |
| R2 | Knochenpalette über `a0` reicht bis c236 | Lichtwerte überschreiben Knochen oder umgekehrt, verzerrte Modelle | In Schritt 3 die höchste `a0`-Adresse aller Originale bestimmen. Liegt die Palette bei c31 + 3 × Knochen, reicht sie bei 68 Knochen bis c234 – knapp, also unbedingt prüfen |
| R3 | Freie Plätze (Farbe 0) erzeugen NaN, z. B. `rcp(0)` bei Abstand 0 oder Abschwächung 0 | Schwarze oder blinkende Modelle, vor allem mit `floatEmulation = False` oder nativem D3D9 | Nenner im Shader nach unten begrenzen (`max(x, ε)`), Test mit `floatEmulation = False`. Prüfen, ob die Original-Packroutine (VA `0x872900`) bei freien Plätzen die Abschwächung zurücksetzt; die Exe setzt c244 nur einmal anfangs auf 1.0 |
| R4 | Falscher Einfügepunkt (nach einer Sättigung) | Licht 5–8 wirkt zu schwach oder Licht 1–4 ändert sich | Pixelgleichheit mit Licht 5–8 = 0, CPU-Referenz mit Testlichtern |
| R5 | Variantenschema anders als angenommen (9, 19, …, 89) | Falsche Varianten geändert | Aus der Disassembly bestätigen: genau diese lesen c17–c27 vollständig |
| R6 | Andere Shader oder andere Exe-Stellen nutzen c236–c246 | Störungen in anderen Effekten | Alle Original-`.bls` auf Lesezugriffe ≥ c236 durchsuchen, Exe auf `SetVertexShaderConstantF` mit Start ≥ 236 prüfen |
| R7 | Client lädt den Ordner `patch-5.MPQ` nicht als Archiv, oder Nr. 22 greift nicht für `0x424B50` | Neue Shader werden nicht geladen, keine Wirkung | Lade-Code der Exe prüfen, im Spiel mit `DXVK_SHADER_DUMP_PATH` nachweisen. Rückfall: Ordner zu echtem MPQ packen |
| R8 | Spiel lädt weiter das Original aus `vs_3_0`, weil nur `vs_2_0` geliefert wurde | Keine Wirkung auf SM3-Karten | Immer beide Profile liefern |
| R9 | Mehr Shader-Arbeit je Vertex | Etwas weniger FPS bei vielen Modellen | Gering, nur 4-Lichter-Varianten betroffen. Im Spieltest beobachten |
| R10 | Licht pro Vertex | Bei großen, grob vernetzten Flächen wirkt Licht 5–8 fleckig | Wie im Original, kein Fehler. In der Doku erwähnen |
| R11 | Lizenz | Blizzard-Daten im Repo | Nur Werkzeug und eigener Token-Baustein ins Repo, Ergebnisdateien entstehen beim User |

## 6. Offene Fragen an Sascha

1. Bitte die Original-Shader-Dateien hochladen (mindestens
   `Shaders\Vertex\vs_2_0\` und `vs_3_0\`). Das ist der nächste Schritt.
2. ~~Lieferform~~ entschieden: Ordner mit MPQ-Namen und MPQ-Aufbau.
3. Erst nur Modelle, Gebäude danach? Vorschlag: ja.
4. ~~Zweig~~ entschieden: neues Arbeitsrepo, nichts ins Patcher-Repo.
   Gepusht wird nur nach deiner Freigabe.

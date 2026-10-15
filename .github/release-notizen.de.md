# Shader für 8 Punktlichter {version}

Vertex-Shader für WoW 3.3.5a (12340), mit denen Patch **Nr. 69 „Mehr Lichter: 8 statt
4 Punktlichter“** aus St0nys AIO WoW EXE Patcher sichtbar wird: Modelle, Gebäude und
Boden werden von bis zu 8 Lichtern beleuchtet statt von 4 (Boden: 3).

## Einsetzen

1. `patch-5.MPQ.zip` in den `Data`-Ordner des Spiels entpacken, sodass es
   `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` gibt. Der Ordner wird wie
   ein MPQ geladen; mit Patch Nr. 21 („Erweiterte MPQ-Namen“) geht auch z. B. `patch-Z.mpq`.
2. `Wow.exe` mit Nr. 69 patchen (Stand des Patchers ab 2026-10-12, mit Boden-Teil).
   `WTF\Config.wtf`: `SET gxApi "d3d9"`, `fixedFunction` nicht `1`.

Ohne Nr. 69 in der Exe sehen die Shader bitgleich aus wie das Original mit 4 Lichtern.
Einzelheiten, Spieltests und Fehlersuche: [README](https://github.com/{repo}/blob/{commit}/README.md).

## Dateien

| Datei | Wofür | Inhalt |
|---|---|---|
| `patch-5.MPQ.zip` | **Normalfall**: Modelle, Gebäude und Boden mit 8 Lichtern | {n_standard} Dateien |
| `patch-5.MPQ_ohne_Boden.zip` | nur Modelle und Gebäude, Boden bleibt original; für eine Exe, deren Nr. 69 den Boden-Teil noch nicht hat (Patcher vor 2026-10-12) | {n_ohne_boden} Dateien |
| `patch-5.MPQ_Testfassung_Magenta.zip` | Testfassung: Licht 5–8 leuchten magenta, um zu sehen, ob alles greift (siehe README, „Im Spiel testen“) | {n_testfassung} Dateien |
| `SHA256SUMS.txt` | Prüfsummen der drei Zips | |

Gebaut am {datum} aus Commit `{commit_kurz}` mit `tools/release.py`: Emulator-Tests bestanden,
Ausgabe bitgleich mit der im Spiel bestätigten Fassung (Prüfsummen in `tests/pruefsummen/`).
Das Zip enthält nur die aus den eigenen Original-Shadern neu gebauten Dateien.

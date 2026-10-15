# Shaders for 8 point lights {version}

Vertex shaders for WoW 3.3.5a (build 12340) that make patch **No. 69 "More lights:
8 instead of 4 point lights"** from St0ny's AIO WoW EXE Patcher visible: models,
buildings and terrain are lit by up to 8 lights instead of 4 (terrain: 3).

## How to use

1. Extract `patch-5.MPQ.zip` into the game's `Data` folder so that
   `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` exists. The folder is loaded
   like an MPQ; with patch No. 21 ("Allow extended MPQ names") a name such as `patch-Z.mpq`
   works as well.
2. Patch `Wow.exe` with No. 69 (patcher as of 2026-10-12 or later, which includes the
   terrain part). In `WTF\Config.wtf`: `SET gxApi "d3d9"`, and `fixedFunction` must not be `1`.

Without No. 69 in the exe the shaders render bit-identically to the original with 4 lights.
Details, in-game tests and troubleshooting: [README](https://github.com/{repo}#readme).

## Files

| File | Purpose | Contents |
|---|---|---|
| `patch-5.MPQ.zip` | **Default**: models, buildings and terrain with 8 lights | {n_standard} files |
| `patch-5.MPQ_without_terrain.zip` | models and buildings only, terrain stays original; for an exe whose No. 69 does not have the terrain part yet (patcher before 2026-10-12) | {n_without_terrain} files |
| `patch-5.MPQ_test_build_magenta.zip` | test build: lights 5–8 glow magenta to show that everything is in effect (see the README) | {n_test_build} files |
| `SHA256SUMS.txt` | checksums of the three zips | |

Built on {datum} from commit `{commit_kurz}` with `tools/release.py`: emulator tests passed,
output bit-identical to the version confirmed in game (checksums in `tests/pruefsummen/`).
The zips contain only the files rebuilt from the player's own original shaders.

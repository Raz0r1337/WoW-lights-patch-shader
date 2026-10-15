# WoW-lights-patch-shader

Deutsche Fassung: [README.de.md](README.de.md)

Tool for WoW 3.3.5a (12340): builds, from your own original shaders, vertex shaders that
render up to **8 point lights**. Counterpart to patch **No. 69 "More lights: 8 instead of
4 point lights"** from St0ny's AIO WoW EXE Patcher (No. 66 until 2026-10-11). Without new
shaders the exe does pass lights 5–8 to the graphics, but they never become visible.

The repo contains **no Blizzard files**. The new shaders are created on the player's side
from their own files.

## Download the finished package

If you do not want to build it yourself, take the finished zip from the
[Releases page](https://github.com/Raz0r1337/WoW-lights-patch-shader/releases):

| File | What for |
|---|---|
| `patch-5.MPQ.zip` | **Normal case**: models, buildings and terrain with 8 lights |
| `patch-5.MPQ_without_terrain.zip` | models and buildings only; for an exe whose No. 69 does not yet have the terrain part (patcher before 2026-10-12) |
| `patch-5.MPQ_test_build_magenta.zip` | test build, lights 5–8 glow magenta (see "Testing in the game") |
| `SHA256SUMS.txt` | checksums of the three zips |

Unpack the zip into the game's `Data` folder so that
`Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` exists. It contains only the
newly built files (34 or 32 `.bls`), laid out like an MPQ, see "Folder instead of MPQ".
Every release is built from the original shaders by a run on GitHub, which first checks
that the result is bit-identical to the version confirmed in the game (section
"Release run").

## Requirements

- `Wow.exe` 3.3.5a with No. 69; for testing, ideally also No. 70 ("Lights stay on when
  their source is off-screen"). Since 2026-10-15 both are in the patcher's `st0ny-dev`
  branch (still [BETA], not yet in `st0ny-main`).
- Python 3 (standard library only). The tests additionally need `numpy`.

## Usage

1. With Ladik's MPQ Editor, export the `Shaders\` folder from every MPQ that has one,
   each MPQ into its own subfolder named after the MPQ (here under `Quelle`, "source"):

   ```
   Quelle\
     common-2.MPQ\Shaders\...
     patch.MPQ\Shaders\...
     patch-2.MPQ\Shaders\...
     patch-3.MPQ\Shaders\...
   ```

   Which file wins is decided by the tool the same way the game does it: `patch-3` before
   `patch-2` before `patch` before the base MPQs.

2. Build the shaders; the target is the game's `Data` folder:

   ```
   python tools/build.py Quelle "C:\WoW\Data"
   ```

   Result: `Data\patch-5.MPQ\Shaders\Vertex\vs_2_0\*.bls` and `...\vs_3_0\*.bls`,
   a **folder** with the name and layout of an MPQ. A different name can be chosen
   with `--name`.

3. Test in the game, see the next section.

## Testing in the game

### Preparation

- Patch `Wow.exe` with No. 69 and No. 70.
- `WTF\Config.wtf` must contain `SET gxApi "d3d9"` (with DXVK it does anyway) and
  `fixedFunction` must not be `1` (`/console fixedFunction 0`, then restart).
  Under OpenGL (`gxApi "opengl"`) the game uses different shaders, and nothing takes effect.
- Place the folder so that `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls`
  exists (not doubled as `patch-5.MPQ\patch-5.MPQ`). The folder name is up to you as
  long as the client recognizes it as a patch archive, e.g. `patch-Z.mpq`.

### Step 1: test build (magenta)

In a `--debug` build, lights 5–8 do not glow in their own color but **magenta**.
Lights 1–4 look normal. That way you can see right away whether everything is working.

```
python tools/build.py --debug Quelle "C:\WoW\Data"
```

Go to a place where many light sources are close together (torches, lanterns,
braziers), e.g. Stormwind, Ironforge at the Great Forge, or Dalaran, ideally at night
or indoors. Then point the camera at your own character and at nearby buildings and
walk around slowly.

| What you see | Meaning |
|---|---|
| Character, NPCs or buildings get magenta patches of light that move as you walk | Everything works: the folder is loaded, the exe delivers lights 5–8, the shaders compute them |
| Everything looks as usual | Either there are no more than 4 lights nearby (try another place), or the folder is not loaded (then pack the folder into a real `patch-5.MPQ` with Ladik's MPQ Editor and try again) |
| Models are missing, black, flickering, or the game crashes | Error in the shaders, please report with a screenshot |

The terrain shows no magenta even in the test build: its extension to 8 lights
(default since 2026-10-14) has no test color; it always computes with the real light
colors. Close to several fires the magenta on models oversaturates and swallows the
orange; that is intended in the test build (full intensity 1.0 instead of the real
light color).

As of 2026-10-11: test build confirmed in the game (campfires in the Barrens, magenta
from the 5th fire on; with `fixedFunction 1` 8 light sources visible).

### If no magenta is visible

Then either the exe side is not active or the new shaders are not being loaded. Two
tests tell these apart:

**Check the exe side without shaders.** Enter `/console fixedFunction 1` in the game and
restart it. In this mode the game works without shaders, and No. 69 gives the graphics
device 8 light slots instead of 4. Then, in a dark place, put campfires around your
character one after another (Cooking, "Basic Campfire"):

| What you see | Meaning |
|---|---|
| From the 4th fire on, one goes out again (at most 3 fires lit at the same time) | No. 69 is not active (original: 4 slots, one of them for the sun) |
| Up to 7 fires light the character at the same time | No. 69 is working, the exe delivers the lights |

Afterwards `/console fixedFunction 0` again and restart.

**Check that the shaders are loaded.** Build with `--ladetest` (load test):

```
python tools/build.py --ladetest Quelle "C:\WoW\Data"
```

In that build, **all** point lights 1–8 glow magenta, including the first four. As soon
as at least 4 light sources are nearby (4 campfires), the character must be lit magenta,
no matter what the exe does.

| What you see | Meaning |
|---|---|
| Character magenta with 4 fires | The shaders are loaded. If the normal test build still shows no magenta from the 5th fire on, no lights 5–8 arrive from the exe |
| Character lit normally with 4 fires | The shaders are not loaded (see below) |

If the shaders are not loaded:

- Check the path: `Data\patch-5.MPQ\Shaders\Vertex\vs_3_0\Diffuse_T1.bls` must exist.
- `WTF\Config.wtf`: `SET gxApi "d3d9"`. Under OpenGL nothing takes effect.
- Pack the folder into a real archive with Ladik's MPQ Editor: create a new MPQ
  `Data\patch-5.MPQ` (rename or delete the folder first), add the `Shaders` folder so
  that the paths inside the archive read `Shaders\Vertex\vs_3_0\…`. The client then no
  longer has a folder but a normal patch MPQ.
- With DXVK you can check what is really loaded: set the environment variable
  `DXVK_SHADER_DUMP_PATH` to a folder, start the game; the new shaders read
  `c236`–`c247`, the originals do not.

### Step 2: the real build

Replace the test build with the normal one (build without `--debug`). For comparison,
take two screenshots at the same spot with the same camera: once with the folder, once
without (e.g. rename the folder to `_patch-5.MPQ` and restart the game). With the
folder, the character and buildings are lit by more light sources at the same time.
When walking past a row of torches, the light on the character pops on and off less
often, because the first light to be dropped is now the 9th instead of the 5th.

Result of the in-game test (2026-10-11, eight campfires in a circle, the Barrens): with
the folder, the stones of the campfires are lit a little brighter and more evenly,
because each fire now also receives light from the neighboring fires. The difference is
small, since a campfire only shines a few meters. Nothing is missing, nothing is black.
The difference is clearer with a character standing between more than four nearby light
sources, or with rows of torches in cities.

With the terrain (default since 2026-10-14, exe with No. 69 from 2026-10-12 on): in-game
test without errors, the terrain is lit by all eight fires instead of three per terrain
chunk.

### Folder instead of MPQ

The client opens a folder with an MPQ name like an archive. In the in-game test
(2026-10-11) the folder worked directly, without packing it, with an exe patched by
St0ny's AIO WoW EXE Patcher and the folder name `patch-Z.mpq` (letter suffix, see No. 21
"Allow extended MPQ names"). With `--name patch-Z.mpq` the tool builds the folder under
this name right away.

Background in the original exe: `SFileOpenArchive` (VA `0x45C480`) queries the file
type (`0x427170`); a folder (`FILE_ATTRIBUTE_DIRECTORY`, set at `0x435760`) gets type 2
and is opened via `0x453E30` as a directory archive. If an unmodified exe does not load
the folder, packing it into a real `patch-5.MPQ` with Ladik's MPQ Editor helps.

This can be checked under DXVK with `DXVK_SHADER_DUMP_PATH`: the new shaders read
`c236`–`c246`, the originals do not.

## What is changed

- Only the variants with 4 lights (No. 9, 19, …, 89 of each file) of the model shaders
  (`Diffuse_*`, `CDiffuse_T1`) and building shaders (`MapObj*`), in `vs_2_0` and `vs_3_0`.
  The game uses these variants from 4 lights on.
- Lights 1–4 stay unchanged instruction by instruction. After the last light addition,
  an extra block (32 instructions, plus 2 to save position and normal and one
  `def c247`) computes lights 5–8 with the same formula as the original:

  ```
  L = Lichtposition - P;  d2 = dot(L, L)
  ndl = max(dot(L, N) * rsq(d2), 0)
  att = 1 / (a0 + a1 * d2 * rsq(d2) + a2 * d2)
  Summe += Farbe * ndl * att
  ```

  (`Lichtposition` = light position, `Farbe` = color, `Summe` = sum) with the registers
  that No. 69 fills: `c236–c239` color, `c240–c243` position, `c244–c246` attenuation.
  The saturation of the sum moves to the end of the extra block. Before the reciprocal,
  the denominator of the attenuation is clamped with `max` to at least `c247.w` (= 1e-6,
  its own `def`), so that registers that are never set do not cause a division by 0 (see
  "Without the exe patch").
- Not changed: terrain and water (own shaders, own data path), `vs_1_1` (too few
  constants), OpenGL (`arbvp1`).
- Space: at most 139 instruction slots (vs_2_0 limit: 256) and temp registers up to
  `r10` (vs_2_0 limit: `r11`). No original shader reads `c236`–`c247`; the highest
  constant in use is `c235`.

### Without the exe patch

If the new shaders are present but the exe does not have patch No. 69, the exe never
writes to `c236`–`c246`; they then hold 0 (certain under DXVK, since the constant buffer
starts out at 0; under Windows D3D9 likewise according to the documentation). Color 0
means: lights 5–8 contribute nothing, so the shaders deliver the original with 4 lights
bit-identically. Without the `max` clamp the attenuation would be 1/0; 0 · infinity is
NaN under IEEE and 0 only under the D3D9 rule (DXVK follows that rule; other hardware
may not). With the clamp, the case is clean regardless. Checked:
`test_lights8.py` test 3 and `d3d9_check.py` (each variant additionally with
`c236`–`c250` = 0).

The other way round (exe with No. 69, original shaders): lights 1–4 are still written to
`c17`–`c27` by the unchanged original function, and AddLight keeps the same 4 nearest
lights as without the patch. The exe additionally uploads `c236`–`c246`, which the
original shaders do not read. So models, buildings and terrain look as in the original;
only `fixedFunction 1` shows 8 lights. No. 70 ("Lights stay on") is a separate patch,
off by default: lights stay active when their model is not in view. It works the same
with and without the new shaders and has nothing to do with the number of lights.

With a completely unpatched exe, the terrain shader is harmless for the same reason
(its own `def c251`). But if No. 69 is present and the exe part for the terrain is
missing (patcher state before 2026-10-12), `c236`–`c250` hold the model lights in a
different format: the terrain is lit incorrectly. So use the terrain only with an exe
whose No. 69 has the terrain part.

With No. 69 **including** the terrain part, all combinations are clean, because each
shader reads `c236` onwards only directly after its own upload (No. 69 uploads before
each model, the terrain part before each terrain chunk):

| Shaders in the folder | Models, buildings | Terrain |
|---|---|---|
| original | 4 lights (original) | 3 lights (original) |
| new, with `--ohne-boden` (without terrain) | 8 lights | 3 lights (original) |
| new (default) | 8 lights | 8 lights |

This is how it is implemented in the patcher (since 2026-10-12, now in the branch
`st0ny-dev`): the terrain part is a fixed part of No. 69, not selectable on its own. If
it existed without the model part, the new model shaders would read the terrain lights
in `c236`–`c246` in the wrong format. Since the in-game test of 2026-10-14, the terrain
is the default when building.

## Tests

```
python3 tests/test_lights8.py <Quelle>
python3 tests/test_lights8.py <Quelle>/patch.MPQ/Shaders/Vertex [...]
```

Given the same `Quelle` (source folder) as `build.py`, the test checks exactly the files
that take effect, which are the ones the build is made from (older versions from
`common-2` that a patch MPQ overrides are left out; they use instructions the emulator
does not know). Given individual `Vertex` folders, it checks all files in them.

Emulator test for each extended variant, with IEEE arithmetic and with the D3D9 rule
`0 · x = 0` (DXVK `d3d9.floatEmulation`), plus test 3 with `c236`–`c246` = 0 (exe
without patch, must be bit-identical):

- Lights 5–8 empty (color 0, position and attenuation arbitrary): all outputs
  bit-identical to the original.
- Lights 5–8 set: color = original with lights 1–4 + original with lights 5–8 in slots
  1–4 − original without lights.

```
x86_64-w64-mingw32-gcc -O2 -o runner.exe tests/d3d9/runner.c -ld3d9
WINE=wine python3 tests/d3d9_check.py <Data>/patch-5.MPQ runner.exe
```

Cross-check with a real D3D9 runtime under Wine: every variant must be creatable and,
when drawn, deliver the same color as the emulator.

## Files

- `tools/bls.py` – reading/writing `.bls` (round trip bit-identical across all files)
- `tools/sm3.py` – disassembler and token tool for D3D9 shaders (SM 2/3)
- `tools/lights8.py` – extra block for lights 5–8 (models, buildings)
- `tools/terrain8.py` – terrain (Terrain.bls) from 3 to 8 lights (see below)
- `tools/build.py` – builds the folder `patch-5.MPQ` (`--debug`: lights 5–8 in magenta, `--ladetest`: all lights in magenta, `--ohne-boden`: leave out the terrain, `--nur modelle|gebaeude|boden`: only one group (models, buildings, terrain) to narrow down a problem, see `docs/COA-VFOG.de.md`)
- `tools/paket.py` – packs the built folder into a zip (same layout as the release zips)
- `tools/release.py` – builds the three versions, runs the tests, compares checksums, packs (see "Release run")
- `tools/emu.py`, `tests/` – emulator and tests (`test_lights8.py`, `test_terrain8.py`, `d3d9_check.py`)
- `tests/pruefsummen/` – SHA-256 of the output confirmed in the game and of the source
- `.github/workflows/release.yml` – the release run on GitHub
- `docs/PLAN.de.md` (German) – original plan with risks
- `docs/BODEN.de.md` (German) – terrain: analysis, exe locations, exe part of the patcher

## Terrain

The terrain goes its own way: `Terrain.bls` computes at most 3 point lights per terrain
chunk from its own constants (c28–c36), which the exe fills (VA `0x7D0050`). The model
part of the lights patch does not change that, which is why at first the terrain still
got only 3 of the 8 lights, and at the edges of the terrain chunks you can see jumps
(as in the original). `tools/terrain8.py` extends the terrain variants to 8 lights,
which read lights 4–8 from c236–c250 (position, color and attenuation per light, as in
c28–c36). These constants are delivered by the terrain part of No. 69 (in the patcher
since 2026-10-12, now in the branch `st0ny-dev`); locations, format and the read-only
check of the exe part are in [docs/BODEN.de.md](docs/BODEN.de.md) (German). In-game
test 2026-10-14 (Sascha, eight campfires): no errors, the terrain is lit by all fires.
Since then the tool builds the terrain by default.

**Do not use the terrain shaders without this exe part** (exe with a state of No. 69
from before 2026-10-12): they then read leftovers of the model lights and the terrain
is lit incorrectly. For such an exe, leave out the terrain (`QUELLE` = source folder,
`ZIEL` = target folder):

```
python3 tools/build.py QUELLE ZIEL --ohne-boden
```

Test of the terrain shaders: `python3 tests/test_terrain8.py QUELLE`.

## Release run

`.github/workflows/release.yml` builds the finished package on GitHub from the original
shaders and attaches it to a release. The run calls `tools/release.py`, which does the
same locally (`AUSGABE` = output folder):

```
python3 tools/release.py QUELLE AUSGABE [--version v1.0.0]
```

Steps: unpack the source, build the three versions, emulator tests (models/buildings,
test build, terrain), compare the checksums of the built files against
`tests/pruefsummen/` (they must be bit-identical to the version confirmed in the game,
otherwise the run aborts), pack the zips, write `SHA256SUMS.txt` and the release text
(English, template `.github/release-notes.md`). The zips are reproducible (timestamp
from `SOURCE_DATE_EPOCH`, in the run the time of the commit).

**Triggers:**

- Push to a branch: dry run, the package is attached to the run as the artifact
  `patch-5.MPQ`.
- Push a tag `v*` (`git tag v1.0.0 && git push origin v1.0.0`): release with this tag.
- On the Actions page "Release" → "Run workflow": with `version` (e.g. `v1.0.1`) the run
  creates a release, without it a dry run; `entwurf` (draft) creates the release as a
  draft first. If the version already exists, the run refreshes the release notes and
  assets (e.g. after a change to the template) and removes packages it no longer builds;
  the tag stays where it is.

**Where the run gets the originals from.** Blizzard files do not go into the git
history. That is why the original vertex shaders (`vs_2_0`, `vs_3_0` from `common-2`,
`patch`, `patch-2`, `patch-3`, 126 files) are stored as `Shader-Quelle.zip` on an
**unpublished release draft** with the tag `quelle` in this repo. A draft is visible
only to people with write access, and the run downloads the file with its own token.
To set up or renew (once, by hand):

1. [Create a new release](https://github.com/Raz0r1337/WoW-lights-patch-shader/releases/new),
   type `quelle` under "Choose a tag" (gives "Create new tag: quelle on publish"; the
   tag is only created on publishing, i.e. never).
2. Title e.g. "Source (draft, do not publish)", drag `Shader-Quelle.zip` into the
   attachments field.
3. Click **"Save draft"**, not "Publish release".

The zip has the layout `Shader-Quelle/<MPQ-Name>/Shaders/Vertex/vs_2_0|vs_3_0/*.bls`
(one extra folder above is allowed, the run looks for the root); its checksums are in
`tests/pruefsummen/quelle.sha256`, and if the source deviates from them, the run reports
it. As a fallback, the run takes the zip from the address in the repo secret
`QUELLE_URL` if there is no draft.

**If the source or the tool is changed deliberately** (so the checksums rightly no longer
match): run `python3 tools/release.py QUELLE AUSGABE --summen-schreiben` (write
checksums) locally, test the output in the game, then check in `tests/pruefsummen/`
along with the change.

## Known issues

- In `patch.MPQ`, `MapObjDiffuse_Comp.bls`, `MapObjDiffuse_T1_Env.bls` and
  `MapObjUDiffuse_T1_Env.bls` are empty (0 bytes); in `common-2.MPQ` they are present.
  These are presumably deletion markers of the patch archive (the game then does not
  use the files). The tool skips them.

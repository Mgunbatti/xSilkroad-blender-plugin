# User guide

## Installation

Download `Silkroad_PK2_Editor_v2_6_0.zip` from [Releases](https://github.com/Mgunbatti/xSilkroad-blender-plugin/releases/latest). In Blender, open **Edit → Preferences → Get Extensions → Install from Disk**, select the ZIP and enable the extension. Disable an older installation first to avoid duplicate registrations.

Press **N** in the 3D Viewport and open **Silkroad PK2 Editor**. If needed, choose **Install PK2 Engine**. Engine installation requires an internet connection. The interface supports English and Turkish.

## Opening archives

Select `Data.pk2` and wait for the scan to finish. Related files are resolved from `Map.pk2`, `Media.pk2` and `Particles.pk2` in the same directory. Map textures require `Map.pk2`.

Browse folders or search by file name. Click a BSR, BMS, BSK, BAN, NVM or DOF entry to import it. You can also select a row and use the selected-model import button.

## Models and animations

Choose a **BSR** file for a textured model or character. Referenced meshes, materials, textures and skeletons are extracted together. Enable animation extraction to include referenced animations.

**BMS** loads mesh geometry; **BSK** loads a skeleton. Before importing a standalone **BAN**, select a compatible rig. Animation bone names must match the skeleton.

## Maps and dungeons

**NVM** imports terrain. Enable map-object extraction to include referenced trees, rocks and other navigation objects. **DOF** imports dungeon blocks; the same setting includes additional dungeon objects. Large dungeons may take several minutes.

The separate Jangan Unreal exporter uses `.o2` visual placements when available, including buildings and decorations absent from NVM navigation data.

## Saving and exporting

Save the scene as `.blend`, or export **FBX + PNG**. Select the mesh and its skeleton. By default, **All clips (separate FBXs)** writes the model to the chosen filename and each attached Action/NLA clip to `<model>_animations/`, with `Animations.json`. Muted imported clips are included; unrelated actions are excluded. Enable **Include animations** when importing the BSR first. **Active clip only** retains the previous single-animation export. Keep the generated texture directory beside the model FBX. Export destinations may be on any writable drive; the PK2 and Blender file do not need to be on that drive.

BMS files can be written back to PK2. The archive is backed up before writing, and the stored file is verified. Write-back is not supported for the other five formats.

## Creating a Jangan Unreal project

Open `Data.pk2` and wait for scanning to finish. Choose **4. Unreal Project → Create Jangan UE Project**, then select a project name and output location. A new project directory is created; an existing non-empty destination is protected.

With automatic Unreal import enabled, `UnrealEditor-Cmd.exe` is detected automatically. You can select its path manually if necessary. With automatic import disabled, the extension prepares FBX + PNG sources and the Unreal import script for later execution.

The button exports all 174 fixed Jangan terrain regions and their source environment placements: the city, Bandit Fortress and surrounding roads, forests and mountains. It preserves the current Blender scene. Unreal imports meshes and textures, creates materials and places the environment automatically. This is the direct plugin output; no separate map repair script is required. Monitor the panel status and wait for UE project ready. Use cancellation or Escape to stop; partial output and error logs remain available. Choose a new project name of at most 20 characters. This environment transfer does not create database mob spawns, combat, quests or the prototype UI.

Open the generated `.uproject` in Unreal. The startup map is `/Game/Jangan/Maps/Jangan`. `SourceAssets/manifest.json` records sources and placements; `ImportReport.json` records Unreal results; `UnrealImport.log` contains detailed output. Repeated models share a single Static Mesh asset.

The transfer covers central Jangan and the area near its walls, regions `60a6`–`63a9`. Environment geometry is static, including rigged trees frozen in their current pose. NPCs, quests, animated water, wind and gameplay systems are outside its scope. The pipeline was validated with Blender 5.2.2 and Unreal Engine 5.8.3.

## Transferring mobs and animations to Unreal

The project panel now has two full-map buttons. **Create Jangan UE Project (Tiles)** preserves the original square tile materials. **Create Jangan UE Project (Landscape)** builds the same static environment with native Unreal Landscape, imported height, softened masks and original ground textures. Soil, Grass, DryGrass, WetSoil, Rock and Paving are separate layers so yellow grass and dirt areas retain their source distribution. Dry grass is classified from source texture colors and names. Both modes cover the fixed 174-region Jangan boundary. Landscape mode omits old terrain meshes entirely; target layers can be painted in Unreal. Source texture selection and classification are recorded in GroundProfile.json and Textures/SourceTextures.json.

For automatic Landscape creation, use Unreal 5.8 on Windows. A compatible editor bridge is installed automatically. If the selected editor's BuildId differs from the bundled binary, the extension builds the supplied source with Unreal build tools; a C++ toolchain is required for that fallback. The separate **Export Jangan Landscape** button still prepares a manual heightmap/mask bundle. These project buttons create static environment projects, without mob spawns, combat or prototype UI.

Select a **BSR** mob or character in the PK2 list, then choose **Export Mob + Animations to UE**. Select an existing `.uproject` with **Python Editor Script Plugin** enabled. Close that Unreal project before automatic import.

The extension imports the resource into a temporary Blender scene, preserves its skeleton and skin weights, and exports the mesh plus each referenced animation. Content appears under `/Game/Silkroad/Characters/<character_name>`, with materials, textures and an `Animations` subfolder. The project's maps and descriptor are preserved. Repeated exports use a new folder rather than overwriting existing assets.

If the target project is open, disable automatic import. Sources and `import_character.py` are prepared under the project's `SourceAssets/SilkroadCharacters` folder. Run the script in Unreal's Python console with `py "ABSOLUTE_PATH_TO_import_character.py"`. The script creates assets without changing the current level.

The selected BSR must have meshes bound to exactly one skeleton. Only its referenced animations are included. A BSR without clips can still export its skeletal mesh. Multi-skeleton resources and unbound meshes produce an explicit error. This does not create NPC behavior, combat logic, an Animation Blueprint or automatic mob placement in the map.

## Error logs

Check the panel status after an operation. Blender's Text Editor contains per-format logs such as `Silkroad import .NVM`. `Silkroad dependency log` lists missing dependencies, and `Silkroad PK2 errors` records archive and import failures.

Missing optional textures or skeletons are recorded while available geometry can remain in the scene. Missing required meshes stop the import. A failed import may leave partial objects.

## Running tests

```text
python -m unittest discover -s tests -v
python -m pip install pk2api==1.5.0 --target engine
python tests/scan_assets.py "GAME_DIRECTORY"
blender --background --factory-startup --python tests/blender_failure_checks.py
blender --background --factory-startup --python tests/blender_e2e.py -- "GAME_DIRECTORY"
blender --background --factory-startup --python tests/blender_bms_winding.py -- "SOURCE_BMS" "OUTPUT_DIRECTORY"
```

Real-asset tests write results to `real_test_output`. See the [validation report](TEST_REPORT.md) and [Unreal transfer report](UE_TRANSFER_REPORT.md) for tested behavior and limits.

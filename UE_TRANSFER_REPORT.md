# Jangan Unreal transfer — v2.4.2

Validated with real Holigan `Data.pk2` and `Map.pk2` archives, Blender 5.2.2 and Unreal Engine 5.8.3.

## Coverage and results

The transfer covers central Jangan and the nearby area outside its walls: 16 regions, X indices 166–169 and Y indices 96–99 (`60a6`–`63a9`). It does not include the entire China map.

| Item | Count |
|---|---:|
| Terrain tiles | 16 |
| Unique model resources | 219 |
| Total Static Mesh assets | 235 |
| Model placements | 2,128 |
| Static Mesh Actors in a fresh project | 2,144 |
| Unique PNG contents | 379 |
| Scene materials | 579 |

The palace and golden dragon appear at their source placements. Roofs and walls render their exterior surfaces. A fresh project was created with the production script, saved and reopened for verification. All 2,128 model placements passed position and rotation checks: maximum position error **0 cm**, maximum yaw error **0.000236 degrees**.

An existing project was also repaired without deleting its legacy navigation-only actors. Seven such actors were hidden and moved to `Archive/NavigationOnly`. Its physical actor count can therefore exceed the fresh-project count.

## Visual placement correction

Earlier exports used NVM navigation objects, which omit some visual buildings and decorations. When available, the exporter now reads the visual `object.ifo` table and `.o2` records from `Map.pk2`. The path is `Y/X.o2`.

Spatial-block and LOD duplicates are combined using region, local UID and asset ID. Conflicting duplicates, truncated records, non-finite values and unparsed trailing bytes produce explicit errors. Foreign-region coverage records are excluded. The original NVM placement flow remains available when `.o2` files are absent.

Compound resources are expanded into their referenced model resources. Particle-only resources are recorded as skipped effects instead of being treated as static meshes. This validated dataset contained no skipped effects.

## Geometry and rotation correction

The BMS importer changes the source Y/Z axes to Blender's Z-up convention. That reflection requires a matching triangle-winding reversal. The importer now reverses the face order, and BMS export restores the original game order. A real roof mesh passed source-normal checks on all 532 faces; the exported BMS retained the original face indices.

The v2.4.1 placement correction remains in place: Unreal rotations use named pitch, yaw and roll parameters, and every resulting actor rotation is verified before saving. Texture, rig, animation and FBX + PNG workflows are preserved.

Twelve invalid UV loops in two source meshes remain recorded as repairs in the manifest: five in `W_CD_mc_cata` and seven in `CJ_lamp02`. Their fallback UV value is `(0, 0)`; original UV coordinates were not reconstructed.

## Extension processing coverage

By processed asset count, **235 / 235 = 100%**. Archive access, dependency resolution, Blender import and FBX + PNG generation use extension code. In this revision, all 219 model resources were exported again; the 16 terrain outputs were retained from the earlier validated extension export.

Unreal content was generated with the import template packaged by the extension. Existing-project repair and scene-validation scripts were run separately. This percentage measures asset processing coverage, not elapsed work time, code authorship or mouse interactions.

## Verification

- 87 unit and regression tests passed.
- A real BMS import/export checked 532 face normals and preserved source face indices.
- Real PK2 → Blender → FBX + PNG processing completed for all 219 model resources.
- Native extension ZIP creation and isolated Blender installation passed; version 2.4.2 and the Unreal export operator were registered.
- The production Unreal script built a fresh project. Reloading the saved map in a second Unreal process verified 235 mesh assets and 2,144 static actors.
- The repaired editor scene passed 2,128 placement checks and material resolution checks. Palace, dragon and overview screenshots were captured.

The panel button was not repeated through physical mouse interaction for this revision. Its export job ran in real Blender, and the production import script ran in real Unreal. The earlier complete operator test is retained as historical evidence.

| Report | Scope |
|---|---|
| `SourceAssets/manifest.json` | Source resources, placement paths, positions and repairs |
| `ImportReport.json` | Production import results from the fresh project |
| `FreshValidation.json` | Current saved-map reload test |
| `VisualValidation.json` | Current repaired-scene checks |
| `VisualRepairReport.json` | Existing-project repair results |
| `PluginTestReport.json` | Earlier complete extension-operator test |

## Usage

Install the extension ZIP through Blender's **Install from Disk** option. Open `Data.pk2`, wait for scanning to finish and choose **4. Unreal Project → Create Jangan UE Project**. Keep `Map.pk2` in the same game directory. Select a new project name; a non-empty destination is not overwritten.

FBX import and material compilation can take several minutes on the first run. Follow the panel status and project log. Open the resulting `.uproject` file in Unreal; the startup map is `/Game/Jangan/Maps/Jangan`.

## Limitations and provenance

The transfer produces a static city environment. It does not implement NPCs, quests, gameplay, animated water, wind or particle systems. Rigged environment assets are frozen in their evaluated pose. Packaged-game and performance tests were not performed. Every game asset and terrain UV variant was not compared against in-game rendering.

Original source copyright notices and GPL terms are retained. Game assets are excluded from the Git repository and extension source/test package. The `.o2` layout was verified against real archive records and compared with the [map format notes](https://github.com/y-xLeo/ikarus-map-editor/blob/main/SRO_MAP_FORMAT_NOTES.md).

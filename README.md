# xSilkroad Blender Plugin

Import Silkroad PK2 models, characters, animations, maps and dungeons into Blender. Export scenes as FBX with PNG textures, or create a separate Jangan Unreal Engine project.

**Tested with Blender 5.2.2 and Unreal Engine 5.8.3.** The interface supports English and Turkish.

## Download and install

1. [Download a published extension ZIP](https://github.com/Mgunbatti/xSilkroad-blender-plugin/releases/latest).
2. In Blender, open **Edit → Preferences → Get Extensions → Install from Disk**.
3. Select the ZIP and enable the extension.
4. Press **N** in the 3D Viewport and open **Silkroad PK2 Editor**. Use **Install PK2 Engine** if needed.

[Latest published release](https://github.com/Mgunbatti/xSilkroad-blender-plugin/releases/latest) · [Source and tests](https://github.com/Mgunbatti/xSilkroad-blender-plugin/tree/main) · [Changelog](CHANGELOG.md)

The source on `main` is version **2.7.0**; published release ZIPs may lag behind it.

## Features

- Browse and search PK2 archives directly in Blender.
- Import selected files and resolve referenced meshes, materials, textures, skeletons and animations.
- Import terrain and dungeon objects with separate Data/Map dependency roots.
- Save Blender scenes or export FBX with PNG textures.
- Write supported BMS edits back to PK2 with backup and verification.
- Transfer a selected mob or character directly into an existing Unreal project as a Skeletal Mesh, Skeleton and separate animation clips.
- Create a Jangan Unreal project with terrain, visual object placements, reusable meshes and materials.
- Inspect per-format import logs, missing dependencies and transfer results.

| Format | Content |
|---|---|
| BSR | Model and referenced resources |
| BMS | Mesh geometry |
| BSK | Skeleton |
| BAN | Animation |
| NVM | Terrain and navigation objects |
| DOF | Dungeon blocks and objects |

Open `Data.pk2`, wait for scanning and click a supported entry to import it. Select BSR for a textured model. Select a compatible skeleton before loading a standalone BAN. Related `Map.pk2`, `Media.pk2` and `Particles.pk2` files are resolved from the same directory.

**Create Jangan UE Project** exports central Jangan and its nearby surroundings into a new Unreal project. Visual map export includes visual `.o2` placements, restoring the palace, golden dragon and decorations, and corrects BMS triangle winding so roofs and walls render properly.

## Documentation

[User guide](USER_GUIDE.md) · [Turkish guide](README_TR.md) · [Changelog](CHANGELOG.md) · [Validation report](TEST_REPORT.md) · [Unreal transfer report](UE_TRANSFER_REPORT.md) · [Character transfer report](CHARACTER_TRANSFER_REPORT.md)

## License

[GPL-3.0-or-later](silkroad_pk2_bridge/LICENSE-GPL-3.0.txt). Original importer copyright notices are retained in their source files. Game assets are not included.


Version 2.7.0 offers two independent full-map project buttons: **Tiles** preserves the original square tile materials; **Landscape** creates native, paintable Unreal terrain with softened transitions. Both cover the fixed 174-region Jangan area and its static environment placements. Landscape keeps Grass, DryGrass, Soil, WetSoil, Rock and Paving separate and omits old terrain meshes. See [USER_GUIDE.md](USER_GUIDE.md) for automatic project creation and [JANGAN_LANDSCAPE.md](JANGAN_LANDSCAPE.md) for the separate manual heightmap workflow.

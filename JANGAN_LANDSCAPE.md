# Jangan Landscape — v2.6.0

In Blender: open Data.pk2 with the companion Map.pk2 available, then use **Silkroad → 4. Unreal Project → Export Jangan Landscape** (Turkish: **Jangan Landscape Aktar**).

Select **Jangan City**, **Bandit Fortress Test**, or **Jangan Region**. The region preset covers the 174 Jangan regions used by this transfer; foreign regions are rejected. Select a new output name. A folder beside that name contains:

- `Landscape.json`: exact world transform, source archives, resolution and height error.
- `Height.png` and `Height.r16`: 16-bit terrain, 2m source sample spacing.
- `Soil`, `Grass`, `Rock`: normalized 8-bit paint layer masks (PNG and raw R8).
- `Visibility`: holes for absent regions and Unreal-required padding.
- `UnrealPlugin/SilkroadLandscapeBridge`: editor-only Unreal plugin source.
- `ImportLandscape.py`: material and native Landscape importer.

## Unreal 5.8

1. Copy the bridge into `<project>/Plugins/SilkroadLandscapeBridge` and compile it using the Unreal C++ toolchain. It has been tested with Unreal 5.8 and the installed Visual Studio C++ tools. Other Unreal versions have not been validated.
2. Enable the bridge and Unreal's Python Editor Script Plugin. Open an empty or duplicated level. The importer adds a Landscape; it never removes existing terrain or other actors.
3. Optionally supply PNG textures in the export's `Textures` folder: `Soil_BaseColor`, `Grass_BaseColor`, `Rock_BaseColor`, and their `_Normal` and `_Rough` maps. Without textures the material supplies editable color defaults. Normal maps are expected to use DirectX conventions.
4. In the Unreal Python console, run:

```python
SILKROAD_LANDSCAPE_MANIFEST = r"C:/YourExport/JanganLandscape/Landscape.json"
SILKROAD_LANDSCAPE_ASSET_ROOT = "/Game/MyJanganLandscape"
exec(open(r"C:/YourExport/JanganLandscape/ImportLandscape.py", encoding="utf-8").read())
```

Use a new asset root for every import. Save your level after reviewing it. When replacing previously imported terrain, hide/remove only its matching FBX terrain actors in the duplicated level. Keep buildings, mobs, NPCs and foliage at their existing coordinates.

The generated Landscape has Soil/Grass/Rock paint targets with layer-info assets and native collision. Unreal-compatible sizes are obtained by padding, never resampling the source terrain. Visibility removes both rendering and collision in missing/padded areas. Source seams larger than 2cm are reported as errors rather than silently changed. Height precision is reported in the manifest.

This release exports Landscape data and supplies a native editor importer; it does not automatically install/compile the Unreal bridge from Blender. Game assets and textures are excluded from the extension ZIP. Existing FBX and character exporters are retained.

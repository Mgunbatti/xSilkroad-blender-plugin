# Changelog

## 2.4.2 — 2026-10-10

- Read visual map placements from Map.pk2 `.o2` files when available; preserve the NVM fallback.
- Include the palace, golden dragon, side buildings and decorations at their source placements.
- Deduplicate spatial-block and LOD records; report malformed or conflicting placements.
- Correct triangle winding during the BMS Y/Z conversion so roof and wall exteriors render correctly.
- Restore source face order when exporting BMS back to the game format.
- Validate a real roof mesh with 532 source-normal checks and unchanged exported face indices.
- Pass 87 regression tests, isolated extension installation and real Unreal saved-map checks covering 235 meshes and 2,128 model placements.

## 2.4.1 — 2026-10-10

- Use named Unreal Rotator parameters to prevent horizontal angles from being applied to pitch.
- Verify each actor's pitch, roll and yaw before saving; reject invalid rotations.
- Correct sun and initial camera rotations.
- Verify 577 placements in a real Unreal 5.8.3 scene and repair 301 tilted objects while preserving positions.

## 2.4.0 — 2026-10-10

- Add separate Jangan Unreal project creation from the panel.
- Export 16 NVM terrain regions, shared BSR models and source placements.
- Import FBX + PNG as Unreal meshes and materials, including masked foliage.
- Freeze environment skeletons in their evaluated pose and record invalid UV repairs.
- Process exports in a temporary Blender scene while preserving existing objects, materials and panel settings.
- Detect the Unreal editor automatically and report transfer results, missing assets and object counts.
- Protect existing non-empty project destinations.
- Pass 75 unit tests, real PK2 → Blender → Unreal 5.8.3 transfer and isolated ZIP installation.

## 2.3.3 — 2026-10-10

- Import supported files directly by clicking their entries in the PK2 browser.
- Correct Data/Map root resolution for NVM terrain, textures and object dependencies.
- Resolve DOF blocks and additional object meshes, materials and textures.
- Add missing NVM terrain UV coordinates.
- Report invalid files, incorrect extensions, empty imports and missing dependencies in Blender Text logs.
- Correct viewport-context and object-mode handling for Blender 5.2.
- Validate mesh, skeleton, animation and FBX + PNG workflows with real game assets.
- Correct extension packaging and manifest validation.

# Changelog

## 2.7.0 — 2026-10-13

- Add two independent full-map project buttons: Tiles for original per-face materials; Landscape for native, paintable terrain with six blended ground families.
- Preserve yellow/dry grass, green grass, ordinary soil, wet soil, rock and city paving with separate source-derived masks. Use source texture colors to identify dry grass instead of merging it into green grass.
- Landscape projects export the full 174-region terrain and all static environment placements, automatically choose original ground textures and install the native editor bridge.
- Landscape projects never export or spawn the old terrain meshes. Missing regions and padding are hidden and excluded from collision.
- Include a matching Unreal 5.8 Win64 bridge binary plus source. Check editor BuildId before use; incompatible builds trigger an automatic bridge build requiring the Unreal C++ toolchain.
- Add continuous broad color variation to the Landscape material and preserve separate manual heightmap and animated character export tools.
- Fix overly broad dry-grass classification and choose a genuinely yellow/brown source texture, preserving green vegetation as Grass.
- Verify 106 automated checks and a fresh, complete Landscape project through the public export button in Blender 5.2.2 and Unreal 5.8.3. All sampled collision traces passed; measured collision error stayed below 0.3 cm.
- Landscape mode groups source textures into six paint layers. Use Tiles mode to retain individual original tile textures; database spawns and gameplay are outside these environment export functions.

## 2.6.2 — 2026-10-13

- Create Jangan UE Project now exports the full fixed 174-region Jangan area and all referenced static environment placements by default.
- Share the same region boundary with the Jangan Landscape exporter; reject foreign selections and missing terrain rather than silently reducing the map.
- Frame the complete map in the generated Unreal editor viewport and record exported scope/regions in the import report.
- Reject project names exceeding Unreal's recommended 20-character limit before creating output folders.
- Keep the separate Landscape and animated character workflows; no prototype UI or database spawn data is bundled into the environment export.
- Avoid Edit Mode stalls when importing legacy cloth meshes and match source material names without case sensitivity.
- Persist skeletal material assignments correctly in Unreal so imported character and weapon textures survive saving and reopening.

## 2.6.1 — 2026-10-13

- Default FBX export now writes a model FBX and separate FBXs for every action associated with the selected rigs, including muted imported NLA clips.
- Preserve action slots, NLA state, pose mode, frame range and frame rate even if export fails; retain an active-clip-only option.
- Fix cross-drive publication: copy staged files to the destination volume before replacing the final FBX/report.
- Keep short temporary texture paths and portable relative PNG references.

## 2.6.0 — 2026-10-12

- Add Jangan-only Landscape export: city, Bandit Fortress sample, and fixed 174-region Jangan preset.
- Export 16-bit height PNG/R16, normalized Soil/Grass/Rock masks, hidden padding/missing-region masks and exact world coordinates.
- Include Unreal 5.8 editor bridge source and a Python material/Landscape importer with optional BaseColor, DirectX Normal and Roughness texture parameters.
- Reject foreign regions, duplicate regions, missing terrain/textures and inconsistent source seams; preserve PK2 archives and existing Blender scenes.
- Add scope, orientation, normalization, padding and quantization tests and a real Blender export regression check.
- Keep the existing FBX and skeletal animation workflows.


## 2.5.1

- Register the two Unreal operators independently so character selection does not disable the Jangan exporter.
- Show the BSR selection requirement beside the character transfer button.
- Add a Blender regression check covering nine selection/session states and both registered operators.


## 2.5.0 — 2026-10-11

- Add **Export Mob + Animations to UE** for a selected BSR resource.
- Preserve skeletal meshes, skeletons, skinning and referenced animation clips instead of freezing them as static geometry.
- Export each animation separately with its source frame rate and Blender action slot; bind every Unreal clip to the imported skeleton.
- Build character materials and PNG textures, including masked alpha textures.
- Import into an existing Unreal project under a new character folder, without saving or modifying its maps.
- Protect existing assets from overwrite and prevent automatic imports into an open target project on Windows.
- Validate sampled bone tracks, skeleton compatibility and animation durations; preserve the original Blender scene and materials.
- Pass 93 regression tests, isolated extension installation and real wolf transfer: 37 source bones, 1,223 mesh vertices and 15 animation clips. Reloaded Unreal clips passed bone-motion checks.

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

# Validation report — v2.5.0

Test environment: Windows, Blender 5.2.2 LTS and Unreal Engine 5.8.3. Real asset tests used Holigan PK2 archives opened in read-only mode. Game binaries and exported game assets are excluded from the repository and extension source packages.

## Current release

93 unit and regression tests passed. The real `silkroad_editor.export_ue_character` operator transferred a wolf BSR into Unreal with 37 source bones, 1,223 mesh vertices and 15 separate clips. Original Blender objects, scene FPS and a colliding material name/color were preserved. The existing Unreal project descriptor was unchanged. The same transfer into an existing Jangan project preserved its saved map byte for byte.

Saved Unreal assets were reloaded in a second process. Bone tracks, sample counts, skeleton compatibility, duration and finite transforms were checked; walking and running clips showed changing bone poses. Native 2.5.0 ZIP creation and isolated extension installation passed with the new operator registered. See [character transfer validation](CHARACTER_TRANSFER_REPORT.md).

## Jangan validation baseline — v2.4.2

- **87 unit and regression tests passed.** Coverage includes archive handling, importer dispatch, dependency extraction, material and animation compatibility, PNG export, map placements and extension metadata.
- A real BMS roof mesh was imported and exported in Blender. All **532 faces** aligned with the source normals; exported face indices matched the source.
- The updated PK2 → Blender → FBX + PNG pipeline processed **219 model resources**. The **16 terrain outputs** were reused from the previous validated extension export.
- The native extension ZIP was built and installed in an isolated Blender profile. Version 2.4.2 and the Unreal export operator were verified.
- A fresh Unreal project was generated with the production import template, saved and reopened in a second Unreal process. **235 meshes, 2,128 model placements and 16 terrain actors** were verified.
- Maximum placement error: **0 cm**. Maximum yaw error: **0.000236 degrees**. All 579 scene materials resolved.
- The updated editor scene was checked separately. The palace and golden dragon were present, and screenshots confirmed the visible roof and wall surfaces.

The current release was tested through the actual Blender export job and Unreal production script. The panel button was not rerun through physical mouse interaction from start to finish. The earlier full operator test remains recorded separately in `test_evidence/ue_PluginTestReport.json`.

Current evidence:

- `test_evidence/unit_tests_242.log`
- `test_evidence/bms_winding_real_result.json`
- `test_evidence/ue_install_result.json`
- `test_evidence/ue_FreshValidation.json`
- `test_evidence/ue_VisualValidation.json`

## Importer validation baseline

The initial compatibility audit used the v2.3.2 Source_Tests package. Its extension files matched the v2.3.2 PNG Fix package byte for byte. The original 54 tests passed before modification; the v2.3.3 audit passed 66 tests, including 12 added cases. Original copyright and license headers remain in the source. File hashes and the change inventory are recorded in `SOURCE_PROVENANCE.json`.

Real imports were executed in Blender background mode using a `VIEW_3D` window context override. Scene contents were checked in addition to operator return values. Row selection and `entry_index` dispatch were tested through real Blender APIs.

| Format / option | Real sample | Scene objects | Total mesh vertices | Result |
|---|---|---:|---:|---|
| BMS | `prim/mesh/mob/europe/wolf01.bms` | 1 | 371 | Passed |
| BSK | `prim/skel/mob/europe/wolf.bsk` | 1 | 0 | Passed |
| BAN | `prim/ani/mob/europe/wolf/wolf_stand01.ban` | 1 | 0 | Passed |
| BSR | `res/mob/arabia/baruswolf_adonis1.bsr` | 4 | 1,223 | Passed |
| FBX + PNG export | BSR sample | — | — | Passed |
| FBX reimport | Exported sample | 4 | — | Passed |
| NVM | `navmesh/nv_1315.nvm` | 1 | 9,409 | Passed |
| DOF | `dungeon/asiam/r1_cv/pha_cv.dof` | 829 | 435,132 | Passed |
| NVM with objects | `navmesh/nv_1315.nvm` | 22 | 12,182 | Passed |
| DOF with objects | `dungeon/asiam/r1_cv/pha_cv.dof` | 2,479 | 709,098 | Passed |

The BSR sample contained 37 bones and 102,494 keyframes connected through NLA slots. The standalone BAN test also checked connected NLA keyframes. FBX + PNG export produced two readable textures without missing-texture entries. FBX reimport verified the rig and PNG image data. JSON `actions` and `images` fields represent total session datablocks, not newly created counts.

Twelve real Blender failure cases covered invalid signatures and incorrect extensions across all six formats. Failures produced tracebacks and did not report `FINISHED`. Synthetic tests cover recursive DOF/BSR/BMT extraction, separate NVM Data/Map roots, tile textures, object tables, missing IDs, path traversal, binary bounds, importer call signatures, false returns, empty results and exceptions. Existing PK2 write-back, asynchronous scanning, viewport, animation-slot, translation and PNG tests passed.

## Dispatch and dependency checks

| Extension | Import operator | Dependencies | Required scene result |
|---|---|---|---|
| BMS | `jmxvbms_0110` | Selected mesh; use BSR for associated materials | Mesh with vertices |
| BSK | `jmxvbsk_0110` | Skeleton, signature 0101; historical operator name retained | Armature with bones |
| BAN | `jmxvban_0102` | Animation and a selected compatible rig | Connected action and keyframes |
| BSR | `jmxvres_0109` | BMS; optional BMT, textures, BSK and BAN | Mesh, materials and optional rig/NLA |
| DOF | `jmxvdof_0101` | Block BSR → mesh/material/texture; optional object BSR | Block and object mesh geometry |
| NVM | `jmxvnvm_1000` | Data/navmesh; Map/tile2d.ifo and textures; optional object.ifo → CPD/BSR | 97 × 97 height mesh with UVs |

The selection, row index, extension check, asset preparation and nested importer calls use a compatible Blender viewport context. Data and Map roots are resolved separately. Optional missing dependencies are listed; missing required meshes or resources stop the import. Invalid binaries, empty geometry, empty rigs and disconnected animations are not treated as successful imports. Each format has a Blender Text log, with separate archive and dependency error records.

## Scope and limitations

These tests cover selected real assets rather than every Silkroad asset or client version. All terrain rotation flags, skeleton/animation combinations and material variants were not compared against in-game rendering. NVM expects 96 × 96 tiles and 97 × 97 height vertices; incompatible layouts produce errors. NVM and DOF import tests do not imply export or PK2 write-back support for those formats. The unfinished NVM exporter remains disabled.

An interrupted or failed import may leave partial scene objects. Standalone BMS imports do not guess associated materials. Temporary dependency workspaces remain available while Blender images reference them. Native extension builds and isolated installation checks do not modify the normal Blender profile.

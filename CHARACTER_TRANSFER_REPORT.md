# Character transfer — v2.5.0

Selected BSR resources can now be transferred into an existing Unreal project as a Skeletal Mesh, Skeleton, PNG textures, materials and separate animation clips. The exporter uses the existing PK2 dependency resolver and Blender importers, retaining skinning instead of baking a static mesh. Each animation is exported with its own action slot, frame range and source FPS, then imported against the same Unreal skeleton.

## Real validation

Tested on Windows with Blender 5.2.2 and Unreal Engine 5.8.3, using `res/mob/europe/wolf.bsr` from a read-only Holigan archive:

- 37 source bones and 1,223 mesh vertices.
- 15 animation clips, including stand, walk, run, attacks and death.
- Unreal contains 38 tracks, including the FBX armature root.
- The real export operator completed automatically, with the original Blender scene objects, frame rate and material name/color preserved.
- The target project descriptor was unchanged. Import into the existing Jangan project also preserved its saved map byte for byte.
- A second Unreal process reloaded the saved assets and sampled bone transforms. All clips had sampled bone tracks; walking and running showed moving bones. Skeleton compatibility, clip durations and finite transforms passed.
- Import also passed with the default Interchange FBX setting enabled. The script temporarily selects the legacy skeletal import path and restores the original setting afterward.
- 93 unit/regression tests passed. Native extension build and installation into an isolated Blender profile passed with the new operator registered.

## Operation

Choose a BSR in the PK2 list and use **Export Mob + Animations to UE**. Select an existing `.uproject` with Python Editor Script Plugin enabled. Close the target editor before automatic import. With automatic import disabled, run the prepared `import_character.py` script in that editor's Python console.

Assets are created under `/Game/Silkroad/Characters/<character_name>`, with material, texture and animation subfolders. Source FBX/PNG files, the manifest, detailed engine log and ImportReport.json remain under `SourceAssets/SilkroadCharacters/<character_name>`. Repeated exports create separate folders; existing assets are not overwritten. Maps are not edited or saved by the character import script.

## Limits

Only animations referenced by the selected BSR are included. The resource must contain meshes bound to exactly one skeleton. Multi-skeleton and unbound-mesh resources fail explicitly. A skeletal BSR without animations can still export its mesh and skeleton. This feature does not generate Animation Blueprints, NPC behavior, combat logic or map placements. The tested FBX produced bind-pose warnings; Unreal rebuilt its bind pose successfully, and subsequent asset and motion checks passed. A visual comparison against every source animation was not performed.

Game assets are excluded from extension and source releases. Original copyright and GPL license notices are preserved.

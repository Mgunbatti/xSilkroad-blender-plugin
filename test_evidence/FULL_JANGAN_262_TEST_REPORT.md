# Full Jangan direct plugin export — 2.6.2

The public Create Jangan UE Project operator was run in Blender 5.2.2 with a new empty destination and the real Data.pk2/Map.pk2 archives. It exported every source file from scratch and automatically ran the plugin's generated Unreal importer in Unreal 5.8.

- 101 automated checks passed.
- 174 terrain regions, 361 environment model resources, 5961 placed environment instances.
- 6135 imported source actors; import completed without errors.
- Placement and material checks passed for all 5961 environment instances. Maximum measured position error: 0 cm.
- Original Blender scene counts restored. No injected manifest, reused old FBX, post-import terrain fixes, material repair script, prototype UI or gameplay code.
- Rendering checked with a transient screenshot camera. The generated level was not saved or altered during that check.

This is static source environment geometry. Source tile textures and original model quality remain visible. Database mob/NPC spawns, skills and prototype gameplay are not part of this map-project button. The separate animated character and Landscape export workflows remain available. Full-map gameplay performance has not been benchmarked.

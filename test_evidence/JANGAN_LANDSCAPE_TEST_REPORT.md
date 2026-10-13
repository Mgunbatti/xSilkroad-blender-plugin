# Jangan Landscape v2.6.0 verification

- 96 unit tests passed, including scope rejection, normalized masks, 16-bit precision, coordinates and terrain seam checks.
- Real Blender 5.2 operator export passed; source scene and material counts were preserved. English/Turkish registration and prior Unreal exporter availability were checked.
- Real Data.pk2 + Map.pk2 export: Bandit 253x253; city 442x442; full Jangan 1828x1387, 174 fixed regions. Maximum recorded quantization error: 0.2852cm. Shared source seams: 0cm.
- Unreal 5.8 editor bridge compiled and imported a real ALandscape in a separate playable Bandit Fortress map. Soil, Grass and Rock targets and an edit layer persisted.
- Five character-channel collision traces matched encoded source heights within 0.0061cm. Padding collision exclusion passed. All 6142 spawn actors remained.
- Final materials were visually checked using the rendered Bandit_Landscape_v5.png. The main playable and full maps remain unchanged by this Landscape trial.
- Full 174-region height/mask export was checked; full-world Landscape rendering and performance have not been validated. Other Unreal versions have not been validated. Original game assets are excluded from release ZIPs.

The public Blender feature produces the Landscape bundle. Automatic editor creation uses the supplied Unreal bridge and Python import script; bridge compilation/installation is a separate step. A locally built Unreal 5.8 bridge is included in the companion ZIP, with source for rebuilds.

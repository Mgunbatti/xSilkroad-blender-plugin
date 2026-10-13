# FBX export fixes 2.6.1

- 97 automated checks passed.
- Blender 5.2.2: registered export operator uses All clips by default; model plus three attached clips exported, all three reimported with actual bone motion.
- Muted NLA clips included; unrelated scene action excluded. Action slot, pose mode, NLA flags, timeline and FPS restore after success and a simulated mid-export failure.
- Cross-drive publication regression passed with cross-directory rename explicitly rejected. Files copy to the destination before a same-directory atomic replacement.
- A second physical drive was unavailable on this machine, so physical D:/E: export was not tested.

Import the BSR with Include animations enabled, select mesh and skeleton, then Export FBX + PNG. Default All clips (separate FBXs) writes the model FBX and a model_animations folder. Import the model in Unreal first, then each animation FBX with its skeleton selected. Active clip only preserves single-clip export. Keep the PNG texture folder beside the model.

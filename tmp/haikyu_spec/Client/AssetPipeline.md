# Asset Pipeline Specification

## 1. 3D Models
- **Format**: FBX (Unity Humanoid compatible)
- **Polycount**: ~15,000 tris per character
- **Texture**: 2048x2048 (BaseMap, Normal, Mask)
- **Shader**: Custom Toon Shader (Outline + Step Lighting)

## 2. Animations
- **Naming**: `CH_[ID]_[ActionName]`
- **Examples**:
    - `CH_HINATA_Serve_Start`
    - `CH_HINATA_Spike_Loop`
    - `CH_HINATA_Victory_01`

## 3. VFX
- **Tool**: Unity VFX Graph / Shuriken
- **Requirements**: Under 50 particles per effect for mobile performance.

## 4. Audio
- **BGM**: Loopable OGG
- **SE**: WAV (Short latency)
- **Voice**: Character specific voice lines triggered by SkillID.

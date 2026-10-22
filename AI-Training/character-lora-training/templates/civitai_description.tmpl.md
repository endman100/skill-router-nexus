# <character> (<character_ja>) – <anime> (<anime_ja>)

Character LoRA for <character> from <anime>, for <base_model>.

## Usage

- Trigger: `<trigger>`
- LoRA strength: <strength>
- Base model: <base_model> (tested with <test_checkpoint>)
- Test settings: sampler `<sampler>`, scheduler `<scheduler>`, CFG <cfg>, <steps> steps, <width>x<height>

## Prompt structure

Prompts follow this Langfuse prompt template:

```
masterpiece, best quality, highres, ultra detailed, <trigger>, {{character_features}}, {{cloth_feature}}, {{other}}
```

- `character_features` = the character appearance tag group
- `cloth_feature` = the default outfit tag group, or your own outfit
- `other` = pose / composition / scene

## Trigger words

1. Trigger word:

```
<trigger>
```

2. Character features:

```
{character_features}
```

3. Default outfit:

```
{outfit_tags}
```

## Keep the default outfit

Use the character features with the default outfit.

```
masterpiece, best quality, highres, ultra detailed, <trigger>, {character_features}, {outfit_tags}, {other_scene}
```

## Change the outfit

Keep the character features, and replace the outfit group with your own clothing tags.

```
masterpiece, best quality, highres, ultra detailed, <trigger>, {character_features}, {change_outfit_tags}, {other_scene}
```

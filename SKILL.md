---
name: skill-card-generator
description: >-
  Generate Skills Hub card images featuring brand IP mascot (white puppy).
  Uses image-to-image generation to maintain IP consistency while varying expressions, outfits, and backgrounds.
  For AI Agent programmatic calls, not manual user triggers.
  Common scenarios: any request to create visual cards, illustrations, or images for skills, features, or capabilities showcase

trigger_keywords:
  - card
  - skill
  - generate
  - create
  - image
  - illustration
  - visual
  - 卡片
  - 生成
  - 图片

version: 1.0
author: your-team
---

# Skill Card Generator Expert

You are the **Skill Card Generator Expert** — a specialized agent responsible for generating branded Skills Hub card images using the Doubao image-to-image API. You maintain strict IP consistency by always using the reference mascot image as the visual base, never describing the mascot's appearance in text.

---

## Core Principles

1. **Never describe the mascot's base appearance in prompts.** The white puppy's shape, fur, face, and body come entirely from `assets/ip-reference.png`. Text prompts only describe what *changes*.
2. **Only three things change per card:** expression/emotion, outfit/accessories, and background/environment.
3. **Reference image is mandatory.** Every API call must include `ip-reference.png` as the input image. Generating without it will produce inconsistent results.
4. **Custom scene generation only.** Describe any scene in natural language — English, Chinese, or mixed.
5. **Return the output file path** so the calling Agent can use or display the image immediately.

---

## Execution Flow

When asked to generate a skill card, follow these steps in order:

### Step 1 — Build the prompt
Use `scripts/prompt_builder.py` to assemble the prompt. The prompt structure is:
```
[expression change] + [outfit and accessories] + [background and environment]
```
Do **NOT** include phrases like "white puppy", "dog", "fluffy", or any description of the mascot's physical appearance.

### Step 2 — Call Doubao API
Submit a multipart request containing:
- `image`: the binary content of `assets/ip-reference.png`
- `prompt`: the assembled text prompt
- `model`: value of `DOUBAO_MODEL` env var

### Step 3 — Save and return
Save the returned image to `output_path` (or auto-generate a timestamped filename) and return the absolute file path.

---

## Required Environment Variables

Set these before running. The skill will raise `EnvironmentError` with a clear message if any are missing.

| Variable | Description |
|----------|-------------|
| `DOUBAO_API_KEY` | Authentication key for Doubao API |
| `DOUBAO_ENDPOINT` | Full API endpoint URL |
| `DOUBAO_MODEL` | Model identifier — use `seedream-5.0-lite` |

---

## Function Interface (for Agent callers)

### Mode 1 — Single custom scene

```python
from scripts.generate_card import generate_custom_card

# English
path = generate_custom_card("buying tickets at a theme park, excited expression")

# Chinese
path = generate_custom_card("门票预订场景，小狗在售票处前开心地拿着门票")

# Mixed / detailed
path = generate_custom_card(
    "playing guitar on a stage with colorful spotlights, cool rock star vibe, "
    "night concert atmosphere"
)

# With custom output path
path = generate_custom_card(
    scene_description="cooking pasta in a cozy kitchen, happy and focused",
    output_path="/output/cards/cooking_promo.png"
)
```

**Rules for `scene_description`:**
- Describe expression, outfit, props, and background — NOT the mascot's body/appearance
- No length limit; be as specific as needed
- Do NOT include style directives (3D, Pixar, etc.) — appended automatically

---

### Mode 2 — Multiple variations of the same scene

Use when you want **several different takes on one scene** to pick the best composition. The API naturally produces different results each time — pose, lighting, framing — even with identical prompts.

> **Cost note:** Each variation ≈ ¥0.22. Plan accordingly:
> 3 variations ≈ ¥0.66 | 5 variations ≈ ¥1.10 | 10 variations ≈ ¥2.20

```python
from scripts.generate_card import generate_custom_card_variations

# 5 different versions of the same scene
paths = generate_custom_card_variations(
    "buying tickets at theme park entrance, excited expression",
    num_variations=5
)
# Returns ordered list v1 → v5:
# ["…/custom_buying_tickets_at_v1_20260402_….png",
#  "…/custom_buying_tickets_at_v2_20260402_….png", ...]

# Chinese scene, 3 versions
paths = generate_custom_card_variations("在咖啡厅工作", num_variations=3)

# 10 options for art direction review
paths = generate_custom_card_variations(
    scene_description="cooking pasta in kitchen, happy and focused",
    num_variations=10,
    output_dir="/output/review/cooking/"
)
```

---

### Mode 3 — Batch custom scenes

Use when generating **multiple cards in one call**. Each description in the list produces one card. The batch continues even if individual generations fail.

```python
from scripts.generate_card import generate_custom_cards_batch

# Basic batch
scenes = [
    "买门票场景，开心的表情",
    "在咖啡厅工作，专注的样子",
    "海边冲浪，兴奋激动",
]
paths = generate_custom_cards_batch(scenes)
# Returns: ["/output/cards/custom_..._001.png", "/output/cards/custom_..._002.png", ...]
# Order matches input list. Failed items are excluded (logged as errors).

# With custom output directory
paths = generate_custom_cards_batch(scenes, output_dir="/my/campaign/cards/")
```

**When to use which mode:**

| Scenario | Use |
|----------|-----|
| One scene, want multiple options to choose from | `generate_custom_card_variations()` |
| Multiple different scenes, one card each | `generate_custom_cards_batch()` |
| Single scene, one card | `generate_custom_card()` |

---

## Output Format

- Format: PNG
- Filename (auto): `custom_{scene_slug}_{YYYYMMDD}_{HHMMSS}.png`
- Default output directory: `./output/cards/` (created automatically if missing)
- Returns: absolute path string

---

## CLI Usage

```bash
# Single custom scene
python scripts/generate_card.py --custom "buying tickets at amusement park"
python scripts/generate_card.py --custom "门票预订，小狗开心拿着门票" /output/tickets.png

# Multiple variations of ONE scene  (--variations <count> "<scene>")
python scripts/generate_card.py --variations 5 "buying tickets at theme park entrance"
python scripts/generate_card.py --variations 3 "在咖啡厅工作" /output/review/

# Batch — different scenes, one card each
python scripts/generate_card.py --custom-batch "scene 1" "scene 2" "scene 3"
python scripts/generate_card.py --custom-batch \
  "买门票场景，开心的表情" \
  "在咖啡厅工作，专注的样子" \
  "海边冲浪，兴奋激动"
```

---

## Error Handling

| Exception | Cause | Action |
|-----------|-------|--------|
| `ValueError` | Empty `scene_description` | Ensure description is non-empty |
| `FileNotFoundError` | `ip-reference.png` missing | Upload reference image to `assets/` |
| `EnvironmentError` | Missing env vars | Set `DOUBAO_API_KEY`, `DOUBAO_ENDPOINT`, `DOUBAO_MODEL` |
| `RuntimeError` | API call failed | Check API key validity and endpoint URL |

---

## File Structure Reference

```
skill-card-generator/
├── SKILL.md                    # This file
├── scripts/
│   ├── generate_card.py        # Main entry point for Agent calls
│   └── prompt_builder.py       # Prompt assembly logic
├── references/
│   └── api-guide.md            # Doubao API reference
└── assets/
    ├── ip-reference.png        # Brand mascot reference (REQUIRED before use)
    ├── skill-config.json       # Skill configurations (empty, reserved)
    └── prompt-template.txt     # Prompt structure template
```

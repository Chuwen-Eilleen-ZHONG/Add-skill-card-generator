# How to Run - Skill Card Generator

## Prerequisites
- Python 3.8+
- Doubao API credentials
- ip-reference.png uploaded to assets/

## Setup

### 1. Install Dependencies
```bash
cd skill-card-generator
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```

Then edit `.env` and fill in:
- `DOUBAO_API_KEY=your_api_key_here`
- `DOUBAO_ENDPOINT=https://ark.cn-beijing.volces.com/api/v3/images/generations`
- `DOUBAO_MODEL=doubao-seedream-5-0-260128`

### 3. Verify Setup
```bash
ls assets/ip-reference.png
cat .env
```

---

## Usage Method 1: Terminal / Command Line

### Single Card Generation
```bash
# Using predefined skill
python -m scripts.generate_card data_analysis

# Custom scene
python -m scripts.generate_card --custom "buying tickets at theme park"
```

### Multiple Variations (Same Scene)
```bash
# Generate 5 versions of same scene
python -m scripts.generate_card --variations 5 "buying tickets at amusement park"

# Chinese description
python -m scripts.generate_card --variations 3 "小狗在咖啡厅工作"
```

Cost: `num_variations × ¥0.22`

### Batch Different Scenes
```bash
python -m scripts.generate_card --custom-batch "scene 1" "scene 2" "scene 3"
```

### List Available Skills
```bash
python -m scripts.generate_card
```

---

## Usage Method 2: Agent Natural Language Interaction

### Agent Setup Instructions

Tell your Agent:

> "I have a skill card generator. Import these functions from `scripts.generate_card`:
> - `generate_custom_card(scene)` — Single card
> - `generate_custom_card_variations(scene, num)` — Multiple versions of the same scene
> - `generate_custom_cards_batch([scenes])` — Different scenes, one card each
> - `generate_skill_card(skill_id)` — Predefined skill from skill-config.json
>
> Each image costs ¥0.22. Always run from the `skill-card-generator/` directory with `PYTHONPATH=.`"

### Conversation Examples

**Example 1: Single Card**

User: "给我生成一个买门票的卡片"

Agent executes:
```python
from scripts.generate_card import generate_custom_card
path = generate_custom_card("buying tickets at amusement park entrance, excited expression")
```

---

**Example 2: Multiple Variations**

User: "生成咖啡厅场景，给我 5 个版本"

Agent executes:
```python
from scripts.generate_card import generate_custom_card_variations
paths = generate_custom_card_variations("working in cozy cafe", num_variations=5)
```

Cost: ¥1.10 (5 images)

---

**Example 3: Batch Different Scenes**

User: "生成买门票、订酒店、租车的卡片"

Agent executes:
```python
from scripts.generate_card import generate_custom_cards_batch
paths = generate_custom_cards_batch([
    "buying tickets at attraction entrance, excited expression",
    "booking hotel at front desk, happy and satisfied expression",
    "renting a car at agency, confident ready-to-go expression",
])
```

Cost: ¥0.66 (3 images)

---

**Example 4: Predefined Skill**

User: "生成数据分析技能卡片"

Agent executes:
```python
from scripts.generate_card import generate_skill_card
path = generate_skill_card("data_analysis")
```

---

## Agent Integration Template

```python
from scripts.generate_card import (
    generate_custom_card,
    generate_custom_card_variations,
    generate_custom_cards_batch,
    generate_skill_card,
    list_available_skills,
)

# Single card
path = generate_custom_card("scene description")

# Multiple versions of same scene
paths = generate_custom_card_variations("scene", num_variations=5)

# Batch of different scenes
paths = generate_custom_cards_batch(["scene1", "scene2", "scene3"])

# Predefined skill
path = generate_skill_card("data_analysis")

# List all valid skill IDs
skills = list_available_skills()
```

---

## Output Location

All images saved to: `skill-card-generator/output/cards/`

Filename formats:

| Mode | Format |
|------|--------|
| Predefined skill | `data_analysis_20260402_150123.png` |
| Custom single | `custom_20260402_150123.png` |
| Variations | `custom_buying_tickets_at_v1_20260402_150123.png` |
| Batch | `custom_batch_001_20260402_150123.png` |

---

## Cost Reference

| Action | Cost |
|--------|------|
| 1 card (any mode) | ¥0.22 |
| 3 variations | ¥0.66 |
| 5 variations | ¥1.10 |
| 10 cards | ¥2.20 |

---

## Troubleshooting

**"API key not found"**
Check `.env` file exists in `skill-card-generator/` and contains `DOUBAO_API_KEY`.

**"Reference image not found"**
Verify `ip-reference.png` exists in `assets/`. Upload it before running.

**"Generated image is not square"**
API returned a non-1:1 image. Verify the `size` parameter is `"1920x1920"` in `_call_doubao_api()`.

**"ModuleNotFoundError: No module named 'scripts'"**
Run with `PYTHONPATH=.` from the `skill-card-generator/` directory:
```bash
cd skill-card-generator
PYTHONPATH=. python -m scripts.generate_card data_analysis
```

**Rate limiting**
Built-in 2-second delay between API calls should prevent this. If errors persist, increase the `time.sleep()` value in `generate_custom_cards_batch()` or `generate_custom_card_variations()`.

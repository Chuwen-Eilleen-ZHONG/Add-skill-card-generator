# Skill Card Generator

自动为 Skills Hub 生成品牌吉祥物卡片图。采用 **图生图** 技术，以固定 IP 参考图为基底，通过 Prompt 控制表情、服装、背景的变化，确保每张卡片的角色形象保持一致。

---

## IP 参考图

> 所有生成图均以此图为基底，角色外观完全来自参考图，Prompt 只描述变化部分。

<img src="assets/ip-reference.png" width="300" alt="IP 参考图 - 白色小狗">

---

## 三种生成模式

### 模式一：预定义技能卡片

从 `assets/skill-config.json` 读取配置，内置 12 种技能，每种技能有预设的表情、服装、背景。

**终端运行**
```bash
python -m scripts.generate_card data_analysis
```

**Agent 代码调用**
```python
from scripts.generate_card import generate_skill_card

path = generate_skill_card("data_analysis")
```

**可用技能 ID**
```bash
python -m scripts.generate_card          # 不带参数列出所有 skill_id
```

| skill_id | 中文名 |
|----------|--------|
| `data_analysis` | 数据分析 |
| `travel_planning` | 旅游规划 |
| `creative_writing` | 创意写作 |
| `coding` | 编程开发 |
| `graphic_design` | 图形设计 |
| `marketing` | 营销策划 |
| `fitness_coaching` | 健身指导 |
| `cooking` | 美食烹饪 |
| `music_production` | 音乐制作 |
| `language_learning` | 语言学习 |
| `finance_planning` | 财务规划 |
| `photography` | 摄影创作 |

**生成效果示例 — `data_analysis`**

| 参考图 | 生成结果 |
|--------|---------|
| <img src="assets/ip-reference.png" width="240"> | <img src="output/cards/data_analysis_20260402_162216.png" width="240"> |

> Prompt：`focused and analytical, wearing smart glasses, wearing a white lab coat, holding a tablet showing graphs...`

---

### 模式二：自定义场景（单张）

无需预设，Agent 可用任意自然语言描述场景，支持中英文混合。

**终端运行**
```bash
# 英文描述
python -m scripts.generate_card --custom "buying tickets at a theme park, excited expression, holding colorful tickets"

# 中文描述
python -m scripts.generate_card --custom "小狗在图书馆看书，戴着圆框眼镜，温馨的暖光氛围"
```

**Agent 代码调用**
```python
from scripts.generate_card import generate_custom_card

# 英文
path = generate_custom_card("buying tickets at a theme park, excited expression")

# 中文
path = generate_custom_card("小狗在图书馆看书，戴着圆框眼镜，沉浸其中")
```

**Prompt 撰写规则**
- ✅ 描述：表情 / 情绪、服装 / 道具、背景 / 场景、氛围 / 灯光
- ❌ 不要描述：角色外观（毛色、体型、脸型等）— 这些由参考图决定

**生成效果示例**

| 场景描述 | 生成结果 |
|----------|---------|
| 在主题公园买门票，兴奋地拿着彩色门票 | <img src="output/cards/custom_20260402_163841.png" width="240"> |
| 图书馆看书，圆框眼镜，飘浮的书页，暖光烛光 | <img src="output/cards/custom_20260402_164011.png" width="240"> |

---

### 模式三：同一场景多版本（Variations）

相同 Prompt 每次 API 调用都会产生不同的构图、光影、角度，适合生成多个版本供选择。

**终端运行**
```bash
# 生成 3 个版本
python -m scripts.generate_card --variations 3 "sitting in a cozy library reading a book, wearing round glasses"
```

**Agent 代码调用**
```python
from scripts.generate_card import generate_custom_card_variations

paths = generate_custom_card_variations(
    "sitting in a cozy library reading a book, wearing round glasses",
    num_variations=3
)
# 返回: ["…_v1_….png", "…_v2_….png", "…_v3_….png"]
```

> 💡 **费用提示：** 每张 ¥0.22。生成 3 个版本 = ¥0.66，5 个版本 = ¥1.10。

**生成效果示例 — 同一场景两个版本**

| v1 | v2 |
|----|-----|
| <img src="output/cards/custom_sitting_in_a_cozy_li_v1_20260402_165208.png" width="240"> | <img src="output/cards/custom_sitting_in_a_cozy_li_v2_20260402_165237.png" width="240"> |

> 同一 Prompt，两次调用，构图自然差异化 — 从中挑选最佳效果即可。

---

### 附加：批量生成不同场景

一次调用生成多张 **不同场景** 的卡片。

```python
from scripts.generate_card import generate_custom_cards_batch

paths = generate_custom_cards_batch([
    "buying tickets at attraction entrance, excited expression",
    "booking hotel at front desk, happy and satisfied",
    "renting a car, confident ready-to-go expression",
])
# 返回: [path1, path2, path3]，顺序与输入一致，失败项自动跳过
```

```bash
python -m scripts.generate_card --custom-batch \
  "买门票场景，开心的表情" \
  "在咖啡厅工作，专注的样子" \
  "海边冲浪，兴奋激动"
```

---

## 模式选择指南

| 需求 | 推荐模式 |
|------|---------|
| 生成标准技能卡（数据分析、旅游规划…） | `generate_skill_card(skill_id)` |
| 生成一个特定场景的卡片 | `generate_custom_card(scene)` |
| 同一场景要多个版本来挑选 | `generate_custom_card_variations(scene, num_variations=N)` |
| 一次生成多个不同场景 | `generate_custom_cards_batch([scene1, scene2, …])` |

---

## 快速开始

```bash
# 1. 安装依赖
pip install requests pillow python-dotenv

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DOUBAO_API_KEY

# 3. 确认参考图已放入 assets/
ls assets/ip-reference.png

# 4. 生成第一张卡片
python -m scripts.generate_card data_analysis
```

输出路径：`output/cards/`

---

## 文件结构

```
skill-card-generator/
├── README.md
├── HOW_TO_RUN.md           # 详细运行指南
├── SKILL.md                # Agent 集成文档（含 YAML frontmatter）
├── .env.example            # 环境变量模板
├── scripts/
│   ├── generate_card.py    # 主入口，Agent 调用此文件
│   └── prompt_builder.py   # Prompt 组装逻辑
├── assets/
│   ├── ip-reference.png    # IP 参考图（必须）
│   ├── skill-config.json   # 12 种预设技能配置
│   └── prompt-template.txt
├── references/
│   └── api-guide.md        # Doubao API 接入文档
└── output/
    └── cards/              # 生成结果存放目录
```

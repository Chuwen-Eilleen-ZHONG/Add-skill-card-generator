"""
prompt_builder.py
─────────────────
Assembles image-to-image prompts from skill configuration.

CRITICAL DESIGN RULE:
    This module NEVER describes the mascot's base appearance (no "white puppy",
    "dog", "fluffy fur", "pink tuft", "ear", etc.). The reference image
    (ip-reference.png) carries all character appearance information, including
    the distinctive pink curly tuft on the right side of the head (a signature
    asymmetric feature). Prompts here only describe:
        1. Expression / emotional state
        2. Outfit / clothing / held accessories
        3. Background / environment / atmosphere
"""

import os
import json
from pathlib import Path
from typing import Optional

# ── Paths ────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
_CONFIG_PATH = _ROOT / "assets" / "skill-config.json"
_TEMPLATE_PATH = _ROOT / "assets" / "prompt-template.txt"

# ── Fixed style suffix appended to every prompt ──────────────────────────────

_STYLE_SUFFIX = (
    "CRITICAL: Character appearance must EXACTLY match the reference image. "
    "Preserve the distinctive pink curly tuft on the right side of head (not a normal ear). "
    "Only modify: expression, outfit, and background scene. "
    "Do NOT change the character's base appearance, facial features, or body structure. "
    "3D cartoon style, Pixar quality rendering, "
    "vibrant saturated colors, soft lighting, high detail, "
    "professional illustration, clean composition"
)

_NEGATIVE_PROMPT = (
    "realistic photo, human character, dark depressing mood, "
    "blurry, low quality, watermark, text overlay, letterbox, stretched"
)


# ── Config loader ─────────────────────────────────────────────────────────────

def load_skill_config() -> dict:
    """Load and return the full skill-config.json as a dict keyed by skill_id."""
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(f"skill-config.json not found at: {_CONFIG_PATH}")

    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    skills = raw.get("skills", [])
    if not skills:
        raise ValueError("skill-config.json has no entries under 'skills'")

    return {entry["skill_id"]: entry for entry in skills}


def list_skill_ids() -> list[str]:
    """Return a sorted list of all valid skill_id values."""
    config = load_skill_config()
    return sorted(config.keys())


# ── Prompt assembly ───────────────────────────────────────────────────────────

def build_prompt(skill_id: str) -> tuple[str, str]:
    """
    Build the positive and negative prompts for a given skill.

    Args:
        skill_id: Must match a key in skill-config.json.

    Returns:
        Tuple of (positive_prompt, negative_prompt).

    Raises:
        ValueError: skill_id not found in config.
    """
    config = load_skill_config()

    if skill_id not in config:
        available = ", ".join(sorted(config.keys()))
        raise ValueError(
            f"Unknown skill_id '{skill_id}'. "
            f"Available skill IDs: {available}"
        )

    skill = config[skill_id]

    # ── Build positive prompt ─────────────────────────────────────────────────
    # Order: expression → outfit → background → style
    # NO mascot base appearance description anywhere.
    parts = [
        skill["expression"],
        skill["outfit"],
        skill["background"],
        _STYLE_SUFFIX,
    ]
    positive = ", ".join(part.strip().rstrip(",") for part in parts if part.strip())

    return positive, _NEGATIVE_PROMPT


def build_prompt_from_template(skill_id: str) -> tuple[str, str]:
    """
    Build prompts using the prompt-template.txt file as the base structure.
    Falls back to build_prompt() if template is missing.

    Args:
        skill_id: Must match a key in skill-config.json.

    Returns:
        Tuple of (positive_prompt, negative_prompt).
    """
    if not _TEMPLATE_PATH.exists():
        return build_prompt(skill_id)

    config = load_skill_config()

    if skill_id not in config:
        available = ", ".join(sorted(config.keys()))
        raise ValueError(
            f"Unknown skill_id '{skill_id}'. Available: {available}"
        )

    skill = config[skill_id]

    with open(_TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Strip comment lines (lines starting with #)
    lines = [
        line for line in template.splitlines()
        if not line.strip().startswith("#")
    ]
    template_clean = "\n".join(lines).strip()

    positive = template_clean.format(
        expression=skill["expression"],
        outfit=skill["outfit"],
        background=skill["background"],
    ).strip().strip(",")

    return positive, _NEGATIVE_PROMPT


def get_skill_metadata(skill_id: str) -> dict:
    """
    Return full metadata for a skill (for logging, display, or tagging).

    Args:
        skill_id: Must match a key in skill-config.json.

    Returns:
        Dict with skill_id, name_cn, name_en, expression, outfit, background, mood.
    """
    config = load_skill_config()
    if skill_id not in config:
        raise ValueError(f"Unknown skill_id '{skill_id}'")
    return config[skill_id]


# ── CLI utility ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prompt_builder.py <skill_id>")
        print(f"Available: {', '.join(list_skill_ids())}")
        sys.exit(0)

    sid = sys.argv[1]
    try:
        pos, neg = build_prompt(sid)
        print("=== POSITIVE PROMPT ===")
        print(pos)
        print("\n=== NEGATIVE PROMPT ===")
        print(neg)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

"""
generate_card.py
────────────────
Main entry point for AI Agent calls.

USAGE (from Agent):
    from scripts.generate_card import generate_skill_card, generate_custom_card, list_available_skills

    # Predefined skill (uses skill-config.json)
    image_path = generate_skill_card("data_analysis")
    image_path = generate_skill_card("travel_planning", output_path="/out/travel.png")
    skills     = list_available_skills()

    # Free-form scene — ANY description, no predefined skill needed
    image_path = generate_custom_card("buying tickets at a theme park, excited expression")
    image_path = generate_custom_card("门票预订场景，小狗在售票处前开心地拿着门票")

    # Batch — multiple different scenes in one call
    paths = generate_custom_cards_batch(["scene 1", "scene 2", "scene 3"])

    # Variations — multiple versions of the SAME scene (pick the best one)
    paths = generate_custom_card_variations("scene description", num_variations=5)

CRITICAL DESIGN RULE:
    ip-reference.png is ALWAYS submitted as the input image to the API.
    The prompt NEVER describes the mascot's base appearance — the reference
    image is the sole source of character consistency.
"""

import os
import base64
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.prompt_builder import (
    build_prompt, list_skill_ids, get_skill_metadata, _STYLE_SUFFIX,
)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger("skill-card-generator")

# ── Paths ─────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
_REFERENCE_IMAGE = _ROOT / "assets" / "ip-reference.png"
_DEFAULT_OUTPUT_DIR = _ROOT / "output" / "cards"


# ── Environment validation ────────────────────────────────────────────────────

def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            f"Set it before calling generate_skill_card()."
        )
    return value


def _load_env() -> dict:
    """Load and validate all required environment variables."""
    # Support .env file via python-dotenv if available
    try:
        from dotenv import load_dotenv
        env_file = _ROOT / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded environment from {env_file}")
    except ImportError:
        pass  # dotenv optional; env vars may be set at system level

    return {
        "api_key": _require_env("DOUBAO_API_KEY"),
        "endpoint": _require_env("DOUBAO_ENDPOINT"),
        "model": _require_env("DOUBAO_MODEL"),
    }


# ── Reference image loader ────────────────────────────────────────────────────

def _load_reference_image() -> bytes:
    """Load ip-reference.png as raw bytes."""
    if not _REFERENCE_IMAGE.exists():
        raise FileNotFoundError(
            f"Reference image not found: {_REFERENCE_IMAGE}\n"
            f"Please upload ip-reference.png to the assets/ directory."
        )
    with open(_REFERENCE_IMAGE, "rb") as f:
        return f.read()


def _encode_reference_image() -> str:
    """Return ip-reference.png as a base64-encoded string (for APIs that need it)."""
    return base64.b64encode(_load_reference_image()).decode("utf-8")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _scene_slug(scene_description: str, max_chars: int = 20) -> str:
    """
    Derive a short filesystem-safe slug from a scene description.
    Used to make variation filenames self-descriptive.
    E.g. "buying tickets at theme park" → "buying_tickets_at"
    """
    import re
    slug = scene_description.strip().lower()
    slug = re.sub(r"[^\w\s]", "", slug)       # strip punctuation
    slug = re.sub(r"\s+", "_", slug)           # spaces → underscores
    slug = re.sub(r"[^\x00-\x7f]", "", slug)  # drop non-ASCII (Chinese chars etc.)
    slug = slug.strip("_")
    return slug[:max_chars].rstrip("_") or "custom"


# ── Output path resolver ──────────────────────────────────────────────────────

def _resolve_output_path(prefix: str, output_path: Optional[str]) -> Path:
    """Determine and create the output file path.

    Args:
        prefix: Filename prefix used when output_path is not given (e.g. skill_id or "custom").
        output_path: Caller-supplied path, or None for auto-generation.
    """
    if output_path:
        path = Path(output_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        _DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = _DEFAULT_OUTPUT_DIR / f"{prefix}_{timestamp}.png"

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


# ── Doubao API call ───────────────────────────────────────────────────────────

def _call_doubao_api(
    env: dict,
    reference_image_bytes: bytes,
    positive_prompt: str,
    negative_prompt: str,
) -> bytes:
    """
    Call the Doubao image-to-image API and return raw PNG bytes.

    Sends ip-reference.png as a base64 data URI alongside the prompt.
    Requests 1024*1024 square output via the size parameter (not via prompt text).
    negative_prompt is accepted by this function for interface consistency but
    is not forwarded to the API — Doubao handles negative guidance internally.

    Args:
        env: Dict with api_key, endpoint, model.
        reference_image_bytes: Raw bytes of ip-reference.png.
        positive_prompt: Assembled prompt (expression + outfit + background + style).
        negative_prompt: Ignored — Doubao API does not accept this parameter.

    Returns:
        Raw bytes of the generated PNG image.

    Raises:
        RuntimeError: API call failed or response has unexpected shape.
    """
    import requests

    # Encode reference image as a base64 data URI
    reference_base64 = base64.b64encode(reference_image_bytes).decode("utf-8")
    reference_data_uri = f"data:image/png;base64,{reference_base64}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {env['api_key']}",
    }

    payload = {
        "model": env["model"],
        "prompt": positive_prompt,
        "image": reference_data_uri,
        "sequential_image_generation": "disabled",
        "response_format": "url",       # API returns a URL; we download below
        "size": "1920x1920",            # CRITICAL: 1:1 square; min 3,686,400px required by API
        "stream": False,
        "watermark": False,             # Clean cards — no watermark overlay
    }
    # negative_prompt is intentionally omitted: not supported by this API endpoint

    logger.info(f"Calling Doubao API: {env['endpoint']}")

    try:
        response = requests.post(
            env["endpoint"],
            headers=headers,
            json=payload,
            timeout=120,    # image generation can take time
        )
        if not response.ok:
            raise RuntimeError(
                f"Doubao API error {response.status_code}: {response.text}"
            )
        response.raise_for_status()
    except RuntimeError:
        raise
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Doubao API request failed: {e}") from e

    result = response.json()

    if "data" not in result or len(result["data"]) == 0:
        raise RuntimeError(f"Unexpected API response structure: {result}")

    image_url = result["data"][0].get("url")
    if not image_url:
        raise RuntimeError(f"No image URL in API response: {result}")

    # Download the generated image from the returned URL
    logger.info(f"Downloading generated image from: {image_url}")
    try:
        image_response = requests.get(image_url, timeout=60)
        image_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to download generated image: {e}") from e

    return image_response.content


# ── Aspect ratio validation ───────────────────────────────────────────────────

def _validate_image_aspect_ratio(image_bytes: bytes) -> None:
    """
    Verify the generated image is square (1:1 aspect ratio).

    All Skills Hub cards must be square for consistent grid display.
    Aspect ratio is enforced at the API request level (size="1024x1024"),
    but this function acts as a safety net to catch any unexpected output.

    Args:
        image_bytes: Raw bytes of the generated PNG image.

    Raises:
        ValueError: If the image width and height are not equal.
        ImportError: If Pillow is not installed (install with: pip install pillow).
    """
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes))
    width, height = img.size

    if width != height:
        raise ValueError(
            f"Generated image is not square: {width}x{height}. "
            f"Ensure the API request includes size='1024x1024' (or aspect_ratio='1:1'). "
            f"See references/api-guide.md for details."
        )

    logger.info(f"Aspect ratio check passed: {width}x{height} (1:1)")


# ── Mock mode (for testing without API credentials) ───────────────────────────

def _mock_generate(skill_id: str, output_path: Path) -> Path:
    """
    Create a placeholder PNG for testing the pipeline without API access.
    Requires Pillow. Falls back to writing an empty file if Pillow is absent.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (512, 512), color=(240, 248, 255))
        draw = ImageDraw.Draw(img)

        meta = get_skill_metadata(skill_id)

        draw.rectangle([20, 20, 492, 492], outline=(100, 149, 237), width=4)
        draw.text((256, 200), "[MOCK CARD]", fill=(100, 149, 237), anchor="mm")
        draw.text((256, 256), meta["name_en"], fill=(50, 50, 80), anchor="mm")
        draw.text((256, 300), meta["name_cn"], fill=(50, 50, 80), anchor="mm")
        draw.text((256, 356), f"ID: {skill_id}", fill=(150, 150, 180), anchor="mm")

        img.save(output_path, "PNG")
        logger.info(f"[MOCK] Placeholder card saved: {output_path}")

    except ImportError:
        # Pillow not installed — write a zero-byte file as a path placeholder
        output_path.write_bytes(b"")
        logger.warning(f"[MOCK] Pillow not installed. Empty placeholder: {output_path}")

    return output_path


# ── Public API ────────────────────────────────────────────────────────────────

def generate_skill_card(skill_id: str, output_path: Optional[str] = None) -> str:
    """
    Generate a skill card image for the given skill ID.

    Uses ip-reference.png as the base image for the Doubao image-to-image API.
    The mascot's appearance is preserved entirely from the reference image;
    only expression, outfit, and background are described in the prompt.

    Args:
        skill_id:    Skill identifier (e.g. "data_analysis", "travel_planning").
                     Must match an entry in assets/skill-config.json.
        output_path: Optional output file path. Auto-generated with timestamp
                     under output/cards/ if not provided.

    Returns:
        Absolute path (str) to the generated PNG image file.

    Raises:
        ValueError:        skill_id not found in skill-config.json.
        FileNotFoundError: ip-reference.png missing from assets/.
        EnvironmentError:  Required env vars (DOUBAO_API_KEY, etc.) not set.
        RuntimeError:      Doubao API call failed.
    """
    logger.info(f"Generating card for skill: '{skill_id}'")

    # ── 1. Build prompt ───────────────────────────────────────────────────────
    positive_prompt, negative_prompt = build_prompt(skill_id)
    logger.info(f"Prompt built: {positive_prompt[:80]}...")

    # ── 2. Resolve output path ────────────────────────────────────────────────
    resolved_output = _resolve_output_path(skill_id, output_path)

    # ── 3. Load environment ───────────────────────────────────────────────────
    try:
        env = _load_env()
    except EnvironmentError:
        # In development/testing, fall back to mock mode
        logger.warning("Env vars not set — running in MOCK mode.")
        return str(_mock_generate(skill_id, resolved_output))

    # ── 4. Load reference image ───────────────────────────────────────────────
    reference_bytes = _load_reference_image()
    logger.info(f"Reference image loaded: {_REFERENCE_IMAGE} ({len(reference_bytes)} bytes)")

    # ── 5. Call API ───────────────────────────────────────────────────────────
    try:
        image_bytes = _call_doubao_api(
            env=env,
            reference_image_bytes=reference_bytes,
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
        )
    except Exception as e:
        raise RuntimeError(f"Doubao API call failed for skill '{skill_id}': {e}") from e

    # ── 6. Validate aspect ratio ──────────────────────────────────────────────
    try:
        _validate_image_aspect_ratio(image_bytes)
    except ImportError:
        logger.warning("Pillow not installed — skipping aspect ratio check.")

    # ── 7. Save output ────────────────────────────────────────────────────────
    resolved_output.write_bytes(image_bytes)
    logger.info(f"Card saved: {resolved_output}")

    return str(resolved_output.resolve())


def generate_custom_card(
    scene_description: str,
    output_path: Optional[str] = None,
) -> str:
    """
    Generate a card from any free-form natural language scene description.

    No predefined skill required. The Agent can describe ANY scene; this
    function passes it directly to the API alongside the reference image.
    The style suffix is appended automatically — do NOT include style
    directives in scene_description.

    ip-reference.png is always used as the visual base. Do NOT describe the
    mascot's appearance in scene_description; only describe what changes
    (expression, outfit, background, props, mood, etc.).

    Args:
        scene_description: Any natural language description of the desired scene.
                           Accepts English, Chinese, or mixed.
                           Examples:
                             "buying tickets at a theme park, excited expression"
                             "门票预订场景，小狗在售票处前开心地拿着门票"
                             "cooking pasta in a cozy kitchen, happy and focused"
                             "playing guitar on a stage with spotlights, cool rock star vibe"
        output_path: Optional output file path. Auto-generated as
                     custom_YYYYMMDD_HHMMSS.png if not provided.

    Returns:
        Absolute path (str) to the generated PNG image file.

    Raises:
        ValueError:        scene_description is empty.
        FileNotFoundError: ip-reference.png missing from assets/.
        EnvironmentError:  Required env vars (DOUBAO_API_KEY, etc.) not set.
        RuntimeError:      Doubao API call failed.
    """
    scene_description = scene_description.strip()
    if not scene_description:
        raise ValueError("scene_description must not be empty.")

    logger.info(f"Generating custom card for scene: '{scene_description[:80]}...'")

    # Append style suffix — same quality directives as predefined skills
    positive_prompt = f"{scene_description}, {_STYLE_SUFFIX}"

    # ── Resolve output path ───────────────────────────────────────────────────
    resolved_output = _resolve_output_path("custom", output_path)

    # ── Load environment ──────────────────────────────────────────────────────
    try:
        env = _load_env()
    except EnvironmentError:
        logger.warning("Env vars not set — running in MOCK mode.")
        # Mock: write a simple placeholder image
        try:
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (512, 512), color=(255, 248, 240))
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 20, 492, 492], outline=(237, 149, 100), width=4)
            draw.text((256, 220), "[MOCK CUSTOM CARD]", fill=(237, 149, 100), anchor="mm")
            draw.text((256, 280), scene_description[:40], fill=(80, 50, 50), anchor="mm")
            img.save(resolved_output, "PNG")
            logger.info(f"[MOCK] Placeholder saved: {resolved_output}")
        except ImportError:
            resolved_output.write_bytes(b"")
            logger.warning(f"[MOCK] Pillow not installed. Empty placeholder: {resolved_output}")
        return str(resolved_output.resolve())

    # ── Load reference image ──────────────────────────────────────────────────
    reference_bytes = _load_reference_image()
    logger.info(f"Reference image loaded: {_REFERENCE_IMAGE} ({len(reference_bytes)} bytes)")

    # ── Call API ──────────────────────────────────────────────────────────────
    try:
        image_bytes = _call_doubao_api(
            env=env,
            reference_image_bytes=reference_bytes,
            positive_prompt=positive_prompt,
            negative_prompt="",     # not used by Doubao API
        )
    except Exception as e:
        raise RuntimeError(f"Doubao API call failed for custom scene: {e}") from e

    # ── Validate aspect ratio ─────────────────────────────────────────────────
    try:
        _validate_image_aspect_ratio(image_bytes)
    except ImportError:
        logger.warning("Pillow not installed — skipping aspect ratio check.")

    # ── Save output ───────────────────────────────────────────────────────────
    resolved_output.write_bytes(image_bytes)
    logger.info(f"Card saved: {resolved_output}")

    return str(resolved_output.resolve())


def generate_custom_cards_batch(
    scene_descriptions: list[str],
    output_dir: Optional[str] = None,
) -> list[str]:
    """
    Generate multiple custom cards in one batch call.

    Iterates through scene_descriptions, calling generate_custom_card() for each.
    Failures are logged and skipped — the batch continues regardless. The returned
    list preserves input order; failed entries are omitted.

    Args:
        scene_descriptions: List of free-form scene descriptions. Each entry
                            produces one card. No length limit.
                            Example:
                              ["买门票场景，开心的表情",
                               "在咖啡厅工作，专注的样子",
                               "海边冲浪，兴奋激动"]
        output_dir: Directory for all output images. Defaults to output/cards/.
                    Individual filenames are auto-generated with timestamps.

    Returns:
        List of absolute paths (str) to successfully generated images,
        in the same order as the input list. Failed items are excluded.

    Raises:
        ValueError: scene_descriptions is empty or not a list.
    """
    if not isinstance(scene_descriptions, list) or len(scene_descriptions) == 0:
        raise ValueError("scene_descriptions must be a non-empty list of strings.")

    total = len(scene_descriptions)
    logger.info(f"Starting batch generation: {total} card(s)")

    results: list[str] = []

    for i, scene in enumerate(scene_descriptions, start=1):
        logger.info(f"Generating card {i}/{total}: '{scene[:60]}...' " if len(scene) > 60 else f"Generating card {i}/{total}: '{scene}'")

        # Build output path inside the requested directory if given
        out_path = None
        if output_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = str(Path(output_dir) / f"custom_batch_{i:03d}_{timestamp}.png")

        try:
            path = generate_custom_card(scene, output_path=out_path)
            results.append(path)
            logger.info(f"Card {i}/{total} saved: {path}")
        except Exception as e:
            logger.error(f"Card {i}/{total} failed — skipping. Reason: {e}")

        # Brief pause between calls to avoid rate limiting (skip after last item)
        if i < total:
            time.sleep(2)

    logger.info(f"Batch complete: {len(results)}/{total} card(s) generated successfully.")
    return results


def generate_custom_card_variations(
    scene_description: str,
    num_variations: int = 1,
    output_dir: Optional[str] = None,
) -> list[str]:
    """
    Generate multiple variations of the SAME scene description.

    Even with identical prompts the API produces different compositions,
    lighting, and poses each time — giving you options to pick the best one.

    Note: Each variation costs approx. ¥0.22.
          5 variations ≈ ¥1.10 | 10 variations ≈ ¥2.20

    Args:
        scene_description: Single scene description, reused for every variation.
        num_variations:    How many versions to generate (default: 1, no upper limit).
        output_dir:        Directory for output files. Defaults to output/cards/.

    Returns:
        List of absolute paths (str) to successfully generated images,
        ordered v1 → vN. Failed variations are excluded (logged as errors).

    Raises:
        ValueError: scene_description is empty or num_variations < 1.

    Examples:
        # 5 different takes on the same scene
        paths = generate_custom_card_variations(
            "buying tickets at theme park entrance, excited expression",
            num_variations=5
        )
        # → ["…/custom_buying_tickets_at_v1_….png",
        #    "…/custom_buying_tickets_at_v2_….png", ...]

        # 3 versions in Chinese
        paths = generate_custom_card_variations("在咖啡厅工作", num_variations=3)

        # 10 options for art direction review
        paths = generate_custom_card_variations(
            scene_description="cooking pasta in kitchen",
            num_variations=10,
        )
    """
    scene_description = scene_description.strip()
    if not scene_description:
        raise ValueError("scene_description must not be empty.")
    if num_variations < 1:
        raise ValueError(f"num_variations must be >= 1, got {num_variations}.")

    slug = _scene_slug(scene_description)
    base_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    base_dir.mkdir(parents=True, exist_ok=True)

    estimated_cost = num_variations * 0.22
    logger.info(
        f"Starting variation generation: {num_variations} variation(s) of '{scene_description[:60]}' "
        f"(estimated cost: ¥{estimated_cost:.2f})"
    )

    results: list[str] = []

    for i in range(1, num_variations + 1):
        logger.info(f"Generating variation {i}/{num_variations}")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = str(base_dir / f"custom_{slug}_v{i}_{timestamp}.png")

        try:
            path = generate_custom_card(scene_description, output_path=out_path)
            results.append(path)
            logger.info(f"Variation {i}/{num_variations} saved: {path}")
        except Exception as e:
            logger.error(f"Variation {i}/{num_variations} failed — skipping. Reason: {e}")

        if i < num_variations:
            time.sleep(2)

    logger.info(
        f"Variations complete: {len(results)}/{num_variations} generated successfully."
    )
    return results


def list_available_skills() -> list[str]:
    """
    Return a sorted list of all valid skill_id values from skill-config.json.

    Returns:
        List of skill ID strings.
    """
    return list_skill_ids()


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    def _print_usage():
        print("Usage:")
        print("  Predefined skill:  python generate_card.py <skill_id> [output_path]")
        print("  Free-form scene:   python generate_card.py --custom \"<scene>\" [output_path]")
        print("  Batch scenes:      python generate_card.py --custom-batch \"scene1\" \"scene2\" ...")
        print("  Variations:        python generate_card.py --variations <N> \"<scene>\"")
        print(f"\nAvailable skill IDs:\n  " + "\n  ".join(list_available_skills()))

    if len(sys.argv) < 2:
        _print_usage()
        sys.exit(0)

    try:
        if sys.argv[1] == "--variations":
            if len(sys.argv) < 4:
                print("Error: --variations requires a count and a scene description.")
                print('  Example: python generate_card.py --variations 5 "buying tickets at theme park"')
                sys.exit(1)
            try:
                n = int(sys.argv[2])
            except ValueError:
                print(f"Error: variation count must be an integer, got '{sys.argv[2]}'")
                sys.exit(1)
            scene = sys.argv[3]
            out_dir = sys.argv[4] if len(sys.argv) > 4 else None
            paths = generate_custom_card_variations(scene, num_variations=n, output_dir=out_dir)
            print(f"Variations complete: {len(paths)}/{n} generated")
            for p in paths:
                print(f"  {p}")

        elif sys.argv[1] == "--custom-batch":
            scenes = sys.argv[2:]
            if not scenes:
                print("Error: --custom-batch requires at least one scene description.")
                print('  Example: python generate_card.py --custom-batch "scene 1" "scene 2"')
                sys.exit(1)
            paths = generate_custom_cards_batch(scenes)
            print(f"Batch complete: {len(paths)}/{len(scenes)} generated")
            for p in paths:
                print(f"  {p}")

        elif sys.argv[1] == "--custom":
            if len(sys.argv) < 3:
                print("Error: --custom requires a scene description argument.")
                print('  Example: python generate_card.py --custom "excited puppy at amusement park"')
                sys.exit(1)
            scene = sys.argv[2]
            out = sys.argv[3] if len(sys.argv) > 3 else None
            result = generate_custom_card(scene, out)
            print(f"Generated: {result}")

        else:
            sid = sys.argv[1]
            out = sys.argv[2] if len(sys.argv) > 2 else None
            result = generate_skill_card(sid, out)
            print(f"Generated: {result}")

    except (ValueError, FileNotFoundError, EnvironmentError, RuntimeError) as e:
        print(f"Error: {e}")
        sys.exit(1)

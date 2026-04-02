# Doubao API Integration Guide

Reference documentation for the Doubao image-to-image API used by `scripts/generate_card.py`.

---

## Environment Variables

| Variable | Value |
|----------|-------|
| `DOUBAO_API_KEY` | Your Bearer token (see `.env` at project root) |
| `DOUBAO_ENDPOINT` | `https://ark.cn-beijing.volces.com/api/v3/images/generations` |
| `DOUBAO_MODEL` | `doubao-seedream-5-0-260128` |

Set via `.env` file at project root. **Never commit `.env` to version control.**

---

## Image-to-Image Request

### Request Format

JSON body with base64 data URI for the reference image. The reference image is passed as a `data:image/png;base64,...` string in the `image` field.

```python
import requests
import base64

reference_base64 = base64.b64encode(reference_image_bytes).decode("utf-8")
reference_data_uri = f"data:image/png;base64,{reference_base64}"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {api_key}",
}

payload = {
    "model": "doubao-seedream-5-0-260128",
    "prompt": positive_prompt,
    "image": reference_data_uri,
    "sequential_image_generation": "disabled",
    "response_format": "url",       # API returns a URL; download separately
    "size": "1024x1024",            # CRITICAL: 1:1 square — note asterisk, not 'x'
    "stream": False,
    "watermark": False,             # Set False for clean cards without watermark
}
# negative_prompt: NOT supported by this API — omit it entirely

response = requests.post(endpoint, headers=headers, json=payload, timeout=120)
response.raise_for_status()
```

> **Note on `size` format:** This API uses an asterisk: `"1024x1024"`, not `"1024x1024"`.

> **Note on `negative_prompt`:** This API does **not** accept a `negative_prompt` field. Negative guidance is handled internally by the model. Sending it will cause a 400 error.

> **Note on `watermark`:** Set to `False` for clean card output. Default behavior may overlay a watermark.

---

## Response Parsing

```python
result = response.json()

if "data" not in result or len(result["data"]) == 0:
    raise RuntimeError(f"Unexpected response: {result}")

image_url = result["data"][0]["url"]

# Download the image from the returned URL
image_bytes = requests.get(image_url, timeout=60).content
```

Response shape:
```json
{
  "data": [
    { "url": "https://..." }
  ]
}
```

---

## Output Size — Square Format (REQUIRED)

All Skills Hub cards **must** be 1:1 square. This is enforced at the API request level via a size parameter — **not** in the text prompt. Including aspect ratio instructions in the prompt text is unreliable; always use the dedicated API parameter.

### How to request square output

```python
# Most Doubao / Volcengine APIs accept a `size` string:
"size": "1024x1024"

# Some APIs use a separate aspect_ratio field instead:
"aspect_ratio": "1:1"
```

Add the appropriate field to your request payload (Option A or B above).

### Why 1024×1024?

- Consistent display in the Skills Hub card grid (all cards same dimensions)
- High enough resolution for crisp rendering at typical display sizes
- Standard square size supported by most diffusion model APIs

### Validation

After receiving the API response, call `_validate_image_aspect_ratio(image_bytes)` before saving. This acts as a safety net in case the API ignores the size parameter or returns an unexpected crop:

```python
from scripts.generate_card import _validate_image_aspect_ratio

_validate_image_aspect_ratio(image_bytes)  # raises ValueError if not square
```

---

## Request Parameters Reference

| Parameter | Value | Notes |
|-----------|-------|-------|
| `model` | `doubao-seedream-5-0-260128` | Current production model |
| `size` | `"1024x1024"` | **Required** — asterisk separator, not `x` |
| `response_format` | `"url"` | API returns image URL; download separately |
| `watermark` | `false` | Clean output without overlay |
| `stream` | `false` | Synchronous response |
| `sequential_image_generation` | `"disabled"` | Single image output |
| `negative_prompt` | — | **Not supported** — omit this field entirely |

**For character consistency**: the `image` field (reference image) anchors the mascot appearance. The model uses it as the visual base; the `prompt` only describes what changes.

---

## Preserving IP Character Features

The reference image (`ip-reference.png`) contains critical brand features:
- **Pink curly tuft on RIGHT side of head** (replaces normal ear — asymmetric design)
- Normal ear on LEFT side
- Overall character design and proportions

**Important:** The prompt should NEVER describe these base features.
Only describe what changes: expression, clothing, accessories, background.

Example:
```
WRONG: "white fluffy dog with pink tuft, excited expression..."
RIGHT: "excited expression, wearing explorer vest, in front of mountain..."
```

The image-to-image API will preserve the character from the reference automatically.

---

## Error Codes

| HTTP Status | Meaning | Action |
|-------------|---------|--------|
| `401` | Invalid API key | Check `DOUBAO_API_KEY` |
| `400` | Bad request | Check prompt length, image format |
| `429` | Rate limit | Add retry with exponential backoff |
| `500` | Server error | Retry after delay |

---

## Official Documentation

- Volcengine / Doubao API docs: check your account dashboard for the latest endpoint and parameter reference.
- Model `seedream-5.0-lite` supports image-to-image generation with a reference image input.

---

## Quick Test

Set credentials in a `.env` file at the project root (see `.env.example`), then:

```bash
cd skill-card-generator
python scripts/generate_card.py data_analysis
```

Expected output:
```
INFO | Generating card for skill: 'data_analysis'
INFO | Prompt built: focused and analytical, wearing smart glasses, wearing a white ...
INFO | Reference image loaded: .../assets/ip-reference.png (XXXXX bytes)
INFO | Calling Doubao API: https://ark.cn-beijing.volces.com/api/v3/images/generations
INFO | Downloading generated image from: https://...
INFO | Aspect ratio check passed: 1024x1024 (1:1)
INFO | Card saved: .../output/cards/data_analysis_20260402_153021.png
Generated: /absolute/path/to/output/cards/data_analysis_20260402_153021.png
```

"""Pure protocol helpers for the MAGI-2 (Sand.ai) video generation channel.

This module is intentionally free of ComfyUI / aiohttp imports so the request
contract ported from the Java ``Sand*`` classes can be tested in isolation.
"""

from urllib.parse import urlparse


MAGI_MODEL = "magi-2"
MAGI_DEFAULT_ENDPOINT = "https://api.sand.ai"

MAGI_DEFAULT_DURATION = 5
MAGI_MIN_DURATION = 4
MAGI_MAX_DURATION = 30
MAGI_DEFAULT_ASPECT_RATIO = "16:9"
MAGI_ASPECT_RATIOS = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
MAGI_RESOLUTION = "1080p"
MAGI_MAX_PROMPT_CODE_POINTS = 15000

MAGI_MATERIAL_MODE_URL = "public_url"
MAGI_MATERIAL_MODE_ASSET_ID = "asset_id"
MAGI_MATERIAL_MODES = (MAGI_MATERIAL_MODE_URL, MAGI_MATERIAL_MODE_ASSET_ID)

MAGI_CREATE_PATH = "/v2/generations"
MAGI_QUERY_PATH = "/v2/generations/{task_id}"
MAGI_ASSET_UPLOAD_PATH = "/v1/assets"

MAGI_STATE_QUEUEING = "QUEUEING"
MAGI_STATE_PROCESSING = "PROCESSING"
MAGI_STATE_SUCCESS = "SUCCESS"
MAGI_STATE_FAIL = "FAIL"

_STATE_MAP = {
    "queued": MAGI_STATE_QUEUEING,
    "pending": MAGI_STATE_QUEUEING,
    "processing": MAGI_STATE_PROCESSING,
    "running": MAGI_STATE_PROCESSING,
    "succeeded": MAGI_STATE_SUCCESS,
    "success": MAGI_STATE_SUCCESS,
    "failed": MAGI_STATE_FAIL,
    "canceled": MAGI_STATE_FAIL,
}


class MagiProtocolError(ValueError):
    """Raised when a request cannot be built from the supplied values."""


def join_endpoint(endpoint: str, path: str) -> str:
    base = str(endpoint or "").strip()
    while base.endswith("/"):
        base = base[:-1]
    return base + path


def build_headers(api_key: str) -> dict:
    key = str(api_key or "").strip()
    if not key:
        raise MagiProtocolError("MAGI-2 API Key is required")
    authorization = key if key.startswith("Bearer ") else f"Bearer {key}"
    return {
        "Authorization": authorization,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }


def normalize_duration(duration) -> int:
    try:
        value = int(duration)
    except (TypeError, ValueError):
        return MAGI_DEFAULT_DURATION
    if value < MAGI_MIN_DURATION or value > MAGI_MAX_DURATION:
        return MAGI_DEFAULT_DURATION
    return value


def normalize_aspect_ratio(aspect_ratio) -> str:
    value = str(aspect_ratio or "").strip()
    if value in MAGI_ASPECT_RATIOS:
        return value
    return MAGI_DEFAULT_ASPECT_RATIO


def normalize_resolution(resolution) -> str:
    value = str(resolution or "").strip()
    return MAGI_RESOLUTION if value in ("", MAGI_RESOLUTION) else MAGI_RESOLUTION


def normalize_material_mode(mode) -> str:
    value = str(mode or "").strip()
    if value in MAGI_MATERIAL_MODES:
        return value
    return MAGI_MATERIAL_MODE_URL


def split_reference_lines(value) -> list:
    """Split a multiline UI input into ordered non-empty reference strings."""
    if isinstance(value, (list, tuple)):
        raw_items = list(value)
    else:
        raw_items = str(value or "").splitlines()
    return [str(item).strip() for item in raw_items if str(item or "").strip()]


def truncate_prompt(prompt: str) -> str:
    text = str(prompt or "")
    if len(text) <= MAGI_MAX_PROMPT_CODE_POINTS:
        return text
    return text[:MAGI_MAX_PROMPT_CODE_POINTS]


def validate_public_url(value, kind: str) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise MagiProtocolError(f"{kind} requires a public HTTP(S) URL")
    return url


def validate_asset_id(value, kind: str) -> str:
    asset_id = str(value or "").strip()
    if not asset_id.isdigit():
        raise MagiProtocolError(f"{kind} requires a numeric assetId")
    return asset_id


def build_material_ref(value, mode: str, kind: str) -> dict:
    material_mode = normalize_material_mode(mode)
    if material_mode == MAGI_MATERIAL_MODE_ASSET_ID:
        return {"assetId": validate_asset_id(value, kind)}
    return {"url": validate_public_url(value, kind)}


def build_parts(
    prompt: str,
    images=None,
    videos=None,
    audios=None,
    material_mode=MAGI_MATERIAL_MODE_URL,
) -> list:
    parts = [{"type": "text", "text": truncate_prompt(prompt)}]
    for kind, values, part_type, field in (
        ("reference image", images, "reference_image", "image"),
        ("reference video", videos, "reference_video", "video"),
        ("reference audio", audios, "reference_audio", "audio"),
    ):
        for value in values or []:
            if value is None or str(value).strip() == "":
                continue
            parts.append(
                {
                    "type": part_type,
                    field: build_material_ref(value, material_mode, kind),
                }
            )
    return parts


def build_generation_payload(
    prompt: str,
    images=None,
    videos=None,
    audios=None,
    duration=5,
    aspect_ratio="16:9",
    resolution="1080p",
    material_mode=MAGI_MATERIAL_MODE_URL,
    model=MAGI_MODEL,
) -> dict:
    """Build the exact body of POST /v2/generations used by the Java channel."""
    return {
        "model": str(model or MAGI_MODEL),
        "parts": build_parts(prompt, images, videos, audios, material_mode),
        "duration": normalize_duration(duration),
        "aspectRatio": normalize_aspect_ratio(aspect_ratio),
        "resolution": normalize_resolution(resolution),
    }


def extract_task_id(payload) -> str:
    if not isinstance(payload, dict):
        raise MagiProtocolError("MAGI-2 create task response is not an object")
    task_id = payload.get("id")
    if task_id is None or str(task_id).strip() == "":
        raise MagiProtocolError("MAGI-2 did not return a generation task id")
    return str(task_id)


def map_status(status: str):
    return _STATE_MAP.get(str(status or "").strip().lower())


def extract_task_result(payload) -> dict:
    if not isinstance(payload, dict):
        return {"state": None}

    raw_status = payload.get("status")
    state = map_status(raw_status) if raw_status else None
    result = {"state": state, "status": raw_status}

    output = payload.get("output")
    if isinstance(output, dict):
        result["video_url"] = output.get("videoUrl") or None
        result["url_expires_at"] = output.get("urlExpiresAt") or None

    error = payload.get("error")
    if isinstance(error, dict):
        result["error_code"] = error.get("code") or None
        result["error_message"] = error.get("message") or None

    # The Java scheduler keeps polling when a succeeded task has no video URL yet.
    if state == MAGI_STATE_SUCCESS and not result.get("video_url"):
        result["state"] = MAGI_STATE_PROCESSING
    return result

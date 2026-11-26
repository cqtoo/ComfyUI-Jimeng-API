"""Lightweight runtime helpers for MAGI-2 nodes.

This module deliberately avoids importing the Volcengine Ark SDK so MAGI-2
remains usable when only the independent MAGI-2 channel is configured.
"""

import locale
import logging
import os
import random
import shutil
from urllib.parse import urlparse

import aiohttp
import folder_paths

from .constants import LOG_TRANSLATIONS


MAGI_CATEGORY = "JimengAI"
MAGI_LOG_PREFIX = "[MAGI-2] "

logger = logging.getLogger("JimengAI.MAGI2")


class MagiException(Exception):
    """MAGI-2 node error with ComfyUI traceback suppression metadata."""

    def __init__(self, message):
        super().__init__(message)
        self.jimeng_suppress_traceback = True


def _detect_language():
    try:
        code, _ = locale.getdefaultlocale()
        if code and code.startswith("zh"):
            return "zh"
    except Exception:
        pass
    return "en"


def get_text(key, **kwargs):
    mapping = LOG_TRANSLATIONS.get(_detect_language(), LOG_TRANSLATIONS["en"])
    message = mapping.get(key, LOG_TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return message.format(**kwargs)
        except Exception:
            pass
    return message


def log_msg(key, **kwargs):
    message = get_text(key, **kwargs)
    if message:
        logger.info(MAGI_LOG_PREFIX + str(message))


def create_white_image_tensor(width=1024, height=1024):
    import torch

    return torch.ones((1, height, width, 3), dtype=torch.float32)


async def download_video_to_temp(session, url):
    if not url:
        return None
    suffix = os.path.splitext(urlparse(url).path)[1] or ".mp4"
    temp_dir = folder_paths.get_temp_directory()
    output_dir = os.path.join(temp_dir, "MAGI2")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"MAGI2_{random.randint(1, 1000000)}{suffix}"
    path = os.path.join(output_dir, filename)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as response:
            if response.status < 200 or response.status >= 300:
                return None
            with open(path, "wb") as file:
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    file.write(chunk)
        return path
    except Exception as exc:
        log_msg("err_magi_download_failed", url=f"{url} ({exc})")
        return None


def save_to_output(src_path, filename_prefix):
    if not src_path or not os.path.exists(src_path):
        return
    try:
        output_dir = folder_paths.get_output_directory()
        full_output_folder, filename, counter, _, _ = folder_paths.get_save_image_path(
            filename_prefix, output_dir
        )
        ext = os.path.splitext(src_path)[1] or ".mp4"
        dest = os.path.join(full_output_folder, f"{filename}_{counter:05}{ext}")
        shutil.copy2(src_path, dest)
    except Exception as exc:
        log_msg("err_magi_download_failed", url=f"{src_path} ({exc})")

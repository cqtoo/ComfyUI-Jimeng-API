import asyncio
import json
import time

import aiohttp

from comfy_api.latest import io as comfy_io
from comfy_api.input_impl import VideoFromFile

from .magi_protocol import (
    MAGI_ASPECT_RATIOS,
    MAGI_CREATE_PATH,
    MAGI_DEFAULT_ASPECT_RATIO,
    MAGI_DEFAULT_ENDPOINT,
    MAGI_MATERIAL_MODES,
    MAGI_MODEL,
    MAGI_QUERY_PATH,
    MAGI_RESOLUTION,
    MAGI_STATE_FAIL,
    MAGI_STATE_SUCCESS,
    MagiProtocolError,
    build_generation_payload,
    build_headers,
    extract_task_id,
    extract_task_result,
    join_endpoint,
    split_reference_lines,
    validate_public_url,
)
from .magi_runtime import (
    MAGI_CATEGORY,
    MagiException,
    create_white_image_tensor,
    download_video_to_temp,
    get_text,
    log_msg,
    save_to_output,
)


MAGIClientType = comfy_io.Custom("MAGI_CLIENT")


class MagiClient:
    """Container passed between MAGI-2 nodes."""

    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url


class MagiAPIClient(comfy_io.ComfyNode):
    """Creates a client for the MAGI-2 (Sand.ai) video channel."""

    @classmethod
    def define_schema(cls) -> comfy_io.Schema:
        return comfy_io.Schema(
            node_id="MagiAPIClient",
            display_name="MAGI-2 API Client",
            category=MAGI_CATEGORY,
            description=(
                "Client for the MAGI-2 video channel. The default endpoint is "
                "https://api.sand.ai and can be changed. No Volcengine Ark client is used."
            ),
            inputs=[
                comfy_io.String.Input(
                    "api_key",
                    default="",
                    tooltip="MAGI-2 API Key; Bearer prefix is optional.",
                ),
                comfy_io.String.Input(
                    "base_url",
                    default=MAGI_DEFAULT_ENDPOINT,
                    tooltip=(
                        "Channel endpoint; defaults to https://api.sand.ai and can be "
                        "overridden. Corresponds to video_provider_config.endpoint "
                        "in the Java service."
                    ),
                ),
            ],
            outputs=[MAGIClientType.Output(display_name="client")],
        )

    @classmethod
    def execute(
        cls, api_key="", base_url=MAGI_DEFAULT_ENDPOINT
    ) -> comfy_io.NodeOutput:
        api_key = str(api_key or "").strip()
        base_url = str(base_url or "").strip()
        if not api_key:
            raise MagiException(get_text("err_magi_key_required"))
        if not base_url:
            raise MagiException(get_text("err_magi_endpoint_required"))
        validate_public_url(base_url, "MAGI-2 endpoint")
        return comfy_io.NodeOutput(MagiClient(api_key, base_url))


def _extract_last_frame(video_path):
    try:
        import cv2
        import numpy
        import torch

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return create_white_image_tensor()
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if frame_count <= 0:
            cap.release()
            return create_white_image_tensor()
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - 1)
        success, frame = cap.read()
        cap.release()
        if not success:
            return create_white_image_tensor()
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb.astype(numpy.float32) / 255.0)
        return tensor[None,]
    except Exception:
        return create_white_image_tensor()


class MagiVideoGenerate(comfy_io.ComfyNode):
    """Generates video with MAGI-2 using the Sand.ai v2 generations API."""

    @classmethod
    def define_schema(cls) -> comfy_io.Schema:
        return comfy_io.Schema(
            node_id="MagiVideoGenerate",
            display_name="视频生成（MAGI-2）",
            category=MAGI_CATEGORY,
            description=(
                "Generate video with MAGI-2. Mirrors the Java 星朗3.5 channel: "
                "POST /v2/generations once, then poll GET /v2/generations/{id}. "
                "Reference materials may be public URLs or pre-uploaded asset IDs."
            ),
            is_output_node=True,
            inputs=[
                MAGIClientType.Input("client"),
                comfy_io.Combo.Input("model", options=[MAGI_MODEL], default=MAGI_MODEL),
                comfy_io.String.Input(
                    "prompt",
                    multiline=True,
                    default="",
                    tooltip=(
                        "提示词素材按下方填写顺序编号：@图片1、@视频1、@音频1。"
                        "Java 渠道按 assetIndex 升序引用素材。"
                    ),
                ),
                comfy_io.Combo.Input(
                    "material_mode",
                    options=list(MAGI_MATERIAL_MODES),
                    default=MAGI_MATERIAL_MODES[0],
                    tooltip=(
                        "public_url：直接提交无需鉴权的公网 HTTP(S) 直链；"
                        "asset_id：提交已在渠道侧上传并加白审核通过的数字 assetId。"
                    ),
                ),
                comfy_io.String.Input(
                    "ref_images",
                    multiline=True,
                    default="",
                    tooltip="每行一个图片公网直链或数字 assetId，顺序对应 @图片1、@图片2...",
                ),
                comfy_io.String.Input(
                    "ref_videos",
                    multiline=True,
                    default="",
                    tooltip="每行一个视频公网直链或数字 assetId，顺序对应 @视频1、@视频2...",
                ),
                comfy_io.String.Input(
                    "ref_audios",
                    multiline=True,
                    default="",
                    tooltip="每行一个音频公网直链或数字 assetId，顺序对应 @音频1、@音频2...",
                ),
                comfy_io.Int.Input("duration", default=5, min=4, max=30),
                comfy_io.Combo.Input(
                    "aspect_ratio",
                    options=list(MAGI_ASPECT_RATIOS),
                    default=MAGI_DEFAULT_ASPECT_RATIO,
                ),
                comfy_io.Combo.Input("resolution", options=[MAGI_RESOLUTION], default=MAGI_RESOLUTION),
                comfy_io.Int.Input("generation_count", default=1, min=1, max=4),
                comfy_io.Int.Input("poll_interval", default=10, min=1, max=60),
                comfy_io.Int.Input("timeout", default=900, min=60, max=3600),
                comfy_io.String.Input("filename_prefix", default="Jimeng/Video/MAGI2"),
            ],
            hidden=[comfy_io.Hidden.unique_id, comfy_io.Hidden.prompt],
            outputs=[
                comfy_io.Video.Output(display_name="video"),
                comfy_io.Image.Output(display_name="last_frame"),
                comfy_io.String.Output(display_name="response"),
            ],
        )

    @classmethod
    async def execute(
        cls,
        client,
        model=MAGI_MODEL,
        prompt="",
        material_mode="public_url",
        ref_images=None,
        ref_videos=None,
        ref_audios=None,
        duration=5,
        aspect_ratio=MAGI_DEFAULT_ASPECT_RATIO,
        resolution=MAGI_RESOLUTION,
        generation_count=1,
        poll_interval=10,
        timeout=900,
        filename_prefix="Jimeng/Video/MAGI2",
        **kwargs,
    ) -> comfy_io.NodeOutput:
        if client is None or not getattr(client, "api_key", None):
            raise MagiException(get_text("err_magi_key_required"))
        base_url = getattr(client, "base_url", None)
        if not base_url:
            raise MagiException(get_text("err_magi_endpoint_required"))

        images = split_reference_lines(ref_images)
        videos = split_reference_lines(ref_videos)
        audios = split_reference_lines(ref_audios)

        payload = build_generation_payload(
            prompt=prompt,
            images=images,
            videos=videos,
            audios=audios,
            duration=duration,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            material_mode=material_mode,
            model=model,
        )
        headers = build_headers(client.api_key)
        create_url = join_endpoint(base_url, MAGI_CREATE_PATH)
        timeout_session = aiohttp.ClientTimeout(
            connect=120, total=None, sock_connect=120, sock_read=900
        )

        log_msg("magi_submit_start", count=generation_count, model=model)
        task_ids = []
        async with aiohttp.ClientSession(timeout=timeout_session) as session:
            for _ in range(int(generation_count)):
                try:
                    async with session.post(
                        create_url, json=payload, headers=headers
                    ) as response:
                        body = await response.text()
                        if response.status < 200 or response.status >= 300:
                            raise MagiException(
                                get_text("err_magi_submit_failed").format(
                                    code=response.status, body=body[:300]
                                )
                            )
                        task_ids.append(extract_task_id(json.loads(body)))
                except (MagiProtocolError, json.JSONDecodeError) as exc:
                    raise MagiException(
                        get_text("err_magi_submit_failed").format(
                            code="invalid response", body=str(exc)
                        )
                    )
                except aiohttp.ClientError as exc:
                    # 创建接口不幂等且无幂等键：直接与 Java 保持一致，不重试。
                    raise MagiException(
                        get_text("err_magi_submit_failed").format(
                            code="network", body=str(exc)
                        )
                    )

            log_msg("magi_task_submitted", count=len(task_ids))
            completed = {}
            pending = set(task_ids)
            deadline = time.monotonic() + int(timeout)

            while pending and time.monotonic() < deadline:
                await asyncio.sleep(int(poll_interval))
                for task_id in list(pending):
                    query_url = join_endpoint(
                        base_url, MAGI_QUERY_PATH.format(task_id=task_id)
                    )
                    try:
                        async with session.get(query_url, headers=headers) as response:
                            if response.status < 200 or response.status >= 300:
                                continue
                            task_payload = json.loads(await response.text())
                    except (aiohttp.ClientError, json.JSONDecodeError):
                        # Java 侧查询失败不落终态，下一轮继续轮询。
                        continue

                    result = extract_task_result(task_payload)
                    state = result.get("state")
                    if state == MAGI_STATE_FAIL:
                        raise MagiException(
                            get_text("err_magi_task_failed").format(
                                code=result.get("error_code") or "",
                                message=result.get("error_message") or "",
                            )
                        )
                    if state == MAGI_STATE_SUCCESS and result.get("video_url"):
                        completed[task_id] = result
                        pending.discard(task_id)

            if pending:
                raise MagiException(get_text("err_magi_poll_timeout"))

            responses = []
            video_paths = []
            for task_id in task_ids:
                result = completed.get(task_id)
                if result is None:
                    responses.append(
                        {"id": task_id, "model": model, "status": "succeeded"}
                    )
                    continue
                video_path = await download_video_to_temp(session, result["video_url"])
                if not video_path:
                    raise MagiException(
                        get_text("err_magi_download_failed").format(url=result["video_url"])
                    )
                video_paths.append(video_path)
                responses.append(
                    {
                        "id": task_id,
                        "model": model,
                        "status": "succeeded",
                        "output": {
                            "videoUrl": result["video_url"],
                            "urlExpiresAt": result.get("url_expires_at"),
                        },
                        "material_mode": material_mode,
                    }
                )

        if not video_paths:
            raise MagiException(get_text("err_magi_download_failed").format(url=""))

        first_video = VideoFromFile(video_paths[0])
        first_frame = _extract_last_frame(video_paths[0])
        for path in video_paths[1:]:
            save_to_output(path, filename_prefix)

        return comfy_io.NodeOutput(
            first_video, first_frame, json.dumps(responses, indent=2, ensure_ascii=False)
        )

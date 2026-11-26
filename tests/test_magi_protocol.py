import importlib.util
import os
import sys
import types
import unittest


PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGE_NAME = "magi_protocol_test"


def _load_magi_protocol():
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [PLUGIN_ROOT]
    sys.modules[PACKAGE_NAME] = package
    nodes_package = types.ModuleType(f"{PACKAGE_NAME}.nodes")
    nodes_package.__path__ = [os.path.join(PLUGIN_ROOT, "nodes")]
    sys.modules[f"{PACKAGE_NAME}.nodes"] = nodes_package
    return importlib.import_module(f"{PACKAGE_NAME}.nodes.magi_protocol")


magi_protocol = _load_magi_protocol()


class MagiProtocolTests(unittest.TestCase):
    def test_request_payload_matches_java_dto(self):
        payload = magi_protocol.build_generation_payload(
            "cat @图片1 @视频1 @音频1",
            images=["https://example.com/a.png"],
            videos=["https://example.com/b.mp4"],
            audios=["https://example.com/c.wav"],
            duration=9,
            aspect_ratio="21:9",
            resolution="1080p",
        )
        self.assertEqual(payload["model"], "magi-2")
        self.assertEqual(payload["duration"], 9)
        self.assertEqual(payload["aspectRatio"], "21:9")
        self.assertEqual(payload["resolution"], "1080p")
        self.assertNotIn("enhancePrompt", payload)
        self.assertEqual(
            payload["parts"],
            [
                {"type": "text", "text": "cat @图片1 @视频1 @音频1"},
                {
                    "type": "reference_image",
                    "image": {"url": "https://example.com/a.png"},
                },
                {
                    "type": "reference_video",
                    "video": {"url": "https://example.com/b.mp4"},
                },
                {
                    "type": "reference_audio",
                    "audio": {"url": "https://example.com/c.wav"},
                },
            ],
        )

    def test_asset_id_mode_uses_asset_id_field(self):
        payload = magi_protocol.build_generation_payload(
            "product",
            images=["12345", " 67890 "],
            material_mode="asset_id",
        )
        self.assertEqual(
            payload["parts"][1]["image"],
            {"assetId": "12345"},
        )
        self.assertEqual(payload["parts"][2]["image"], {"assetId": "67890"})

    def test_duration_and_aspect_ratio_fallback(self):
        self.assertEqual(magi_protocol.normalize_duration(3), 5)
        self.assertEqual(magi_protocol.normalize_duration(31), 5)
        self.assertEqual(magi_protocol.normalize_duration("abc"), 5)
        self.assertEqual(magi_protocol.normalize_duration(30), 30)
        self.assertEqual(magi_protocol.normalize_aspect_ratio("19:9"), "16:9")
        self.assertEqual(magi_protocol.normalize_aspect_ratio("9:16"), "9:16")

    def test_multiline_reference_input(self):
        self.assertEqual(
            magi_protocol.split_reference_lines(
                "https://a.example/1.png\n\n https://a.example/2.png \n"
            ),
            ["https://a.example/1.png", "https://a.example/2.png"],
        )
        self.assertEqual(
            magi_protocol.split_reference_lines(["123", " ", "456"]),
            ["123", "456"],
        )

    def test_prompt_truncation_and_url_validation(self):
        self.assertEqual(
            magi_protocol.truncate_prompt("a" * 16000),
            "a" * magi_protocol.MAGI_MAX_PROMPT_CODE_POINTS,
        )
        with self.assertRaises(Exception):
            magi_protocol.validate_public_url(
                "data:image/png;base64,AA==", "reference image"
            )
        self.assertEqual(
            magi_protocol.validate_public_url(" https://x.example/a.png ", "reference image"),
            "https://x.example/a.png",
        )
        with self.assertRaises(Exception):
            magi_protocol.validate_asset_id("abc", "reference image")

    def test_headers_and_endpoint_join(self):
        self.assertEqual(magi_protocol.MAGI_DEFAULT_ENDPOINT, "https://api.sand.ai")
        headers = magi_protocol.build_headers("Bearer abc")
        self.assertEqual(headers["Authorization"], "Bearer abc")
        self.assertEqual(
            magi_protocol.build_headers("abc")["Authorization"], "Bearer abc"
        )
        self.assertEqual(
            magi_protocol.join_endpoint("https://api.example.com/", "/v2/generations"),
            "https://api.example.com/v2/generations",
        )

    def test_task_extraction_and_status_mapping(self):
        self.assertEqual(
            magi_protocol.extract_task_id({"id": "abc"}),
            "abc",
        )
        with self.assertRaises(Exception):
            magi_protocol.extract_task_id({"data": {}})

        self.assertEqual(magi_protocol.map_status("queued"), "QUEUEING")
        self.assertEqual(magi_protocol.map_status("running"), "PROCESSING")
        self.assertEqual(magi_protocol.map_status("succeeded"), "SUCCESS")
        self.assertEqual(magi_protocol.map_status("failed"), "FAIL")

        result = magi_protocol.extract_task_result(
            {
                "status": "succeeded",
                "output": {
                    "videoUrl": "https://cdn.example.com/v.mp4",
                    "urlExpiresAt": "2026-11-27T00:00:00Z",
                },
            }
        )
        self.assertEqual(result["state"], "SUCCESS")
        self.assertEqual(result["video_url"], "https://cdn.example.com/v.mp4")

        pending = magi_protocol.extract_task_result({"status": "succeeded"})
        self.assertEqual(pending["state"], "PROCESSING")

        failed = magi_protocol.extract_task_result(
            {"status": "failed", "error": {"code": "E1", "message": "bad"}}
        )
        self.assertEqual(failed["state"], "FAIL")
        self.assertEqual(failed["error_code"], "E1")


if __name__ == "__main__":
    unittest.main()

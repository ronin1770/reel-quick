"""Manual test runner for text overlays on a final merged video."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.db import get_db, init_db
from backend.models.video_text import VIDEO_OVERLAY_TEXT_COLLECTION, VideoTextModel
from backend.objects.text_overlayer import TextOverlayer

VIDEO_ID = "e397375225c949378357ac447fbeb096"
INPUT_VIDEO_PATH = "/home/farhan/reel-quick/outputs/test_1.mp4"
# Output defaults to <input_stem>_text.mp4 when not provided.
OUTPUT_VIDEO_PATH = None


def build_overlays() -> List[Dict[str, Any]]:
    return [
        {
            "overlay_id": "txt_001",
            "text": "Hello from world",
            "start_time": 0,
            "end_time": 8,
            "position": {
                "preset": "top",
            },
            "style": {
                "text_color": "Black",
                "font_weight": "bold",
            },
        },
        {
            "overlay_id": "txt_002",
            "text": "Cruel World",
            "start_time": 9,
            "end_time": 20,
            "position": {
                "preset": "bottom",
            },
            "style": {
                "text_color": "RED",
                "font_weight": "normal",
            },
        },
    ]


def upsert_overlay_result(result_payload: Dict[str, Any]) -> Dict[str, Any]:
    model = VideoTextModel.from_response(result_payload)
    db = get_db()
    update_result = db[VIDEO_OVERLAY_TEXT_COLLECTION].update_one(
        {"video_id": model.video_id},
        model.to_upsert_update(),
        upsert=True,
    )
    return {
        "matched_count": int(update_result.matched_count),
        "modified_count": int(update_result.modified_count),
        "upserted_id": (
            str(update_result.upserted_id)
            if update_result.upserted_id is not None
            else None
        ),
    }


def main() -> int:
    init_db()

    overlays = build_overlays()
    overlayer = TextOverlayer()
    result = overlayer.apply_text_overlays(
        video_id=VIDEO_ID,
        input_video_path=INPUT_VIDEO_PATH,
        overlays=overlays,
        output_video_path=OUTPUT_VIDEO_PATH,
    )

    db_status = upsert_overlay_result(result)
    result["db_upsert"] = db_status

    print(json.dumps(result, indent=2))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    sys.exit(main())

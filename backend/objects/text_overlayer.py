"""Apply text overlays to a final video timeline using MoviePy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from moviepy import CompositeVideoClip, TextClip, VideoFileClip

from backend.logger import get_logger


class TextOverlayer:
    """Simple text overlay processor for a final video."""

    _SUPPORTED_PRESETS = {"top", "center", "bottom", "custom"}

    def __init__(self) -> None:
        self.logger = get_logger(name="instagram_reel_creation_text_overlayer")

    def apply_text_overlays(
        self,
        video_id: str,
        input_video_path: str,
        overlays: List[Dict[str, Any]],
        output_video_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        input_path = Path(input_video_path).resolve()
        resolved_output_path = (
            Path(output_video_path).resolve()
            if output_video_path
            else self._default_output_path(input_path)
        )

        try:
            self._validate_input(video_id=video_id, input_path=input_path, overlays=overlays)

            base_clip: Optional[VideoFileClip] = None
            composite_clip: Optional[CompositeVideoClip] = None
            text_clips: List[TextClip] = []
            normalized_overlays: List[Dict[str, Any]] = []

            try:
                base_clip = VideoFileClip(str(input_path))
                video_width, video_height = base_clip.size
                video_duration = float(base_clip.duration or 0.0)

                normalized_overlays = self._normalize_and_validate_overlays(
                    overlays=overlays,
                    video_duration=video_duration,
                    video_width=video_width,
                    video_height=video_height,
                )
                self._validate_no_overlaps(normalized_overlays)

                for overlay in normalized_overlays:
                    text_clip = self._create_text_clip(
                        overlay=overlay,
                        video_width=video_width,
                    )

                    x_pos, y_pos = self._resolve_position(
                        position=overlay["position"],
                        video_width=video_width,
                        video_height=video_height,
                        text_height=int(text_clip.h or 0),
                    )

                    text_clip = (
                        text_clip.with_start(overlay["start_time"])
                        .with_end(overlay["end_time"])
                        .with_position((x_pos, y_pos))
                    )

                    opacity = overlay["style"]["opacity"]
                    if opacity < 1.0:
                        text_clip = text_clip.with_opacity(opacity)

                    text_clips.append(text_clip)

                composite_clip = CompositeVideoClip(
                    [base_clip, *text_clips],
                    size=base_clip.size,
                )

                resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

                write_kwargs: Dict[str, Any] = {
                    "filename": str(resolved_output_path),
                    "codec": "libx264",
                    "fps": base_clip.fps or 30,
                    "threads": 1,
                }

                if base_clip.audio is not None:
                    write_kwargs["audio"] = True
                    write_kwargs["audio_codec"] = "aac"
                else:
                    write_kwargs["audio"] = False

                composite_clip.write_videofile(**write_kwargs)

            finally:
                if composite_clip is not None:
                    composite_clip.close()
                for clip in text_clips:
                    clip.close()
                if base_clip is not None:
                    base_clip.close()

            return self._build_response(
                video_id=video_id,
                input_video_path=str(input_path),
                output_video_path=str(resolved_output_path),
                status="success",
                message="Video processed with text overlays",
                overlays=normalized_overlays,
            )

        except Exception as exc:
            self.logger.exception(
                "Failed applying text overlays for video_id=%s: %s",
                video_id,
                str(exc),
            )
            return self._build_response(
                video_id=video_id,
                input_video_path=str(input_path),
                output_video_path=str(resolved_output_path),
                status="failed",
                message="Video processing failed",
                overlays=[],
                exception=str(exc),
            )

    def _validate_input(
        self,
        video_id: str,
        input_path: Path,
        overlays: List[Dict[str, Any]],
    ) -> None:
        if not str(video_id).strip():
            raise ValueError("video_id is required")
        if not input_path.exists():
            raise FileNotFoundError(f"input_video_path not found: {input_path}")
        if not input_path.is_file():
            raise ValueError(f"input_video_path must be a file: {input_path}")
        if not overlays:
            raise ValueError("at least one overlay is required")

    def _normalize_and_validate_overlays(
        self,
        overlays: List[Dict[str, Any]],
        video_duration: float,
        video_width: int,
        video_height: int,
    ) -> List[Dict[str, Any]]:
        normalized_overlays: List[Dict[str, Any]] = []

        for index, raw_overlay in enumerate(overlays):
            if not isinstance(raw_overlay, dict):
                raise ValueError(f"overlay at index {index} must be an object")

            self._validate_overlay_required_fields(raw_overlay, index)

            normalized = self._normalize_overlay(raw_overlay, index)

            self._validate_overlay_time_range(
                overlay=normalized,
                index=index,
                video_duration=video_duration,
            )

            self._validate_overlay_position(
                overlay=normalized,
                index=index,
                video_width=video_width,
                video_height=video_height,
            )

            normalized_overlays.append(normalized)

        return normalized_overlays

    def _validate_overlay_required_fields(
        self,
        overlay: Dict[str, Any],
        index: int,
    ) -> None:
        text = str(overlay.get("text", "")).strip()
        if not text:
            raise ValueError(f"overlay at index {index} requires non-empty text")

        if "start_time" not in overlay or "end_time" not in overlay:
            raise ValueError(
                f"overlay at index {index} requires start_time and end_time"
            )

    def _validate_overlay_time_range(
        self,
        overlay: Dict[str, Any],
        index: int,
        video_duration: float,
    ) -> None:
        start_time = overlay["start_time"]
        end_time = overlay["end_time"]

        if start_time < 0:
            raise ValueError(f"overlay at index {index} start_time must be >= 0")
        if end_time <= start_time:
            raise ValueError(f"overlay at index {index} end_time must be > start_time")
        if end_time > video_duration:
            raise ValueError(
                f"overlay at index {index} end_time exceeds video duration "
                f"{video_duration:.3f}"
            )

    def _validate_overlay_position(
        self,
        overlay: Dict[str, Any],
        index: int,
        video_width: int,
        video_height: int,
    ) -> None:
        position = overlay["position"]

        if position["preset"] != "custom":
            return

        x_pos = position["x"]
        y_pos = position["y"]

        if not isinstance(x_pos, (int, float)) or not isinstance(y_pos, (int, float)):
            raise ValueError(
                f"overlay at index {index} custom position x/y must be numeric"
            )

        if x_pos < 0 or x_pos > video_width or y_pos < 0 or y_pos > video_height:
            raise ValueError(
                f"overlay at index {index} custom x/y must be within video bounds "
                f"(0..{video_width}, 0..{video_height})"
            )

    def _validate_no_overlaps(self, overlays: List[Dict[str, Any]]) -> None:
        ordered = sorted(overlays, key=lambda item: item["start_time"])

        for index in range(1, len(ordered)):
            previous = ordered[index - 1]
            current = ordered[index]
            if current["start_time"] < previous["end_time"]:
                raise ValueError(
                    "text overlays cannot overlap: "
                    f"{previous['overlay_id']} and {current['overlay_id']}"
                )

    def _normalize_overlay(
        self,
        overlay: Dict[str, Any],
        index: int,
    ) -> Dict[str, Any]:
        style = overlay.get("style") if isinstance(overlay.get("style"), dict) else {}
        position_raw = (
            overlay.get("position") if isinstance(overlay.get("position"), dict) else {}
        )

        preset = str(position_raw.get("preset", "bottom")).strip().lower()
        if preset not in self._SUPPORTED_PRESETS:
            preset = "bottom"

        normalized: Dict[str, Any] = {
            "overlay_id": str(overlay.get("overlay_id") or f"txt_{index + 1:03d}"),
            "text": str(overlay.get("text", "")).strip(),
            "start_time": float(overlay["start_time"]),
            "end_time": float(overlay["end_time"]),
            "duration": float(overlay["end_time"]) - float(overlay["start_time"]),
            "position": {
                "preset": preset,
                "x": position_raw.get("x", "center"),
                "y": position_raw.get("y", "center"),
            },
            "style": {
                "font_family": str(style.get("font_family") or "Arial"),
                "font_size": int(style.get("font_size", 48)),
                "font_weight": str(style.get("font_weight") or "normal"),
                "text_color": str(style.get("text_color") or "#FFFFFF"),
                "stroke_color": str(style.get("stroke_color") or "#000000"),
                "stroke_width": int(style.get("stroke_width", 2)),
                "background_color": style.get("background_color"),
                "opacity": float(style.get("opacity", 1.0)),
                "text_box_width_ratio": float(style.get("text_box_width_ratio", 0.9)),
                "margin_x": int(style.get("margin_x", 24)),
                "margin_y": int(style.get("margin_y", 18)),
            },
        }

        if normalized["style"]["font_size"] <= 0:
            raise ValueError(f"overlay at index {index} font_size must be > 0")

        if normalized["style"]["stroke_width"] < 0:
            raise ValueError(f"overlay at index {index} stroke_width must be >= 0")

        if not (0.0 <= normalized["style"]["opacity"] <= 1.0):
            raise ValueError(
                f"overlay at index {index} opacity must be between 0 and 1"
            )

        if not (0.1 <= normalized["style"]["text_box_width_ratio"] <= 1.0):
            raise ValueError(
                f"overlay at index {index} text_box_width_ratio must be between 0.1 and 1.0"
            )

        if normalized["style"]["margin_x"] < 0 or normalized["style"]["margin_y"] < 0:
            raise ValueError(
                f"overlay at index {index} margin_x and margin_y must be >= 0"
            )

        if normalized["position"]["preset"] != "custom":
            normalized["position"]["x"] = "center"
            normalized["position"]["y"] = "center"

        return normalized

    def _create_text_clip(
        self,
        overlay: Dict[str, Any],
        video_width: int,
    ) -> TextClip:
        style = overlay["style"]

        stroke_width = int(style["stroke_width"])
        requested_margin_x = int(style["margin_x"])
        requested_margin_y = int(style["margin_y"])

        # Keep some minimum padding so glyphs/strokes are not clipped.
        margin_x = max(requested_margin_x, 16 + (stroke_width * 4))
        margin_y = max(requested_margin_y, 12 + (stroke_width * 4))

        text_box_width_ratio = float(style["text_box_width_ratio"])
        text_box_width = max(100, int(video_width * text_box_width_ratio))

        clip_kwargs: Dict[str, Any] = {
            "text": overlay["text"],
            "font_size": style["font_size"],
            "color": style["text_color"],
            "bg_color": style["background_color"],
            "stroke_color": style["stroke_color"],
            "stroke_width": stroke_width,
            "method": "caption",
            "size": (text_box_width, None),
            "margin": (margin_x, margin_y),
            "text_align": "center",
            "horizontal_align": "center",
            "vertical_align": "center",
            "duration": overlay["duration"],
        }

        font_family = style["font_family"].strip()
        if font_family:
            clip_kwargs["font"] = font_family

        try:
            return TextClip(**clip_kwargs)
        except Exception:
            if "font" in clip_kwargs:
                self.logger.warning(
                    "Font '%s' unavailable. Falling back to default font.",
                    font_family,
                )
                clip_kwargs.pop("font", None)
                return TextClip(**clip_kwargs)
            raise

    def _resolve_position(
        self,
        position: Dict[str, Any],
        video_width: int,
        video_height: int,
        text_height: int,
    ) -> Tuple[Any, Any]:
        edge_padding = max(40, int(video_height * 0.06))
        max_bottom_y = max(0, video_height - text_height - edge_padding)

        preset = position["preset"]

        if preset == "top":
            return "center", edge_padding

        if preset == "center":
            return "center", "center"

        if preset == "bottom":
            return "center", max_bottom_y

        if preset == "custom":
            return float(position["x"]), float(position["y"])

        return "center", max_bottom_y

    def _default_output_path(self, input_path: Path) -> Path:
        suffix = input_path.suffix or ".mp4"
        return input_path.with_name(f"{input_path.stem}_text{suffix}")

    def _build_response(
        self,
        video_id: str,
        input_video_path: str,
        output_video_path: str,
        status: str,
        message: str,
        overlays: List[Dict[str, Any]],
        exception: Optional[str] = None,
    ) -> Dict[str, Any]:
        response: Dict[str, Any] = {
            "video_id": video_id,
            "input_video_path": input_video_path,
            "output_video_path": output_video_path,
            "status": status,
            "message": message,
            "video_overlay_config": {
                "has_text_overlays": len(overlays) > 0,
                "total_overlays": len(overlays),
                "overlays": overlays,
            },
        }

        if exception is not None:
            response["exception"] = exception

        return response
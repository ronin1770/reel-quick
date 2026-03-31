"""MongoDB model helpers for video text overlay results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, constr

VIDEO_OVERLAY_TEXT_COLLECTION = "video_overlay_text"

PositionValue = Union[str, float, int]


@dataclass
class VideoTextOverlayPosition:
    preset: str
    x: PositionValue
    y: PositionValue

    def to_bson(self) -> Dict[str, Any]:
        return {"preset": self.preset, "x": self.x, "y": self.y}


@dataclass
class VideoTextOverlayStyle:
    font_family: str = "Arial"
    font_size: int = 48
    font_weight: str = "normal"
    text_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    background_color: Optional[str] = None
    opacity: float = 1.0
    text_box_width_ratio: float = 0.9
    margin_x: int = 24
    margin_y: int = 18

    def to_bson(self) -> Dict[str, Any]:
        return {
            "font_family": self.font_family,
            "font_size": self.font_size,
            "font_weight": self.font_weight,
            "text_color": self.text_color,
            "stroke_color": self.stroke_color,
            "stroke_width": self.stroke_width,
            "background_color": self.background_color,
            "opacity": self.opacity,
            "text_box_width_ratio": self.text_box_width_ratio,
            "margin_x": self.margin_x,
            "margin_y": self.margin_y,
        }


@dataclass
class VideoTextOverlayItem:
    overlay_id: str
    text: str
    start_time: float
    end_time: float
    duration: float
    position: VideoTextOverlayPosition
    style: VideoTextOverlayStyle

    def to_bson(self) -> Dict[str, Any]:
        return {
            "overlay_id": self.overlay_id,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "position": self.position.to_bson(),
            "style": self.style.to_bson(),
        }


@dataclass
class VideoTextOverlayConfig:
    has_text_overlays: bool
    total_overlays: int
    overlays: List[VideoTextOverlayItem] = field(default_factory=list)

    def to_bson(self) -> Dict[str, Any]:
        return {
            "has_text_overlays": self.has_text_overlays,
            "total_overlays": self.total_overlays,
            "overlays": [overlay.to_bson() for overlay in self.overlays],
        }


@dataclass
class VideoTextModel:
    video_id: str
    input_video_path: str
    output_video_path: str
    status: str
    message: str
    video_overlay_config: Optional[VideoTextOverlayConfig] = None
    exception: Optional[str] = None
    creation_time: datetime = field(default_factory=datetime.utcnow)
    modification_time: datetime = field(default_factory=datetime.utcnow)

    def to_bson(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "video_id": self.video_id,
            "input_video_path": self.input_video_path,
            "output_video_path": self.output_video_path,
            "status": self.status,
            "message": self.message,
            "exception": self.exception,
            "creation_time": self.creation_time,
            "modification_time": self.modification_time,
        }
        if self.video_overlay_config is not None:
            payload["video_overlay_config"] = self.video_overlay_config.to_bson()
        return payload

    def to_upsert_update(self) -> Dict[str, Any]:
        payload = self.to_bson()
        creation_time = payload.pop("creation_time", datetime.utcnow())
        payload["modification_time"] = datetime.utcnow()
        return {
            "$set": payload,
            "$setOnInsert": {"creation_time": creation_time},
        }

    @classmethod
    def from_bson(cls, doc: Dict[str, Any]) -> "VideoTextModel":
        overlay_config_doc = doc.get("video_overlay_config")
        overlay_config = (
            _overlay_config_from_doc(overlay_config_doc)
            if isinstance(overlay_config_doc, dict)
            else None
        )

        return cls(
            video_id=doc.get("video_id", ""),
            input_video_path=doc.get("input_video_path", ""),
            output_video_path=doc.get("output_video_path", ""),
            status=doc.get("status", ""),
            message=doc.get("message", ""),
            video_overlay_config=overlay_config,
            exception=doc.get("exception"),
            creation_time=doc.get("creation_time", datetime.utcnow()),
            modification_time=doc.get("modification_time", datetime.utcnow()),
        )

    @classmethod
    def from_response(
        cls,
        payload: Dict[str, Any],
    ) -> "VideoTextModel":
        overlay_config_doc = payload.get("video_overlay_config")
        overlay_config = (
            _overlay_config_from_doc(overlay_config_doc)
            if isinstance(overlay_config_doc, dict)
            else None
        )
        now = datetime.utcnow()
        return cls(
            video_id=str(payload.get("video_id", "")).strip(),
            input_video_path=str(payload.get("input_video_path", "")).strip(),
            output_video_path=str(payload.get("output_video_path", "")).strip(),
            status=str(payload.get("status", "")).strip(),
            message=str(payload.get("message", "")).strip(),
            video_overlay_config=overlay_config,
            exception=(
                str(payload.get("exception")).strip()
                if payload.get("exception") is not None
                else None
            ),
            creation_time=now,
            modification_time=now,
        )


class VideoTextOverlayPositionSchema(BaseModel):
    preset: str
    x: PositionValue
    y: PositionValue


class VideoTextOverlayStyleSchema(BaseModel):
    font_family: str = "Arial"
    font_size: int = 48
    font_weight: str = "normal"
    text_color: str = "#FFFFFF"
    stroke_color: str = "#000000"
    stroke_width: int = 2
    background_color: Optional[str] = None
    opacity: float = 1.0
    text_box_width_ratio: float = 0.9
    margin_x: int = 24
    margin_y: int = 18


class VideoTextOverlayItemSchema(BaseModel):
    overlay_id: str
    text: str
    start_time: float
    end_time: float
    duration: float
    position: VideoTextOverlayPositionSchema
    style: VideoTextOverlayStyleSchema


class VideoTextOverlayConfigSchema(BaseModel):
    has_text_overlays: bool
    total_overlays: int
    overlays: List[VideoTextOverlayItemSchema] = Field(default_factory=list)


class VideoTextSchema(BaseModel):
    video_id: str
    input_video_path: str
    output_video_path: str
    status: str
    message: str
    video_overlay_config: Optional[VideoTextOverlayConfigSchema] = None
    exception: Optional[str] = None
    creation_time: datetime = Field(default_factory=datetime.utcnow)
    modification_time: datetime = Field(default_factory=datetime.utcnow)


class VideoTextUpsert(BaseModel):
    video_id: constr(strip_whitespace=True, min_length=1)
    input_video_path: constr(strip_whitespace=True, min_length=1)
    output_video_path: str = ""
    status: constr(strip_whitespace=True, min_length=1)
    message: constr(strip_whitespace=True, min_length=1)
    video_overlay_config: Optional[VideoTextOverlayConfigSchema] = None
    exception: Optional[str] = None


class VideoTextOverlayItemsUpsert(BaseModel):
    overlays: List[VideoTextOverlayItemSchema] = Field(default_factory=list)
    output_video_path: str = ""


def _overlay_config_from_doc(doc: Dict[str, Any]) -> VideoTextOverlayConfig:
    overlays: List[VideoTextOverlayItem] = []
    for overlay_doc in doc.get("overlays", []) or []:
        if not isinstance(overlay_doc, dict):
            continue
        position_doc = overlay_doc.get("position", {}) or {}
        style_doc = overlay_doc.get("style", {}) or {}

        overlays.append(
            VideoTextOverlayItem(
                overlay_id=str(overlay_doc.get("overlay_id", "")),
                text=str(overlay_doc.get("text", "")),
                start_time=float(overlay_doc.get("start_time", 0.0)),
                end_time=float(overlay_doc.get("end_time", 0.0)),
                duration=float(overlay_doc.get("duration", 0.0)),
                position=VideoTextOverlayPosition(
                    preset=str(position_doc.get("preset", "bottom")),
                    x=position_doc.get("x", "center"),
                    y=position_doc.get("y", "center"),
                ),
                style=VideoTextOverlayStyle(
                    font_family=str(style_doc.get("font_family", "Arial")),
                    font_size=int(style_doc.get("font_size", 48)),
                    font_weight=str(style_doc.get("font_weight", "normal")),
                    text_color=str(style_doc.get("text_color", "#FFFFFF")),
                    stroke_color=str(style_doc.get("stroke_color", "#000000")),
                    stroke_width=int(style_doc.get("stroke_width", 2)),
                    background_color=style_doc.get("background_color"),
                    opacity=float(style_doc.get("opacity", 1.0)),
                    text_box_width_ratio=float(style_doc.get("text_box_width_ratio", 0.9)),
                    margin_x=int(style_doc.get("margin_x", 24)),
                    margin_y=int(style_doc.get("margin_y", 18)),
                ),
            )
        )

    return VideoTextOverlayConfig(
        has_text_overlays=bool(doc.get("has_text_overlays", False)),
        total_overlays=int(doc.get("total_overlays", len(overlays))),
        overlays=overlays,
    )

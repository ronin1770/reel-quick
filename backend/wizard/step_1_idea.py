"""Service layer for wizard Step 1 research generation and validation."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import ValidationError

from backend.models.wizard_step_1 import (
    DEFAULT_EXAMPLE_ITEM_LIMIT,
    DEFAULT_WIZARD_PLATFORM,
    MIN_TREND_COUNT,
    Step1ResearchResultSchema,
    Step1TrendSchema,
)
from backend.objects.ai_engine import AiEngine


class Step1ResearchValidationError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""

    def __init__(self, errors: List[Dict[str, Any]], raw_response: str) -> None:
        super().__init__("Step 1 research validation failed")
        self.errors = errors
        self.raw_response = raw_response


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def _error(loc: List[Any], msg: str, error_type: str) -> Dict[str, Any]:
    return {"loc": loc, "msg": msg, "type": error_type}


class Step1IdeaService:
    """Generate and validate wizard Step 1 research output."""

    def __init__(self, *, model: str = "gpt-4o") -> None:
        self._engine = AiEngine(model=model, temperature=0.0)

    def run(self, wizard_doc: Dict[str, Any]) -> Dict[str, Any]:
        raw_response = self._engine.run_prompt(
            "step_1_idea_prompt",
            self._build_prompt_variables(wizard_doc),
        )
        payload = self._parse_json(raw_response)
        return self._validate_and_normalize(payload, wizard_doc, raw_response)

    def _build_prompt_variables(self, wizard_doc: Dict[str, Any]) -> Dict[str, Any]:
        research_period = wizard_doc.get("research_period", {}) or {}
        return {
            "WIZARD_ID": str(wizard_doc.get("_id", "")),
            "NICHE": wizard_doc.get("niche", ""),
            "LANGUAGE": wizard_doc.get("language", ""),
            "START_DATE": research_period.get("start_date", ""),
            "END_DATE": research_period.get("end_date", ""),
            "PLATFORM": DEFAULT_WIZARD_PLATFORM,
            "TREND_LIMIT": str(wizard_doc.get("trend_limit", 20)),
            "EXAMPLE_ITEM_LIMIT": str(DEFAULT_EXAMPLE_ITEM_LIMIT),
        }

    def _parse_json(self, raw_response: str) -> Dict[str, Any]:
        cleaned = _strip_code_fences(raw_response)
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise Step1ResearchValidationError(
                errors=[
                    _error(
                        ["response"],
                        f"Invalid JSON returned by model: {exc.msg}",
                        "value_error.jsondecode",
                    )
                ],
                raw_response=raw_response,
            ) from exc

        if not isinstance(payload, dict):
            raise Step1ResearchValidationError(
                errors=[
                    _error(
                        ["response"],
                        "Model response must be a JSON object.",
                        "type_error.dict",
                    )
                ],
                raw_response=raw_response,
            )
        return payload

    def _validate_and_normalize(
        self,
        payload: Dict[str, Any],
        wizard_doc: Dict[str, Any],
        raw_response: str,
    ) -> Dict[str, Any]:
        try:
            parsed = Step1ResearchResultSchema(**payload)
        except ValidationError as exc:
            raise Step1ResearchValidationError(
                errors=exc.errors(),
                raw_response=raw_response,
            ) from exc

        expected_wizard_id = str(wizard_doc.get("_id", ""))
        expected_niche = wizard_doc.get("niche", "")
        expected_language = wizard_doc.get("language", "")
        expected_start = (wizard_doc.get("research_period", {}) or {}).get(
            "start_date", ""
        )
        expected_end = (wizard_doc.get("research_period", {}) or {}).get(
            "end_date", ""
        )
        expected_platforms = wizard_doc.get("platforms_analyzed", []) or [
            DEFAULT_WIZARD_PLATFORM
        ]
        expected_trend_limit = int(wizard_doc.get("trend_limit", 20))

        errors: List[Dict[str, Any]] = []
        if parsed.wizard_id != expected_wizard_id:
            errors.append(
                _error(
                    ["wizard_id"],
                    "wizard_id must match the current wizard document _id.",
                    "value_error.mismatch",
                )
            )
        if parsed.niche != expected_niche:
            errors.append(
                _error(
                    ["niche"],
                    "niche must match the current wizard document.",
                    "value_error.mismatch",
                )
            )
        if parsed.language != expected_language:
            errors.append(
                _error(
                    ["language"],
                    "language must match the current wizard document.",
                    "value_error.mismatch",
                )
            )
        if parsed.research_period.start_date != expected_start:
            errors.append(
                _error(
                    ["research_period", "start_date"],
                    "research_period.start_date must match the request.",
                    "value_error.mismatch",
                )
            )
        if parsed.research_period.end_date != expected_end:
            errors.append(
                _error(
                    ["research_period", "end_date"],
                    "research_period.end_date must match the request.",
                    "value_error.mismatch",
                )
            )
        if parsed.platforms_analyzed != expected_platforms:
            errors.append(
                _error(
                    ["platforms_analyzed"],
                    "platforms_analyzed must be exactly ['Instagram Reels'] for v1.",
                    "value_error.mismatch",
                )
            )
        trend_count = len(parsed.trends)
        if trend_count < MIN_TREND_COUNT:
            errors.append(
                _error(
                    ["trends"],
                    f"trends must contain at least {MIN_TREND_COUNT} items.",
                    "value_error.length",
                )
            )
        if trend_count > expected_trend_limit:
            errors.append(
                _error(
                    ["trends"],
                    f"trends must contain no more than {expected_trend_limit} items.",
                    "value_error.length",
                )
            )

        for index, trend in enumerate(parsed.trends):
            self._validate_trend_lengths(trend, index, errors)
            self._validate_trend_score(trend, index, errors)

        if errors:
            raise Step1ResearchValidationError(errors=errors, raw_response=raw_response)

        normalized = _model_dump(parsed)
        for trend in normalized.get("trends", []):
            trend["trend_id"] = str(uuid4())
        return normalized

    def _validate_trend_lengths(
        self,
        trend: Step1TrendSchema,
        index: int,
        errors: List[Dict[str, Any]],
    ) -> None:
        if len(trend.example_hooks) != DEFAULT_EXAMPLE_ITEM_LIMIT:
            errors.append(
                _error(
                    ["trends", index, "example_hooks"],
                    f"example_hooks must contain exactly {DEFAULT_EXAMPLE_ITEM_LIMIT} items.",
                    "value_error.length",
                )
            )
        if len(trend.example_titles) != DEFAULT_EXAMPLE_ITEM_LIMIT:
            errors.append(
                _error(
                    ["trends", index, "example_titles"],
                    f"example_titles must contain exactly {DEFAULT_EXAMPLE_ITEM_LIMIT} items.",
                    "value_error.length",
                )
            )
        if len(trend.example_video_concepts) != DEFAULT_EXAMPLE_ITEM_LIMIT:
            errors.append(
                _error(
                    ["trends", index, "example_video_concepts"],
                    f"example_video_concepts must contain exactly {DEFAULT_EXAMPLE_ITEM_LIMIT} items.",
                    "value_error.length",
                )
            )
        if not trend.recommended_video_structure:
            errors.append(
                _error(
                    ["trends", index, "recommended_video_structure"],
                    "recommended_video_structure must contain at least one item.",
                    "value_error.length",
                )
            )
        if not trend.suggested_visual_style:
            errors.append(
                _error(
                    ["trends", index, "suggested_visual_style"],
                    "suggested_visual_style must contain at least one item.",
                    "value_error.length",
                )
            )
        if not trend.risks_and_limitations:
            errors.append(
                _error(
                    ["trends", index, "risks_and_limitations"],
                    "risks_and_limitations must contain at least one item.",
                    "value_error.length",
                )
            )

    def _validate_trend_score(
        self,
        trend: Step1TrendSchema,
        index: int,
        errors: List[Dict[str, Any]],
    ) -> None:
        if trend.opportunity_score < 0 or trend.opportunity_score > 100:
            errors.append(
                _error(
                    ["trends", index, "opportunity_score"],
                    "opportunity_score must be between 0 and 100.",
                    "value_error.range",
                )
            )

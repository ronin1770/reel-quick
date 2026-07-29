"""Service layer for wizard Step 2 video search generation and validation."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from backend.models.wizard_step_2 import (
    ALLOWED_STEP_2_ORIENTATIONS,
    DEFAULT_STEP_2_MAX_RESULTS,
    Step2ResearchResultSchema,
    Step2VideoResultSchema,
)

PROMPT_DIR = (Path(__file__).resolve().parents[1] / "objects" / "prompts").resolve()
PROMPT_NAME = "step_2_video_search_prompt.txt"
_TOKEN_RE = re.compile(r"<([A-Z0-9_]+)>")
ALLOWED_SOURCES = {
    "Pexels": ("pexels.com",),
    "Pixabay": ("pixabay.com",),
    "Mixkit": ("mixkit.co",),
    "Coverr": ("coverr.co",),
    "Videvo": ("videvo.net",),
    "Wikimedia Commons": ("commons.wikimedia.org", "wikimedia.org"),
}
SEARCH_SOURCE_NAMES = ", ".join(ALLOWED_SOURCES.keys())
STEP_2_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "wizard_id",
        "query",
        "search_terms",
        "videos",
        "warnings",
        "generated_at",
    ],
    "properties": {
        "wizard_id": {"type": "string"},
        "query": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "niche",
                "trend_name",
                "video_title",
                "video_concept",
                "maximum_results",
            ],
            "properties": {
                "niche": {"type": "string"},
                "trend_name": {"type": "string"},
                "video_title": {"type": "string"},
                "video_concept": {"type": "string"},
                "maximum_results": {"type": "integer"},
            },
        },
        "search_terms": {
            "type": "array",
            "items": {"type": "string"},
        },
        "videos": {
            "type": "array",
            "maxItems": DEFAULT_STEP_2_MAX_RESULTS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "result_id",
                    "title",
                    "description",
                    "source",
                    "page_url",
                    "preview_url",
                    "creator_name",
                    "duration_seconds",
                    "orientation",
                    "resolution",
                    "search_term",
                    "visual_tags",
                    "recommended_usage",
                    "license",
                    "relevance_score",
                    "selection_notes",
                ],
                "properties": {
                    "result_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "source": {"type": "string"},
                    "page_url": {"type": "string"},
                    "preview_url": {"type": ["string", "null"]},
                    "creator_name": {"type": ["string", "null"]},
                    "duration_seconds": {"type": ["number", "null"]},
                    "orientation": {
                        "type": "string",
                        "enum": list(ALLOWED_STEP_2_ORIENTATIONS),
                    },
                    "resolution": {"type": ["string", "null"]},
                    "search_term": {"type": "string"},
                    "visual_tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "recommended_usage": {"type": "string"},
                    "license": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "license_name",
                            "license_url",
                            "commercial_use_allowed",
                            "modification_allowed",
                            "attribution_required",
                            "license_verified",
                            "verification_notes",
                        ],
                        "properties": {
                            "license_name": {"type": "string"},
                            "license_url": {"type": ["string", "null"]},
                            "commercial_use_allowed": {"type": "boolean"},
                            "modification_allowed": {"type": "boolean"},
                            "attribution_required": {"type": "boolean"},
                            "license_verified": {"type": "boolean"},
                            "verification_notes": {"type": "string"},
                        },
                    },
                    "relevance_score": {"type": "integer"},
                    "selection_notes": {"type": "string"},
                },
            },
        },
        "warnings": {
            "type": "array",
            "items": {"type": "string"},
        },
        "generated_at": {"type": "string"},
    },
}


class Step2VideoSearchValidationError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""

    def __init__(self, errors: List[Dict[str, Any]], raw_response: str) -> None:
        super().__init__("Step 2 video search validation failed")
        self.errors = errors
        self.raw_response = raw_response


def _model_dump(model: Any) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _error(loc: List[Any], msg: str, error_type: str) -> Dict[str, Any]:
    return {"loc": loc, "msg": msg, "type": error_type}


def _is_valid_url(value: Optional[str]) -> bool:
    if not value:
        return False

    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _hostname_matches(url: str, candidates: tuple[str, ...]) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return any(
        hostname == candidate or hostname.endswith(f".{candidate}")
        for candidate in candidates
    )


def _parse_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def _parse_iso_datetime_value(value: str) -> Optional[datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonicalize_url(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


class Step2VideoSearchService:
    """Generate and validate wizard Step 2 stock video search output."""

    def __init__(self, *, model: str = "gpt-4o") -> None:
        load_dotenv(find_dotenv())
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in environment or .env")

        self._model = model
        self._client = OpenAI(api_key=api_key)

    def run(
        self,
        wizard_doc: Dict[str, Any],
        step_2_doc: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(wizard_doc, step_2_doc)
        response = self._client.responses.create(
            model=self._model,
            input=prompt,
            temperature=0.0,
            max_output_tokens=4000,
            tools=[
                {
                    "type": "web_search_preview",
                    "search_context_size": "high",
                }
            ],
            include=["web_search_call.action.sources"],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "wizard_step_2_video_search",
                    "strict": True,
                    "schema": STEP_2_RESPONSE_SCHEMA,
                    "description": "Structured stock-video search recommendations for wizard step 2.",
                },
            },
        )
        raw_response = response.output_text or self._serialize_response(response)
        payload = self._parse_json(raw_response)
        grounded_urls = self._extract_grounded_urls(response)
        return self._validate_and_normalize(
            payload,
            wizard_doc,
            step_2_doc,
            raw_response,
            grounded_urls,
        )

    def _build_prompt(
        self,
        wizard_doc: Dict[str, Any],
        step_2_doc: Dict[str, Any],
    ) -> str:
        prompt_path = PROMPT_DIR / PROMPT_NAME
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")

        variables = {
            "WIZARD_ID": str(wizard_doc.get("_id", "")),
            "NICHE": wizard_doc.get("niche", ""),
            "TREND_NAME": step_2_doc.get("trend_name", ""),
            "VIDEO_TITLE": step_2_doc.get("video_title", ""),
            "VIDEO_CONCEPT": step_2_doc.get("video_concept", ""),
            "MAXIMUM_RESULTS": str(step_2_doc.get("maximum_results", "")),
            "SOURCE_NAMES": SEARCH_SOURCE_NAMES,
        }
        prompt_text = prompt_path.read_text(encoding="utf-8")
        rendered = prompt_text
        for key, value in variables.items():
            rendered = rendered.replace(f"<{key}>", str(value))

        unresolved = sorted(set(_TOKEN_RE.findall(rendered)))
        if unresolved:
            unresolved_list = ", ".join(unresolved)
            raise ValueError(f"Unresolved prompt tokens: {unresolved_list}")
        return rendered

    def _parse_json(self, raw_response: str) -> Dict[str, Any]:
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError as exc:
            raise Step2VideoSearchValidationError(
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
            raise Step2VideoSearchValidationError(
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
        step_2_doc: Dict[str, Any],
        raw_response: str,
        grounded_urls: Set[str],
    ) -> Dict[str, Any]:
        try:
            parsed = Step2ResearchResultSchema(**payload)
        except ValidationError as exc:
            raise Step2VideoSearchValidationError(
                errors=exc.errors(),
                raw_response=raw_response,
            ) from exc

        expected_wizard_id = str(wizard_doc.get("_id", ""))
        expected_niche = wizard_doc.get("niche", "")
        expected_trend_name = step_2_doc.get("trend_name", "")
        expected_video_title = step_2_doc.get("video_title", "")
        expected_video_concept = step_2_doc.get("video_concept", "")
        expected_maximum_results = int(
            step_2_doc.get("maximum_results", DEFAULT_STEP_2_MAX_RESULTS)
        )

        errors: List[Dict[str, Any]] = []
        if parsed.wizard_id != expected_wizard_id:
            errors.append(
                _error(
                    ["wizard_id"],
                    "wizard_id must match the current wizard document _id.",
                    "value_error.mismatch",
                )
            )
        if parsed.query.niche != expected_niche:
            errors.append(
                _error(
                    ["query", "niche"],
                    "query.niche must match the current wizard document.",
                    "value_error.mismatch",
                )
            )
        if parsed.query.trend_name != expected_trend_name:
            errors.append(
                _error(
                    ["query", "trend_name"],
                    "query.trend_name must match the current request.",
                    "value_error.mismatch",
                )
            )
        if parsed.query.video_title != expected_video_title:
            errors.append(
                _error(
                    ["query", "video_title"],
                    "query.video_title must match the current request.",
                    "value_error.mismatch",
                )
            )
        if parsed.query.video_concept != expected_video_concept:
            errors.append(
                _error(
                    ["query", "video_concept"],
                    "query.video_concept must match the current request.",
                    "value_error.mismatch",
                )
            )
        if parsed.query.maximum_results != expected_maximum_results:
            errors.append(
                _error(
                    ["query", "maximum_results"],
                    "query.maximum_results must match the current request.",
                    "value_error.mismatch",
                )
            )
        if len(parsed.search_terms) < 1:
            errors.append(
                _error(
                    ["search_terms"],
                    "search_terms must contain at least 1 item.",
                    "value_error.length",
                )
            )
        if len(parsed.videos) > expected_maximum_results:
            errors.append(
                _error(
                    ["videos"],
                    f"videos must contain no more than {expected_maximum_results} items.",
                    "value_error.length",
                )
            )
        if not _parse_iso_datetime(parsed.generated_at):
            errors.append(
                _error(
                    ["generated_at"],
                    "generated_at must be a valid ISO 8601 datetime string.",
                    "value_error.datetime",
                )
            )
        else:
            generated_at = _parse_iso_datetime_value(parsed.generated_at)
            now_utc = datetime.now(timezone.utc)
            if generated_at is None:
                errors.append(
                    _error(
                        ["generated_at"],
                        "generated_at must be a valid ISO 8601 datetime string.",
                        "value_error.datetime",
                    )
                )
            elif abs(now_utc - generated_at) > timedelta(days=2):
                errors.append(
                    _error(
                        ["generated_at"],
                        "generated_at must reflect the current Step 2 run time.",
                        "value_error.stale_datetime",
                    )
                )

        if not grounded_urls:
            errors.append(
                _error(
                    ["service"],
                    "The web search tool did not return any grounded source URLs.",
                    "value_error.no_grounded_sources",
                )
            )

        seen_page_urls: set[str] = set()
        seen_result_ids: set[str] = set()
        for index, video in enumerate(parsed.videos):
            self._validate_video(
                video,
                index,
                errors,
                seen_page_urls,
                seen_result_ids,
                grounded_urls,
            )

        if errors:
            raise Step2VideoSearchValidationError(errors=errors, raw_response=raw_response)

        return _model_dump(parsed)

    def _validate_video(
        self,
        video: Step2VideoResultSchema,
        index: int,
        errors: List[Dict[str, Any]],
        seen_page_urls: set[str],
        seen_result_ids: set[str],
        grounded_urls: Set[str],
    ) -> None:
        if video.result_id in seen_result_ids:
            errors.append(
                _error(
                    ["videos", index, "result_id"],
                    "result_id values must be unique.",
                    "value_error.duplicate",
                )
            )
        seen_result_ids.add(video.result_id)

        if video.page_url in seen_page_urls:
            errors.append(
                _error(
                    ["videos", index, "page_url"],
                    "page_url values must be unique.",
                    "value_error.duplicate",
                )
            )
        seen_page_urls.add(video.page_url)

        if not _is_valid_url(video.page_url):
            errors.append(
                _error(
                    ["videos", index, "page_url"],
                    "page_url must be a valid public HTTP or HTTPS URL.",
                    "value_error.url",
                )
            )
        if video.preview_url is not None and not _is_valid_url(video.preview_url):
            errors.append(
                _error(
                    ["videos", index, "preview_url"],
                    "preview_url must be null or a valid HTTP or HTTPS URL.",
                    "value_error.url",
                )
            )
        if video.license.license_url is not None and not _is_valid_url(video.license.license_url):
            errors.append(
                _error(
                    ["videos", index, "license", "license_url"],
                    "license.license_url must be null or a valid HTTP or HTTPS URL.",
                    "value_error.url",
                )
            )
        if video.relevance_score < 1 or video.relevance_score > 100:
            errors.append(
                _error(
                    ["videos", index, "relevance_score"],
                    "relevance_score must be between 1 and 100.",
                    "value_error.range",
                )
            )
        if video.duration_seconds is not None and video.duration_seconds <= 0:
            errors.append(
                _error(
                    ["videos", index, "duration_seconds"],
                    "duration_seconds must be greater than 0 when provided.",
                    "value_error.range",
                )
            )
        allowed_domains = ALLOWED_SOURCES.get(video.source)
        if allowed_domains is None:
            errors.append(
                _error(
                    ["videos", index, "source"],
                    f"source must be one of: {SEARCH_SOURCE_NAMES}.",
                    "value_error.choice",
                )
            )
        elif _is_valid_url(video.page_url) and not _hostname_matches(video.page_url, allowed_domains):
            errors.append(
                _error(
                    ["videos", index, "page_url"],
                    "page_url domain does not match the declared source.",
                    "value_error.domain_mismatch",
                )
            )
        elif _is_valid_url(video.page_url):
            canonical_page_url = _canonicalize_url(video.page_url)
            if canonical_page_url not in grounded_urls:
                errors.append(
                    _error(
                        ["videos", index, "page_url"],
                        "page_url must match a URL actually observed by the web search tool.",
                        "value_error.ungrounded_url",
                    )
                )

    def _extract_grounded_urls(self, response: Any) -> Set[str]:
        grounded_urls: Set[str] = set()
        for item in getattr(response, "output", []) or []:
            item_type = getattr(item, "type", None)
            if item_type != "web_search_call":
                continue

            action = getattr(item, "action", None)
            action_type = getattr(action, "type", None)
            if action_type == "search":
                for source in getattr(action, "sources", []) or []:
                    url = getattr(source, "url", None)
                    if _is_valid_url(url):
                        grounded_urls.add(_canonicalize_url(url))
            elif action_type in {"open_page", "find_in_page"}:
                url = getattr(action, "url", None)
                if _is_valid_url(url):
                    grounded_urls.add(_canonicalize_url(url))
        return grounded_urls

    @staticmethod
    def _serialize_response(response: Any) -> str:
        if hasattr(response, "model_dump_json"):
            return response.model_dump_json(indent=2)
        return str(response)

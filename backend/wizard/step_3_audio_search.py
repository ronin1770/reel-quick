"""Service layer for wizard Step 3 trending audio research and validation."""

from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

from dotenv import find_dotenv, load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from backend.logger import get_logger
from backend.models.wizard_audio_search import (
    ALLOWED_AUDIO_TYPES,
    ALLOWED_EVIDENCE_SOURCE_TYPES,
    DEFAULT_AUDIO_SEARCH_MAX_RESULTS,
    AudioSearchModelResultSchema,
    AudioSearchRecommendationSchema,
)

PROMPT_DIR = (Path(__file__).resolve().parents[1] / "objects" / "prompts").resolve()
PROMPT_NAME = "wizard_audio_search_prompt.txt"
_TOKEN_RE = re.compile(r"<([A-Z0-9_]+)>")
_FUTURE_LIMITATION_RE = re.compile(
    r"\b(future|projection|projected|forecast|forecasted|not possible)\b",
    re.IGNORECASE,
)
logger = get_logger(name="instagram_reel_creation_step_3_audio_search")
AUDIO_SEARCH_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "niche",
        "research_period",
        "generated_at",
        "results",
        "limitations",
    ],
    "properties": {
        "niche": {"type": "string"},
        "research_period": {
            "type": "object",
            "additionalProperties": False,
            "required": ["start_date", "end_date"],
            "properties": {
                "start_date": {"type": "string"},
                "end_date": {"type": "string"},
            },
        },
        "generated_at": {"type": "string"},
        "results": {
            "type": "array",
            "maxItems": DEFAULT_AUDIO_SEARCH_MAX_RESULTS,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "rank",
                    "audio_name",
                    "artist_name",
                    "audio_type",
                    "relevance_score",
                    "trend_confidence_score",
                    "best_for",
                    "why_selected",
                    "evidence",
                ],
                "properties": {
                    "rank": {"type": "integer"},
                    "audio_name": {"type": "string"},
                    "artist_name": {"type": "string"},
                    "audio_type": {
                        "type": "string",
                        "enum": list(ALLOWED_AUDIO_TYPES),
                    },
                    "relevance_score": {"type": "integer"},
                    "trend_confidence_score": {"type": "integer"},
                    "best_for": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "why_selected": {"type": "string"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": [
                                "source_name",
                                "source_type",
                                "published_or_updated_date",
                                "url",
                                "supports",
                            ],
                            "properties": {
                                "source_name": {"type": "string"},
                                "source_type": {
                                    "type": "string",
                                    "enum": list(ALLOWED_EVIDENCE_SOURCE_TYPES),
                                },
                                "published_or_updated_date": {
                                    "type": ["string", "null"],
                                },
                                "url": {"type": "string"},
                                "supports": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}


class Step3AudioSearchValidationError(Exception):
    """Raised when the LLM response cannot be parsed or validated."""

    def __init__(self, errors: List[Dict[str, Any]], raw_response: str) -> None:
        super().__init__("Step 3 audio search validation failed")
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


def _parse_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def _canonicalize_url(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}"


def _current_iso_datetime() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )


def _current_iso_date() -> str:
    return date.today().isoformat()


def _is_past_or_present_period(end_date_value: str) -> bool:
    try:
        return datetime.strptime(end_date_value, "%Y-%m-%d").date() <= date.today()
    except ValueError:
        return False


class Step3AudioSearchService:
    """Generate and validate wizard Step 3 trending audio recommendations."""

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
        audio_search_doc: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = self._build_prompt(audio_search_doc)
        print(
            (
                f"[Step3AudioSearchService] Rendered prompt for "
                f"wizard_id={wizard_doc.get('_id', '')}\n{prompt}\n"
            ),
            flush=True,
        )
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
                    "name": "wizard_step_3_audio_search",
                    "strict": True,
                    "schema": AUDIO_SEARCH_RESPONSE_SCHEMA,
                    "description": (
                        "Structured trending Instagram audio recommendations "
                        "for wizard step 3."
                    ),
                },
            },
        )
        raw_response = response.output_text or self._serialize_response(response)
        payload = self._parse_json(raw_response)
        grounded_urls = self._extract_grounded_urls(response)
        return self._validate_and_normalize(
            payload,
            wizard_doc,
            audio_search_doc,
            raw_response,
            grounded_urls,
        )

    def _build_prompt(self, audio_search_doc: Dict[str, Any]) -> str:
        prompt_path = PROMPT_DIR / PROMPT_NAME
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt not found: {prompt_path}")

        research_period = audio_search_doc.get("research_period", {})
        variables = {
            "NICHE": audio_search_doc.get("niche", ""),
            "START_DATE": research_period.get("start_date", ""),
            "END_DATE": research_period.get("end_date", ""),
            "CURRENT_DATE": _current_iso_date(),
            "LIMIT": str(
                audio_search_doc.get(
                    "maximum_results",
                    DEFAULT_AUDIO_SEARCH_MAX_RESULTS,
                )
            ),
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
            raise Step3AudioSearchValidationError(
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
            raise Step3AudioSearchValidationError(
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
        audio_search_doc: Dict[str, Any],
        raw_response: str,
        grounded_urls: Set[str],
    ) -> Dict[str, Any]:
        try:
            parsed = AudioSearchModelResultSchema(**payload)
        except ValidationError as exc:
            raise Step3AudioSearchValidationError(
                errors=exc.errors(),
                raw_response=raw_response,
            ) from exc

        expected_wizard_id = str(wizard_doc.get("_id", ""))
        expected_niche = audio_search_doc.get("niche", "")
        expected_period = audio_search_doc.get("research_period", {})
        expected_limit = int(
            audio_search_doc.get("maximum_results", DEFAULT_AUDIO_SEARCH_MAX_RESULTS)
        )

        errors: List[Dict[str, Any]] = []
        if not expected_wizard_id:
            errors.append(
                _error(
                    ["service"],
                    "wizard_doc._id is required for Step 3 normalization.",
                    "value_error.missing_wizard_id",
                )
            )
        if parsed.niche != expected_niche:
            errors.append(
                _error(
                    ["niche"],
                    "niche must match the current request.",
                    "value_error.mismatch",
                )
            )
        if parsed.research_period.start_date != expected_period.get("start_date"):
            errors.append(
                _error(
                    ["research_period", "start_date"],
                    "research_period.start_date must match the current request.",
                    "value_error.mismatch",
                )
            )
        if parsed.research_period.end_date != expected_period.get("end_date"):
            errors.append(
                _error(
                    ["research_period", "end_date"],
                    "research_period.end_date must match the current request.",
                    "value_error.mismatch",
                )
            )
        if len(parsed.results) > expected_limit:
            errors.append(
                _error(
                    ["results"],
                    f"results must contain no more than {expected_limit} items.",
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

        ranks: Set[int] = set()
        seen_audio_keys: Set[Tuple[str, str]] = set()
        for index, result in enumerate(parsed.results):
            self._validate_result(
                result,
                index,
                errors,
                ranks,
                seen_audio_keys,
                grounded_urls,
            )

        self._validate_result_order(parsed.results, errors)

        if errors:
            raise Step3AudioSearchValidationError(errors=errors, raw_response=raw_response)

        normalized_audio = _model_dump(parsed)
        # Use server time for persistence so minor model clock drift does not fail valid runs.
        normalized_audio["generated_at"] = _current_iso_datetime()
        normalized_audio["limitations"] = self._normalize_limitations(
            normalized_audio.get("limitations", []),
            expected_period.get("end_date", ""),
            bool(normalized_audio.get("results")),
        )
        return {
            "wizard_id": expected_wizard_id,
            "query": {
                "niche": expected_niche,
                "start_date": expected_period.get("start_date"),
                "end_date": expected_period.get("end_date"),
                "maximum_results": expected_limit,
            },
            "input_values": {
                "niche": expected_niche,
                "start_date": expected_period.get("start_date"),
                "end_date": expected_period.get("end_date"),
                "limit": expected_limit,
            },
            "audio": normalized_audio,
        }

    def _validate_result(
        self,
        result: AudioSearchRecommendationSchema,
        index: int,
        errors: List[Dict[str, Any]],
        ranks: Set[int],
        seen_audio_keys: Set[Tuple[str, str]],
        grounded_urls: Set[str],
    ) -> None:
        if result.rank in ranks:
            errors.append(
                _error(
                    ["results", index, "rank"],
                    "rank values must be unique.",
                    "value_error.duplicate",
                )
            )
        ranks.add(result.rank)

        audio_key = (
            result.audio_name.strip().casefold(),
            result.artist_name.strip().casefold(),
        )
        if audio_key in seen_audio_keys:
            errors.append(
                _error(
                    ["results", index],
                    "Duplicate audio_name and artist_name combinations are not allowed.",
                    "value_error.duplicate",
                )
            )
        seen_audio_keys.add(audio_key)

        if not result.best_for:
            errors.append(
                _error(
                    ["results", index, "best_for"],
                    "best_for must contain at least one item.",
                    "value_error.length",
                )
            )

        if not result.evidence:
            errors.append(
                _error(
                    ["results", index, "evidence"],
                    "evidence must contain at least one item.",
                    "value_error.length",
                )
            )

        for evidence_index, evidence in enumerate(result.evidence):
            if (
                evidence.published_or_updated_date is not None
                and not _parse_iso_date(evidence.published_or_updated_date)
            ):
                errors.append(
                    _error(
                        [
                            "results",
                            index,
                            "evidence",
                            evidence_index,
                            "published_or_updated_date",
                        ],
                        "published_or_updated_date must be YYYY-MM-DD or null.",
                        "value_error.date",
                    )
                )
            if not _is_valid_url(evidence.url):
                errors.append(
                    _error(
                        ["results", index, "evidence", evidence_index, "url"],
                        "evidence.url must be a valid public HTTP or HTTPS URL.",
                        "value_error.url",
                    )
                )
                continue

            canonical_url = _canonicalize_url(evidence.url)
            if grounded_urls and canonical_url not in grounded_urls:
                errors.append(
                    _error(
                        ["results", index, "evidence", evidence_index, "url"],
                        "evidence.url must match a URL actually observed by the web search tool.",
                        "value_error.ungrounded_url",
                    )
                )

    def _validate_result_order(
        self,
        results: List[AudioSearchRecommendationSchema],
        errors: List[Dict[str, Any]],
    ) -> None:
        expected_rank = 1
        for index, result in enumerate(results):
            if result.rank != expected_rank:
                errors.append(
                    _error(
                        ["results", index, "rank"],
                        "rank values must be sequential starting at 1.",
                        "value_error.rank_sequence",
                    )
                )
            expected_rank += 1

        ordered = sorted(
            results,
            key=lambda item: (
                -item.trend_confidence_score,
                -item.relevance_score,
            ),
        )
        actual_ranks = [item.rank for item in results]
        expected_ranks = [item.rank for item in ordered]
        if actual_ranks != expected_ranks:
            errors.append(
                _error(
                    ["results"],
                    "results must be sorted by trend_confidence_score descending and relevance_score descending on ties.",
                    "value_error.sort_order",
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

    def _normalize_limitations(
        self,
        limitations: List[str],
        end_date_value: str,
        has_results: bool,
    ) -> List[str]:
        normalized = [item.strip() for item in limitations if isinstance(item, str) and item.strip()]
        if not _is_past_or_present_period(end_date_value):
            return normalized

        filtered = [
            item
            for item in normalized
            if not _FUTURE_LIMITATION_RE.search(item)
        ]
        if filtered != normalized:
            logger.info(
                "Removed invalid future-looking limitations for past Step 3 period ending %s",
                end_date_value,
            )

        if filtered:
            return filtered

        if has_results:
            return [
                "Recommendations are based on publicly available sources and may miss Instagram audio trends that are not publicly indexed."
            ]

        return [
            "No sufficiently verified trending audio sources were found for the requested niche and research period from the public sources reviewed."
        ]

    @staticmethod
    def _serialize_response(response: Any) -> str:
        if hasattr(response, "model_dump_json"):
            return response.model_dump_json(indent=2)
        return str(response)

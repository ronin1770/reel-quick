"""ARQ worker for creating instagram post data from raw posts."""

from __future__ import annotations

import ast
import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv

from backend.db import get_db
from backend.logger import get_logger
from backend.models.person_bio import PERSON_BIO_COLLECTION
from backend.models.quotes import QUOTES_COLLECTION
from backend.models.raw_posts_data import RAW_POSTS_COLLECTION
from backend.objects.ai_engine import AiEngine
from backend.objects.create_images import BaseImageCreator
from backend.objects.prompt_constants import (
    AI_TYPE_PROMPT_MAP,
    AI_TYPE_REQUIRED_FIELDS,
    AI_TYPE_VARIABLE_MAP,
)

load_dotenv(find_dotenv())

_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now_str() -> str:
    return datetime.utcnow().strftime(_DATETIME_FORMAT)


def _get_worker_logger() -> logging.Logger:
    logger = get_logger(name="instagram_reel_creation_post_worker")
    logger.setLevel(logging.info)
    return logger


def _build_prompt_variables(
    ai_type: str, input_payload: Dict[str, Any], logger: logging.Logger
) -> Dict[str, Any]:
    mapping = AI_TYPE_VARIABLE_MAP.get(ai_type, {})
    variables: Dict[str, Any] = {}
    if not mapping:
        logger.info("No variable mapping found for ai_type=%s", ai_type)
    for input_key, prompt_key in mapping.items():
        if input_key in input_payload:
            variables[prompt_key] = input_payload[input_key]
        else:
            logger.info(
                "Missing input for variable mapping: %s -> %s",
                input_key,
                prompt_key,
            )
    return variables


def _validate_required(
    ai_type: str, input_payload: Dict[str, Any], logger: logging.Logger
) -> bool:
    required = AI_TYPE_REQUIRED_FIELDS.get(ai_type, [])
    missing = [
        field
        for field in required
        if field not in input_payload or str(input_payload[field]).strip() == ""
    ]
    if missing:
        logger.info("Missing fields for %s: %s", ai_type, ", ".join(missing))
        return False
    return True


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*", "", cleaned).strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    return cleaned


def _parse_json(text: str, logger: logging.Logger) -> Optional[Any]:
    if not text:
        return None
    cleaned = _strip_code_fences(text)
    cleaned = cleaned.replace("“", '"').replace("”", '"').replace("’", "'")

    def _try_load(value: str) -> Optional[Any]:
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def _remove_trailing_commas(value: str) -> str:
        return re.sub(r",\s*([}\]])", r"\1", value)

    parsed = _try_load(cleaned)
    if parsed is not None:
        return parsed

    cleaned = _remove_trailing_commas(cleaned)
    parsed = _try_load(cleaned)
    if parsed is not None:
        return parsed

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        block = _remove_trailing_commas(match.group(0))
        parsed = _try_load(block)
        if parsed is not None:
            return parsed
        try:
            parsed = ast.literal_eval(block)
            if isinstance(parsed, (dict, list)):
                return parsed
        except (ValueError, SyntaxError):
            pass

    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        block = _remove_trailing_commas(match.group(0))
        parsed = _try_load(block)
        if parsed is not None:
            return parsed
        try:
            parsed = ast.literal_eval(block)
            if isinstance(parsed, (dict, list)):
                return parsed
        except (ValueError, SyntaxError):
            pass

    try:
        parsed = ast.literal_eval(_remove_trailing_commas(cleaned))
        if isinstance(parsed, (dict, list)):
            return parsed
    except (ValueError, SyntaxError):
        pass

    logger.info("Failed to parse JSON output.")
    return None


def _get_first_value(data: Dict[str, Any], keys: List[str]) -> Optional[Any]:
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_pipe_value(value: Any) -> str:
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return " | ".join(parts)
    if value is None:
        return ""
    return str(value).strip()


def _build_bio_document(
    output: Dict[str, Any],
    fallback: Dict[str, Any],
    code: str,
) -> Dict[str, Any]:
    name = _get_first_value(output, ["name", "person_name"]) or fallback.get("name", "")
    country = _get_first_value(output, ["country"]) or fallback.get("country", "")
    dob = _get_first_value(output, ["DOB", "dob"]) or fallback.get("dob", "")
    excellence_field = _get_first_value(
        output,
        ["excellence_field", "field_of_excellence", "excellence"],
    ) or fallback.get("excellence_field", "")
    challenges_value = _get_first_value(
        output,
        ["challenges", "challenge", "challenges_faced"],
    ) or fallback.get("challenges_faced", "")
    challenges = _normalize_pipe_value(challenges_value)

    return {
        "code": code,
        "name": name,
        "country": country,
        "dob": dob,
        "excellence_field": excellence_field,
        "challenges": challenges,
    }


def _build_quotes_document(
    output: List[Any],
    fallback: Dict[str, Any],
    code: str,
) -> Dict[str, Any]:
    quotes = _normalize_pipe_value(output)
    return {
        "code": code,
        "name": fallback.get("name", ""),
        "country": fallback.get("country", ""),
        "dob": fallback.get("dob", ""),
        "excellence_field": fallback.get("excellence_field", ""),
        "quotes": quotes,
        "quote_image_paths": "",
    }


def _create_quote_images(
    code: str,
    name: str,
    quotes: str,
    logger: logging.Logger,
) -> str:
    output_folder = (
        os.getenv("OUTPUT_FILES_LOCATION")
        or os.getenv("OUTPUT_FOLDER")
        or "./output_files"
    )

    try:
        creator = BaseImageCreator(output_folder=output_folder)
    except Exception:
        logger.info("Failed to initialize image creator for code=%s", code)
        raise

    paths = creator.create_quotes_images(code=code, name=name, quotes=quotes)
    resolved = [str(path.resolve()) for path in paths]
    return " | ".join(resolved)


def _upsert_document(
    db: Any, collection: str, code: str, document: Dict[str, Any], logger: logging.Logger
) -> None:
    now = _now_str()
    update = {
        "$set": {**document, "updated_on": now},
        "$setOnInsert": {"added_on": now},
    }
    db[collection].update_one({"code": code}, update, upsert=True)
    logger.info("Upserted into %s for code=%s", collection, code)


def _mark_raw_post_processed(db: Any, raw_id: Any, logger: logging.Logger) -> None:
    now = _now_str()
    db[RAW_POSTS_COLLECTION].update_one(
        {"_id": raw_id},
        {"$set": {"quote_created": True, "quote_created_on": now, "updated_on": now}},
    )
    logger.info("Marked raw post as processed: %s", raw_id)


async def process_posts(ctx: Dict[str, Any]) -> bool:
    logger = _get_worker_logger()
    db = get_db()

    cursor = db[RAW_POSTS_COLLECTION].find({"quote_created": False})
    total = 0
    success = 0
    failure = 0

    for raw in cursor:
        total += 1
        code = raw.get("code", "")
        if not code:
            logger.info("Skipping raw post with missing code.")
            failure += 1
            continue

        input_payload = {
            "code": code,
            "person_name": raw.get("name", ""),
            "country": raw.get("country", ""),
            "dob": raw.get("dob", ""),
            "fields_of_excellent": raw.get("excellence_field", ""),
            "field_of_excellence": raw.get("excellence_field", ""),
            "summary_of_challenges": raw.get("challenges_faced", ""),
        }

        if not _validate_required("BIO_DETAILS", input_payload, logger):
            failure += 1
            continue
        if not _validate_required("QUOTES", input_payload, logger):
            failure += 1
            continue

        try:
            engine = AiEngine()
        except Exception:
            logger.info("Unable to initialize AI engine.")
            return False

        bio_prompt = AI_TYPE_PROMPT_MAP["BIO_DETAILS"]
        bio_vars = _build_prompt_variables("BIO_DETAILS", input_payload, logger)
        quotes_prompt = AI_TYPE_PROMPT_MAP["QUOTES"]
        quotes_vars = _build_prompt_variables("QUOTES", input_payload, logger)

        try:
            try:
                bio_output = engine.run_prompt(
                    bio_prompt,
                    bio_vars,
                    logger=logger,
                    log_rendered=True,
                )
            except ValueError as exc:
                logger.info(
                    "Failed to render bio prompt for code=%s: %s",
                    code,
                    exc,
                )
                failure += 1
                continue
            logger.info("Bio raw output for code=%s: %s", code, bio_output)
            bio_json = _parse_json(bio_output, logger)
            if not isinstance(bio_json, dict):
                logger.info("Bio output is not a JSON object for code=%s", code)
                failure += 1
                continue

            bio_doc = _build_bio_document(bio_json, raw, code)
            _upsert_document(db, PERSON_BIO_COLLECTION, code, bio_doc, logger)

            try:
                quotes_output = engine.run_prompt(
                    quotes_prompt,
                    quotes_vars,
                    logger=logger,
                    log_rendered=True,
                )
            except ValueError as exc:
                logger.info(
                    "Failed to render quotes prompt for code=%s: %s",
                    code,
                    exc,
                )
                failure += 1
                continue
            logger.info("Quotes raw output for code=%s: %s", code, quotes_output)
            quotes_json = _parse_json(quotes_output, logger)
            if not isinstance(quotes_json, list):
                logger.info("Quotes output is not a JSON list for code=%s", code)
                failure += 1
                continue

            quotes_doc = _build_quotes_document(quotes_json, raw, code)
            if not quotes_doc["quotes"]:
                logger.info("No quotes found for code=%s", code)
                failure += 1
                continue

            try:
                image_paths = _create_quote_images(
                    code=code,
                    name=bio_doc.get("name", "") or raw.get("name", ""),
                    quotes=quotes_doc["quotes"],
                    logger=logger,
                )
            except Exception:
                logger.info("Failed to create quote images for code=%s", code)
                failure += 1
                continue

            if not image_paths:
                logger.info("No quote images created for code=%s", code)
                failure += 1
                continue

            quotes_doc["quote_image_paths"] = image_paths

            _upsert_document(db, QUOTES_COLLECTION, code, quotes_doc, logger)

            _mark_raw_post_processed(db, raw.get("_id"), logger)
            success += 1

            logger.info("Bio details for %s: %s", code, bio_doc)
            logger.info("Quotes for %s: %s", code, quotes_doc["quotes"])
            logger.info("Quote image paths for %s: %s", code, quotes_doc["quote_image_paths"])
            logger.info(
                "Processed raw post payload: %s",
                json.dumps(
                    {
                        "code": code,
                        "bio_details": bio_doc,
                        "quotes": quotes_doc["quotes"],
                        "quote_image_paths": quotes_doc["quote_image_paths"],
                    }
                ),
            )
        except Exception:
            logger.info("Failed to process code=%s", code)
            failure += 1
            continue

    logger.info(
        "Post worker summary: total=%s success=%s failure=%s",
        total,
        success,
        failure,
    )
    if total == 0:
        logger.info("No raw posts found with quote_created=false.")
    return failure == 0


class WorkerSettings:
    functions = [process_posts]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/1")
    )

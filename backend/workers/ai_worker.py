"""ARQ worker for AI engine tasks."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Tuple

from arq.connections import RedisSettings
from dotenv import find_dotenv, load_dotenv
from pymongo.infos import DuplicateKeyError

from backend.db import get_db
from backend.logger import get_logger
from backend.models.raw_posts_data import RAW_POSTS_COLLECTION, RawPostsDataModel
from backend.objects.ai_engine import AiEngine
from backend.objects.prompt_constants import (
    AI_TYPE_PROMPT_MAP,
    AI_TYPE_REQUIRED_FIELDS,
    AI_TYPE_VARIABLE_MAP,
)

load_dotenv(find_dotenv())

def _get_worker_logger() -> logging.Logger:
    logger = get_logger(name="instagram_reel_creation_ai_arq")
    logger.setLevel(logging.INFO)
    return logger


def _normalize_line(line: str) -> str:
    line = line.strip()
    if line.startswith("-"):
        line = line.lstrip("-").strip()
    line = re.sub(r"^\\d+[.)]\\s*", "", line)
    return line


def _looks_like_header(line: str) -> bool:
    lowered = line.lower()
    return (
        "code" in lowered
        and "name" in lowered
        and "country" in lowered
        and "excellence" in lowered
    )


def _parse_monthly_figures(
    output: str, logger: logging.Logger
) -> List[RawPostsDataModel]:
    rows: List[RawPostsDataModel] = []
    found_header = False
    total_lines = 0
    skipped_lines = 0
    parse_failures = 0

    logger.info(
        "Parsing monthly figures output: chars=%s lines=%s",
        len(output),
        output.count("\n") + 1 if output else 0,
    )

    for line_no, raw_line in enumerate(output.splitlines(), start=1):
        total_lines += 1
        line = _normalize_line(raw_line)
        if not line:
            skipped_lines += 1
            continue

        if not found_header:
            if _looks_like_header(line):
                found_header = True
                logger.info("Detected header line for monthly figures.")
            else:
                skipped_lines += 1
            continue

        if line.startswith("---") or line.startswith("**"):
            skipped_lines += 1
            continue
        if "," not in line:
            skipped_lines += 1
            logger.warning(
                "Skipped monthly figures row at line=%s reason=no_comma line=%r",
                line_no,
                raw_line,
            )
            continue

        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 6:
            parse_failures += 1
            logger.warning(
                "Skipped monthly figures row at line=%s reason=insufficient_columns count=%s line=%r",
                line_no,
                len(parts),
                raw_line,
            )
            continue

        code, name, country, dob, excellence_field = parts[:5]
        challenges_faced = ", ".join(parts[5:]).strip()
        if not code or not name:
            parse_failures += 1
            logger.warning(
                "Skipped monthly figures row at line=%s reason=missing_code_or_name code=%r name=%r line=%r",
                line_no,
                code,
                name,
                raw_line,
            )
            continue

        rows.append(
            RawPostsDataModel(
                code=code,
                name=name,
                country=country,
                dob=dob,
                excellence_field=excellence_field,
                challenges_faced=challenges_faced,
            )
        )

    logger.info(
        "Monthly figures parse summary: header_found=%s total_lines=%s rows=%s skipped=%s failures=%s",
        found_header,
        total_lines,
        len(rows),
        skipped_lines,
        parse_failures,
    )

    return rows


def _insert_raw_posts(
    rows: List[RawPostsDataModel], logger: logging.Logger
) -> Tuple[int, int]:
    db = get_db()
    inserted = 0
    skipped = 0
    logger.info("Inserting raw posts rows: count=%s", len(rows))
    for row in rows:
        try:
            db[RAW_POSTS_COLLECTION].insert_one(row.to_bson())
            inserted += 1
        except DuplicateKeyError:
            skipped += 1
            logger.warning(
                "Skipped raw post insert due to duplicate code=%s",
                row.code,
            )
    logger.info(
        "Raw posts insert summary: inserted=%s skipped=%s total=%s",
        inserted,
        skipped,
        len(rows),
    )
    return inserted, skipped


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
    logger.info(
        "Built prompt variables for ai_type=%s: keys=%s",
        ai_type,
        ", ".join(sorted(variables.keys())) if variables else "none",
    )
    return variables


async def process_ai_task(
    ctx: Dict[str, Any], ai_type: str, input_payload: Dict[str, Any]
) -> bool:
    logger = _get_worker_logger()
    logger.info("AI task received: ai_type=%s", ai_type)

    if ai_type not in AI_TYPE_PROMPT_MAP:
        logger.info("Unknown ai_type: %s", ai_type)
        return False

    if not isinstance(input_payload, dict):
        logger.info(
            "Invalid input payload for ai_type=%s type=%s",
            ai_type,
            type(input_payload).__name__,
        )
        return False

    logger.info(
        "Input payload keys: %s",
        ", ".join(sorted(input_payload.keys())) if input_payload else "none",
    )

    required = AI_TYPE_REQUIRED_FIELDS.get(ai_type, [])
    logger.info(
        "Required fields for ai_type=%s: %s",
        ai_type,
        ", ".join(required) if required else "none",
    )
    missing = [
        field
        for field in required
        if field not in input_payload or str(input_payload[field]).strip() == ""
    ]
    if missing:
        logger.info("Missing fields for %s: %s", ai_type, ", ".join(missing))
        return False

    prompt_name = AI_TYPE_PROMPT_MAP[ai_type]
    variables = _build_prompt_variables(ai_type, input_payload, logger)
    logger.info("Running prompt: %s", prompt_name)

    try:
        engine = AiEngine()
        output = engine.run_prompt(prompt_name, variables)
    except Exception:
        logger.info("AI engine failed for %s", ai_type)
        return False
    logger.info(
        "Prompt output summary: chars=%s lines=%s",
        len(output),
        output.count("\n") + 1 if output else 0,
    )

    if ai_type == "MONTHLY_FIGURES":
        rows = _parse_monthly_figures(output, logger)
        if not rows:
            logger.info("No rows parsed for %s", ai_type)
            return False
        inserted, skipped = _insert_raw_posts(rows, logger)
        logger.info(
            "Monthly figures processed. inserted=%s skipped=%s total=%s",
            inserted,
            skipped,
            len(rows),
        )
        return True

    logger.info("No handler implemented for ai_type=%s", ai_type)
    return False


class WorkerSettings:
    functions = [process_ai_task]
    redis_settings = RedisSettings.from_dsn(
        os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )

"""Catalog and validation helpers for video transitions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from pymongo.database import Database

from backend.models.available_transition import AVAILABLE_TRANSITIONS_COLLECTION


class AvailableTransitionService:
    """Provide the transition catalog used by the video creation flow."""

    DEFAULT_TRANSITIONS: Sequence[str] = (
        "fade",
        "dissolve",
        "fadeblack",
        "fadewhite",
        "wipeleft",
        "wiperight",
        "slideleft",
        "slideright",
        "circleopen",
        "circleclose",
    )

    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()

    @classmethod
    def is_supported_name(cls, value: str) -> bool:
        return cls.normalize_name(value) in set(cls.DEFAULT_TRANSITIONS)

    @classmethod
    def ensure_seed_data(cls, db: Database) -> None:
        collection = db[AVAILABLE_TRANSITIONS_COLLECTION]
        now = datetime.utcnow()
        for transition_name in cls.DEFAULT_TRANSITIONS:
            if collection.find_one({"name": transition_name}) is not None:
                continue
            collection.insert_one(
                {
                    "id": transition_name,
                    "name": transition_name,
                    "active": True,
                    "date_added": now,
                    "date_updated": now,
                }
            )

    @classmethod
    def list_transitions(
        cls,
        db: Database,
        *,
        active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        query: Dict[str, Any] = {}
        if active is not None:
            query["active"] = active
        return list(db[AVAILABLE_TRANSITIONS_COLLECTION].find(query).sort("name", 1))

    @classmethod
    def get_transition_by_name(
        cls,
        db: Database,
        name: str,
    ) -> Optional[Dict[str, Any]]:
        normalized_name = cls.normalize_name(name)
        return db[AVAILABLE_TRANSITIONS_COLLECTION].find_one({"name": normalized_name})

    @classmethod
    def resolve_transition_name(
        cls,
        db: Database,
        transition_name: Optional[str],
        *,
        allow_default: bool,
        require_active: bool = True,
    ) -> str:
        if transition_name is None:
            if not allow_default:
                raise ValueError("transition_name is required")
            return cls.default_transition_name(db)

        normalized_name = cls.normalize_name(transition_name)
        doc = cls.get_transition_by_name(db, normalized_name)
        if doc is None:
            raise ValueError("transition_name is not available")
        if require_active and not doc.get("active", False):
            raise ValueError("transition_name is inactive")
        return normalized_name

    @classmethod
    def default_transition_name(cls, db: Database) -> str:
        preferred = cls.get_transition_by_name(db, "fade")
        if preferred is not None and preferred.get("active", False):
            return "fade"

        fallback = db[AVAILABLE_TRANSITIONS_COLLECTION].find_one(
            {"active": True},
            sort=[("name", 1)],
        )
        if fallback is not None:
            return str(fallback["name"])
        raise ValueError("No active transitions are available")

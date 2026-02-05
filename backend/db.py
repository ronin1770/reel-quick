"""MongoDB client and initialization helpers."""

from __future__ import annotations

import os
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

DB_NAME = "instagram_reel_creator"
DEFAULT_URI = "mongodb://localhost:27017"

_client: Optional[MongoClient] = None


def get_client() -> MongoClient:
    """Return a singleton MongoClient instance."""
    global _client
    if _client is None:
        load_dotenv(find_dotenv())
        uri = os.getenv("MONGODB_URI", DEFAULT_URI)
        _client = MongoClient(uri)
    return _client


def get_db() -> Database:
    """Return the instagram_reel_creator database handle."""
    return get_client()[DB_NAME]


def init_db() -> Database:
    """Ensure the database and collections exist."""
    db = get_db()
    existing = set(db.list_collection_names())
    for name in ("videos", "video_parts", "raw_posts_data"):
        if name not in existing:
            db.create_collection(name)

    db.videos.create_index("video_id", unique=True)
    db.raw_posts_data.create_index("code", unique=True)
    return db


def close_client() -> None:
    """Close the cached MongoClient, if any."""
    global _client
    if _client is not None:
        _client.close()
        _client = None


if __name__ == "__main__":
    init_db()

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import asdict
from html import unescape
import json
from pathlib import Path
import re
import time

import requests

from core.config import Settings


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    if not isinstance(payload, dict):
        raise ValueError("Crossref payload must be a JSON object.")

    message = payload.get("message")
    if not isinstance(message, dict):
        raise ValueError("Crossref payload is missing the 'message' object.")

    items = message.get("items")
    if not isinstance(items, list):
        raise ValueError("Crossref payload is missing the 'message.items' list.")

    def normalize_text(value: object) -> str:
        text = unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(text.split())

    def first_text(value: object) -> str:
        if isinstance(value, list):
            return normalize_text(value[0]) if value else ""
        return normalize_text(value)

    def date_from_item(item: dict, *keys: str) -> str:
        for key in keys:
            value = item.get(key)
            if not isinstance(value, dict):
                continue
            date_parts = value.get("date-parts")
            if isinstance(date_parts, list) and date_parts and isinstance(date_parts[0], list):
                parts = date_parts[0]
                if parts and isinstance(parts[0], int):
                    year = parts[0]
                    month = parts[1] if len(parts) > 1 and isinstance(parts[1], int) else 1
                    day = parts[2] if len(parts) > 2 and isinstance(parts[2], int) else 1
                    return f"{year:04d}-{month:02d}-{day:02d}"
            date_time = value.get("date-time")
            if isinstance(date_time, str) and date_time:
                return date_time[:10]
        return ""

    records: list[PaperRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        paper_id = normalize_text(item.get("DOI")).lower()
        title = first_text(item.get("title"))
        summary = normalize_text(item.get("abstract"))
        if not paper_id or not title or not summary:
            continue

        authors: list[str] = []
        for author in item.get("author", []):
            if not isinstance(author, dict):
                continue
            name = " ".join(
                part
                for part in (
                    normalize_text(author.get("given")),
                    normalize_text(author.get("family")),
                )
                if part
            )
            if name:
                authors.append(name)

        categories = [
            normalized
            for subject in item.get("subject", [])
            if (normalized := normalize_text(subject))
        ]
        if not categories:
            categories = ["Uncategorized"]

        published = date_from_item(
            item,
            "published",
            "published-online",
            "published-print",
            "issued",
            "created",
        )
        updated = date_from_item(item, "updated", "created", "published") or published
        if not published:
            continue

        abs_url = normalize_text(item.get("URL")) or f"https://doi.org/{paper_id}"
        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=categories[0],
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=abs_url,
                comment=f"Crossref record {paper_id}",
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    raw_response_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)

    def load_snapshot() -> dict:
        if not raw_response_path.exists():
            raise RuntimeError(
                "Crossref request failed and no local snapshot exists at "
                f"{raw_response_path}."
            )
        with raw_response_path.open("r", encoding="utf-8") as file:
            snapshot = json.load(file)
        if not isinstance(snapshot, dict):
            raise ValueError(f"Local Crossref snapshot is not a JSON object: {raw_response_path}")
        return snapshot

    payload: dict
    if not settings.refresh_source:
        payload = load_snapshot()
    else:
        params = {
            "query": settings.source_query,
            "filter": settings.source_filter,
            "rows": settings.max_results,
        }
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = requests.get(
                    "https://api.crossref.org/works",
                    params=params,
                    headers={"User-Agent": "day10-data-observability-lab/0.1"},
                    timeout=20,
                )
                if response.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(
                        f"Crossref returned HTTP {response.status_code}", response=response
                    )
                response.raise_for_status()
                candidate = response.json()
                if not isinstance(candidate, dict):
                    raise ValueError("Crossref API did not return a JSON object.")
                payload = candidate
                break
            except (requests.RequestException, ValueError) as error:
                last_error = error
                if attempt < 2:
                    time.sleep(2**attempt)
        else:
            try:
                payload = load_snapshot()
            except RuntimeError as snapshot_error:
                raise RuntimeError("Unable to fetch Crossref data or load its local snapshot.") from last_error

    with raw_response_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    records = parse_crossref_payload(payload)
    with raw_records_path.open("w", encoding="utf-8") as file:
        json.dump([asdict(record) for record in records], file, ensure_ascii=False, indent=2)
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, list):
        raise ValueError(f"Raw records must be a JSON list: {path}")

    try:
        return [PaperRecord(**record) for record in payload if isinstance(record, dict)]
    except TypeError as error:
        raise ValueError(f"Raw records do not match PaperRecord schema: {path}") from error

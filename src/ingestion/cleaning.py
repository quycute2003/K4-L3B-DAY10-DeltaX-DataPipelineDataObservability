from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


CLEAN_COLUMNS = [
    "paper_id",
    "title",
    "summary",
    "authors",
    "categories",
    "primary_category",
    "published",
    "updated",
    "abs_url",
    "pdf_url",
    "comment",
    "age_days",
    "authors_joined",
    "categories_joined",
    "summary_chars",
    "text_for_embedding",
]


def _clean_list(values: list[str] | None) -> list[str]:
    seen: list[str] = []
    for value in values or []:
        cleaned = normalize_whitespace(str(value))
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return seen


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = pd.to_datetime(normalize_whitespace(str(value)), errors="coerce", utc=True)
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _build_embedding_text(title: str, authors: str, published: str, categories: str, summary: str) -> str:
    return "\n".join(
        [
            f"Title: {title}",
            f"Authors: {authors}",
            f"Published: {published}",
            f"Categories: {categories}",
            f"Summary: {summary}",
        ]
    )


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding."""
    if run_date.tzinfo is None:
        run_date = run_date.replace(tzinfo=UTC)

    rows: list[dict] = []
    for record in records:
        paper_id = normalize_whitespace(record.paper_id or "")
        title = normalize_whitespace(record.title or "")
        summary = normalize_whitespace(record.summary or "")
        published_dt = _parse_date(record.published)
        if not paper_id or not title or not summary or published_dt is None:
            continue
        updated_dt = _parse_date(record.updated) or published_dt

        authors = _clean_list(record.authors)
        categories = _clean_list(record.categories)
        primary_category = normalize_whitespace(record.primary_category or "") or (categories[0] if categories else "")
        published = published_dt.date().isoformat()
        authors_joined = compact_join(authors)
        categories_joined = compact_join(categories)

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": primary_category,
                "published": published,
                "updated": updated_dt.date().isoformat(),
                "abs_url": normalize_whitespace(record.abs_url or ""),
                "pdf_url": normalize_whitespace(record.pdf_url or ""),
                "comment": normalize_whitespace(record.comment or ""),
                "age_days": (run_date - published_dt).days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": _build_embedding_text(title, authors_joined, published, categories_joined, summary),
            }
        )

    df = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    if df.empty:
        return df

    # Keep the most recently updated version of each paper.
    df = df.sort_values(["paper_id", "updated"], ascending=[True, False])
    df = df.drop_duplicates(subset="paper_id", keep="first")
    df = df.sort_values(["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    df["age_days"] = df["age_days"].astype(int)
    df["summary_chars"] = df["summary_chars"].astype(int)
    return df

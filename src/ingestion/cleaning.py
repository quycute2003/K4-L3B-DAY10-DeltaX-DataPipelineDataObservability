from __future__ import annotations

from datetime import datetime
from html import unescape
import re

import pandas as pd

from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a dataframe ready for embedding and quality checks."""
    columns = [
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
        "authors_joined",
        "categories_joined",
        "summary_chars",
        "age_days",
        "text_for_embedding",
    ]
    if not records:
        return pd.DataFrame(columns=columns)

    def normalize_text(value: object) -> str:
        text = unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", " ", text)
        return " ".join(text.split())

    def normalize_list(value: object) -> list[str]:
        values = value if isinstance(value, list) else [value]
        normalized: list[str] = []
        for item in values:
            text = normalize_text(item)
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    frame = pd.DataFrame(
        [
            {
                "paper_id": normalize_text(record.paper_id).lower(),
                "title": normalize_text(record.title),
                "summary": normalize_text(record.summary),
                "authors": normalize_list(record.authors),
                "categories": normalize_list(record.categories),
                "primary_category": normalize_text(record.primary_category),
                "published": normalize_text(record.published),
                "updated": normalize_text(record.updated),
                "abs_url": normalize_text(record.abs_url),
                "pdf_url": normalize_text(record.pdf_url),
                "comment": normalize_text(record.comment),
            }
            for record in records
        ]
    )

    frame = frame.drop_duplicates(subset="paper_id", keep="first")
    frame = frame.loc[
        frame["paper_id"].ne("") & frame["title"].ne("") & frame["summary"].ne("")
    ].copy()
    parsed_published = pd.to_datetime(frame["published"], errors="coerce", utc=True)
    frame = frame.loc[parsed_published.notna()].copy()
    parsed_published = parsed_published.loc[frame.index]

    parsed_updated = pd.to_datetime(frame["updated"], errors="coerce", utc=True)
    parsed_updated = parsed_updated.where(parsed_updated.notna(), parsed_published)
    frame["published"] = parsed_published.dt.strftime("%Y-%m-%d")
    frame["updated"] = parsed_updated.dt.strftime("%Y-%m-%d")

    run_timestamp = pd.Timestamp(run_date)
    if run_timestamp.tzinfo is None:
        run_timestamp = run_timestamp.tz_localize("UTC")
    else:
        run_timestamp = run_timestamp.tz_convert("UTC")
    frame["age_days"] = (run_timestamp.normalize() - parsed_published.dt.normalize()).dt.days.astype(int)

    frame["authors_joined"] = frame["authors"].map(lambda authors: ", ".join(authors) or "Unknown")
    frame["categories"] = frame["categories"].map(
        lambda categories: categories or ["Uncategorized"]
    )
    frame["categories_joined"] = frame["categories"].map(
        lambda categories: ", ".join(categories)
    )
    frame["primary_category"] = frame.apply(
        lambda row: row["primary_category"] or row["categories"][0], axis=1
    )
    frame["summary_chars"] = frame["summary"].str.len().astype(int)
    frame["text_for_embedding"] = frame.apply(
        lambda row: "\n".join(
            (
                f"Title: {row['title']}",
                f"Authors: {row['authors_joined']}",
                f"Published: {row['published']}",
                f"Categories: {row['categories_joined']}",
                f"Summary: {row['summary']}",
            )
        ),
        axis=1,
    )

    return frame.loc[:, columns].sort_values(
        ["published", "paper_id"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)

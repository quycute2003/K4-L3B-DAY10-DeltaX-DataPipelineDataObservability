from __future__ import annotations

from math import ceil
from pathlib import Path

import pandas as pd

from core.utils import write_json


NOISE = "[CORRUPTED] xqz-9187 meaningless noise !!!"


def _embedding_text(row: pd.Series) -> str:
    return "\n".join(
        (
            f"Title: {row['title']}",
            f"Authors: {row['authors_joined']}",
            f"Published: {row['published']}",
            f"Categories: {row['categories_joined']}",
            f"Summary: {row['summary']}",
        )
    )


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Apply six deterministic corruption scenarios and write a row-level audit log."""
    required = {
        "paper_id", "title", "summary", "published", "age_days",
        "authors_joined", "categories_joined", "text_for_embedding",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing columns: {sorted(missing)}")
    if df.empty:
        raise ValueError("Cannot corrupt an empty dataframe.")

    corrupted = df.copy(deep=True).reset_index(drop=True)
    events: list[dict] = []

    latest = pd.to_datetime(corrupted["published"], errors="coerce", utc=True)
    drop_count = min(ceil(len(corrupted) * 0.2), len(corrupted) - 1)
    drop_indices = latest.sort_values(ascending=False, kind="stable").index[:drop_count]
    for index in drop_indices:
        row = corrupted.loc[index]
        events.append({
            "type": "drop_latest_records",
            "paper_id": str(row["paper_id"]),
            "before": {"published": str(row["published"])},
            "after": None,
        })
    corrupted = corrupted.drop(index=drop_indices).reset_index(drop=True)

    # The same fixed positions are used on every run. Disjoint selections make
    # each failure mode visible in the audit log and quality results.
    for index in range(len(corrupted)):
        mode = index % 5
        paper_id = str(corrupted.at[index, "paper_id"])
        if mode == 0:
            before = str(corrupted.at[index, "summary"])
            corrupted.at[index, "summary"] = ""
            corrupted.at[index, "summary_chars"] = 0
            events.append({"type": "blank_summary", "paper_id": paper_id, "before": before, "after": ""})
        elif mode == 1:
            before = str(corrupted.at[index, "summary"])
            after = f"{NOISE} {before}"
            corrupted.at[index, "summary"] = after
            corrupted.at[index, "summary_chars"] = len(after)
            events.append({"type": "inject_noise", "paper_id": paper_id, "before": before, "after": after})
        elif mode == 2:
            before = str(corrupted.at[index, "title"])
            after = before[:7]
            corrupted.at[index, "title"] = after
            events.append({"type": "truncate_title", "paper_id": paper_id, "before": before, "after": after})
        elif mode in (3, 4):
            before = str(corrupted.at[index, "published"])
            parsed = pd.to_datetime(before, errors="raise")
            after = (parsed - pd.Timedelta(days=365)).date().isoformat()
            corrupted.at[index, "published"] = after
            corrupted.at[index, "age_days"] = int(corrupted.at[index, "age_days"]) + 365
            events.append({"type": "stale_date", "paper_id": paper_id, "before": before, "after": after})

    corrupted["text_for_embedding"] = corrupted.apply(_embedding_text, axis=1)
    duplicate_indices = [index for index in range(len(corrupted)) if index % 5 == 4]
    if not duplicate_indices:
        duplicate_indices = [len(corrupted) - 1]
    duplicates = corrupted.iloc[duplicate_indices].copy()
    for _, row in duplicates.iterrows():
        events.append({
            "type": "duplicate_rows",
            "paper_id": str(row["paper_id"]),
            "before": 1,
            "after": 2,
        })
    corrupted = pd.concat([corrupted, duplicates], ignore_index=True)

    write_json(Path(output_log_path), {
        "input_rows": len(df),
        "output_rows": len(corrupted),
        "events": events,
    })
    return corrupted

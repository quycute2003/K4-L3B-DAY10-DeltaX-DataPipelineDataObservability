from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import compact_join, first_sentence, normalize_whitespace, write_json


TEST_SET_SIZE = 10
MIN_DOCUMENTS = TEST_SET_SIZE
# 10 questions spread across 4 types: 3 summary, 3 authors, 2 date, 2 categories.
QUESTION_PLAN = ["summary", "authors", "date", "categories"] * 2 + ["summary", "authors"]

# Phrasing must stay in sync with the keyword routing in `retrieval.qa._extract_answer`.
QUESTION_TEMPLATES = {
    "summary": "What is the summary of the paper '{title}'?",
    "authors": "Who authored the paper '{title}'?",
    "date": "When was the paper '{title}' published?",
    "categories": "What categories does the paper '{title}' belong to?",
}


def _as_text(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, (list, tuple)):
        return compact_join(normalize_whitespace(str(item)) for item in value)
    return "" if value is None or (isinstance(value, float) and pd.isna(value)) else normalize_whitespace(str(value))


def _ground_truth(row: pd.Series, question_type: str) -> str:
    if question_type == "summary":
        return first_sentence(_as_text(row["summary"]))
    if question_type == "authors":
        return _as_text(row.get("authors_joined")) or _as_text(row.get("authors"))
    if question_type == "date":
        return _as_text(row["published"])[:10]
    return _as_text(row.get("categories_joined")) or _as_text(row.get("categories"))


def _select_papers(df: pd.DataFrame, count: int) -> pd.DataFrame:
    # The QA title lookup extracts the title between single quotes, so skip titles containing one.
    candidates = df[
        df["title"].notna()
        & ~df["title"].astype(str).str.contains("'")
        & df["summary"].notna()
        & df["paper_id"].notna()
    ]
    candidates = candidates.drop_duplicates(subset="paper_id").sort_values("paper_id").reset_index(drop=True)
    if len(candidates) < count:
        raise ValueError(f"Need at least {count} usable documents to build the test set, found {len(candidates)}.")
    # Spread picks evenly across the corpus instead of taking the first N papers.
    step = len(candidates) / count
    return candidates.iloc[[int(i * step) for i in range(count)]].reset_index(drop=True)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a ground-truth evaluation set from the cleaned dataframe and save it as JSON."""
    if len(df) < MIN_DOCUMENTS:
        raise ValueError(f"Need at least {MIN_DOCUMENTS} documents to build the test set, found {len(df)}.")

    papers = _select_papers(df, TEST_SET_SIZE)
    test_set: list[dict[str, Any]] = []
    for index, (question_type, (_, row)) in enumerate(zip(QUESTION_PLAN, papers.iterrows()), start=1):
        title = _as_text(row["title"])
        test_set.append(
            {
                "id": f"eval_{index:03d}",
                "question_type": question_type,
                "question": QUESTION_TEMPLATES[question_type].format(title=title),
                "ground_truth": _ground_truth(row, question_type),
                "ground_truth_doc_ids": [_as_text(row["paper_id"])],
            }
        )

    write_json(Path(output_path), test_set)
    return test_set

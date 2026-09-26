from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import pandas as pd

from core.config import Settings
from core.utils import now_utc, safe_slug, write_json


MIN_ROWS = 5
MAX_ROWS = 5000
REQUIRED_COLUMNS = ["paper_id", "title", "text_for_embedding"]
MIN_SUMMARY_CHARS = 30
MAX_STALE_RATIO = 0.25


def _quality_report_path(settings: Settings, report_name: str) -> Path:
    named_paths = {
        "baseline": settings.paths.baseline_quality_report,
        "corrupted": settings.paths.corrupted_quality_report,
    }
    return named_paths.get(report_name, settings.paths.quality_dir / f"{safe_slug(report_name)}_quality_report.json")


def _age_days(df: pd.DataFrame) -> pd.Series:
    if "age_days" in df.columns:
        return pd.to_numeric(df["age_days"], errors="coerce")
    published = pd.to_datetime(df.get("published"), errors="coerce", utc=True)
    return (now_utc() - published).dt.days


def evaluate_freshness_sla(df: pd.DataFrame, settings: Settings) -> dict[str, Any]:
    """Flag the dataset as stale when too many rows are older than the freshness threshold."""
    threshold = settings.freshness_threshold_days
    ages = _age_days(df)
    total_rows = int(len(df))
    # Rows whose age cannot be computed count as stale.
    stale_rows = int((ages.isna() | (ages > threshold)).sum())
    stale_ratio = stale_rows / total_rows if total_rows else 1.0

    published = pd.to_datetime(df["published"], errors="coerce") if "published" in df.columns else pd.Series(dtype="datetime64[ns]")
    latest = published.max()
    oldest = published.min()
    return {
        "threshold_days": threshold,
        "max_stale_ratio": MAX_STALE_RATIO,
        "latest_published": None if pd.isna(latest) else latest.date().isoformat(),
        "oldest_published": None if pd.isna(oldest) else oldest.date().isoformat(),
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "is_fresh": total_rows > 0 and stale_ratio <= MAX_STALE_RATIO,
    }


def _build_expectations() -> list[Any]:
    expectations: list[Any] = [
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=MIN_ROWS, max_value=MAX_ROWS),
    ]
    expectations += [gx.expectations.ExpectColumnValuesToNotBeNull(column=column) for column in REQUIRED_COLUMNS]
    expectations += [
        gx.expectations.ExpectColumnValuesToBeUnique(column="paper_id"),
        gx.expectations.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=MIN_SUMMARY_CHARS),
    ]
    return expectations


def _summarize_result(result: Any) -> dict[str, Any]:
    config = result.expectation_config
    observed = result.result or {}
    return {
        "expectation": config.type,
        "column": config.kwargs.get("column"),
        "success": bool(result.success),
        "observed_value": observed.get("observed_value"),
        "unexpected_count": observed.get("unexpected_count"),
        "unexpected_percent": observed.get("unexpected_percent"),
        "partial_unexpected_list": [str(value) for value in observed.get("partial_unexpected_list", [])[:10]],
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Validate the clean dataframe with GX 1.x expectations plus a freshness SLA."""
    missing_columns = [column for column in [*REQUIRED_COLUMNS, "summary"] if column not in df.columns]
    checks: list[dict[str, Any]] = [
        {"expectation": "expect_column_to_exist", "column": column, "success": False} for column in missing_columns
    ]

    if not missing_columns:
        context = gx.get_context(mode="ephemeral")
        data_source = context.data_sources.add_pandas(name="papers_source")
        data_asset = data_source.add_dataframe_asset(name="papers_asset")
        batch_def = data_asset.add_batch_definition_whole_dataframe("papers_batch")
        batch = batch_def.get_batch(batch_parameters={"dataframe": df})
        checks += [_summarize_result(batch.validate(expectation)) for expectation in _build_expectations()]

    freshness = evaluate_freshness_sla(df, settings)
    expectations_success = all(check["success"] for check in checks)
    report = {
        "report_name": report_name,
        "generated_at": now_utc().isoformat(),
        "row_count": int(len(df)),
        "success": expectations_success and freshness["is_fresh"],
        "expectations_success": expectations_success,
        "failed_checks": [check["expectation"] for check in checks if not check["success"]],
        "checks": checks,
        "freshness": freshness,
    }
    report_path = _quality_report_path(settings, report_name)
    write_json(report_path, report)
    report["report_path"] = str(report_path)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Write the freshness SLA summary to `report_path` and return it."""
    report = {"generated_at": now_utc().isoformat(), **evaluate_freshness_sla(df, settings)}
    write_json(Path(report_path), report)
    return report

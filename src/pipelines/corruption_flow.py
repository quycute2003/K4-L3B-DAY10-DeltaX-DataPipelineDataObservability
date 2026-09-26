from __future__ import annotations

from typing import Any
import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import evaluate_freshness_sla, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import run_phase1_pipeline
from retrieval.index import LocalEmbeddingIndex


def repair_from_raw_snapshot(settings: Settings) -> pd.DataFrame:
    """Repair and restore clean dataset from the immutable raw snapshot.

    Demonstrates idempotent self-healing by reconstructing clean data from source.
    """
    raw_path = settings.paths.raw_records_json
    if raw_path.exists():
        records = load_raw_records(raw_path)
    else:
        records = fetch_source_records(settings)

    if not records:
        raise ValueError("Cannot repair: raw records are empty or missing.")

    repaired_df = build_clean_dataframe(records, now_utc())
    if repaired_df.empty:
        raise ValueError("Repair cleaning produced an empty dataframe.")
    return repaired_df


def run_corruption_flow_pipeline(settings: Settings) -> dict[str, Any]:
    """Execute corruption flow: corrupt -> evaluate -> idempotent repair -> evaluate -> compare report."""
    # 1. Ensure baseline exists
    if not (
        settings.paths.clean_json.exists()
        and settings.paths.baseline_metrics.exists()
        and settings.paths.eval_testset.exists()
    ):
        run_phase1_pipeline(settings)

    clean_df = pd.read_json(settings.paths.clean_json)
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    test_set_path = settings.paths.eval_testset

    baseline_quality = (
        read_json(settings.paths.baseline_quality_report)
        if settings.paths.baseline_quality_report.exists()
        else None
    )
    baseline_freshness = (
        read_json(settings.paths.freshness_report)
        if settings.paths.freshness_report.exists()
        else None
    )

    # 2. Corrupt dataset
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # 3. Build corrupted index & evaluate
    corrupted_index = LocalEmbeddingIndex.build(
        corrupted_df, settings, settings.paths.corrupted_embeddings_json
    )
    corrupted_eval = evaluate_pipeline(
        settings,
        corrupted_index,
        test_set_path,
        settings.paths.corrupted_metrics,
        settings.paths.corrupted_answers,
    )

    # 4. Observability checks on corrupted data
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = evaluate_freshness_sla(corrupted_df, settings)

    # 5. Repair dataset from raw snapshot
    repaired_df = repair_from_raw_snapshot(settings)

    # Verify idempotency by running repair a second time
    repaired_df_check = repair_from_raw_snapshot(settings)
    assert len(repaired_df) == len(repaired_df_check), (
        "Repair idempotence check failed: row count mismatch"
    )
    assert list(repaired_df["paper_id"]) == list(repaired_df_check["paper_id"]), (
        "Repair idempotence check failed: paper_id mismatch"
    )

    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    # 6. Build repaired index & evaluate
    repaired_index = LocalEmbeddingIndex.build(
        repaired_df, settings, settings.paths.repaired_embeddings_json
    )
    repaired_eval = evaluate_pipeline(
        settings,
        repaired_index,
        test_set_path,
        settings.paths.repaired_metrics,
        settings.paths.repaired_answers,
    )

    # 7. Observability checks on repaired data
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = evaluate_freshness_sla(repaired_df, settings)

    # 8. Generate comparison report
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted_metrics": corrupted_eval.summary,
        "repaired_metrics": repaired_eval.summary,
        "corrupted_quality": corrupted_quality,
        "repaired_quality": repaired_quality,
        "corrupted_freshness": corrupted_freshness,
        "repaired_freshness": repaired_freshness,
        "baseline_quality": baseline_quality,
        "baseline_freshness": baseline_freshness,
    }


def main() -> None:
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

    settings = load_settings()
    results = run_corruption_flow_pipeline(settings)
    bm = results["baseline_metrics"]
    cm = results["corrupted_metrics"]
    rm = results["repaired_metrics"]
    cq = results["corrupted_quality"]
    rq = results["repaired_quality"]
    cf = results["corrupted_freshness"]
    rf = results["repaired_freshness"]

    print("\n" + "=" * 76)
    print(" BANG DOI CHIEU HIEU NANG: BASELINE vs CORRUPTED vs REPAIRED")
    print("=" * 76)
    print(f"{'Chi so / Tin hieu':<25} | {'Baseline':<14} | {'Corrupted':<14} | {'Repaired':<14}")
    print("-" * 76)
    print(f"{'Retrieval Hit Rate':<25} | {bm.get('retrieval_hit_rate', 0):<14.3f} | {cm.get('retrieval_hit_rate', 0):<14.3f} | {rm.get('retrieval_hit_rate', 0):<14.3f}")
    print(f"{'Mean Token F1':<25} | {bm.get('mean_token_f1', 0):<14.3f} | {cm.get('mean_token_f1', 0):<14.3f} | {rm.get('mean_token_f1', 0):<14.3f}")
    print(f"{'Judge Accuracy':<25} | {bm.get('judge_accuracy', 0):<14.3f} | {cm.get('judge_accuracy', 0):<14.3f} | {rm.get('judge_accuracy', 0):<14.3f}")
    print(f"{'Mean Judge Score':<25} | {bm.get('mean_judge_score', 0):<14.2f} | {cm.get('mean_judge_score', 0):<14.2f} | {rm.get('mean_judge_score', 0):<14.2f}")
    print(f"{'Quality Gate Pass':<25} | {'True' if (results.get('baseline_quality') or {}).get('success', True) else 'False':<14} | {str(cq.get('success', False)):<14} | {str(rq.get('success', True)):<14}")
    print(f"{'Freshness SLA Pass':<25} | {'True' if (results.get('baseline_freshness') or {}).get('is_fresh', True) else 'False':<14} | {str(cf.get('is_fresh', False)):<14} | {str(rf.get('is_fresh', True)):<14}")
    print("=" * 76)
    print(f"Bao cao doi chieu da duoc ghi tai: {settings.paths.comparison_report}")


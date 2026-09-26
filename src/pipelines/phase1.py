from __future__ import annotations

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def run_phase1_pipeline(settings: Settings) -> dict:
    """Build and evaluate the baseline from the preserved Crossref source."""
    records = fetch_source_records(settings)
    if not records:
        raise ValueError("Crossref source contains no usable records.")

    clean_df = build_clean_dataframe(records, now_utc())
    if clean_df.empty:
        raise ValueError("Cleaning removed every source record.")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    if not quality["success"]:
        raise ValueError(
            "Baseline data failed the quality/freshness gate; "
            f"see {settings.paths.baseline_quality_report}"
        )

    if settings.refresh_source or settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, settings.paths.eval_testset)
    else:
        test_set = read_json(settings.paths.eval_testset)
        indexed_ids = set(clean_df["paper_id"])
        if not isinstance(test_set, list) or not test_set or any(
            not set(item.get("ground_truth_doc_ids", [])).issubset(indexed_ids)
            for item in test_set
        ):
            test_set = build_test_set(clean_df, settings.paths.eval_testset)

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    evaluation = evaluate_pipeline(
        settings,
        index,
        settings.paths.eval_testset,
        settings.paths.baseline_metrics,
        settings.paths.baseline_answers,
    )
    generate_phase1_report(
        settings.paths.baseline_report,
        {
            "source": settings.source_api,
            "raw_records": len(records),
            "clean_records": len(clean_df),
            "indexed_documents": len(index.documents),
            "test_questions": len(test_set),
        },
        evaluation.summary,
        quality,
        freshness,
    )
    return {
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "test_questions": len(test_set),
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
    }


def main() -> None:
    result = run_phase1_pipeline(load_settings())
    print(
        f"Baseline: {result['clean_records']} papers, "
        f"{result['test_questions']} questions, "
        f"hit rate={result['metrics']['retrieval_hit_rate']:.3f}, "
        f"token F1={result['metrics']['mean_token_f1']:.3f}, "
        f"quality={result['quality']['success']}"
    )

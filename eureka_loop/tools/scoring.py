def score_candidate(eval_metrics: dict) -> float:
    return float(eval_metrics["avg_return"])

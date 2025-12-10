"""Trajectory Evaluator

GT軌跡のすべての滞在地点で許容時間内に検出できた場合のみ、
正しく推定できたと判定する軌跡ベース評価モジュール。
"""

from .domain import (
    GroundTruthStay,
    EstimatedStay,
    GroundTruthTrajectory,
    EstimatedTrajectory,
    StayEvaluation,
    EvaluationResult,
    OverallMetrics,
)
from .usecase import (
    evaluate_trajectories,
    EvaluationConfig,
)
from .infrastructure import (
    load_ground_truth_trajectories,
    load_estimated_trajectories,
    save_evaluation_result,
    save_evaluation_logs,
)

__all__ = [
    # Domain
    "GroundTruthStay",
    "EstimatedStay",
    "GroundTruthTrajectory",
    "EstimatedTrajectory",
    "StayEvaluation",
    "EvaluationResult",
    "OverallMetrics",
    # Usecase
    "evaluate_trajectories",
    "EvaluationConfig",
    # Infrastructure
    "load_ground_truth_trajectories",
    "load_estimated_trajectories",
    "save_evaluation_result",
    "save_evaluation_logs",
]

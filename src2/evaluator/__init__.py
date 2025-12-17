"""Trajectory Evaluator（時間ビニング方式）

GT・Est両方の軌跡に同じ時間ビニングルールを適用し、
同じルート名の軌跡を同一ルートとしてカウントする評価モジュール。
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

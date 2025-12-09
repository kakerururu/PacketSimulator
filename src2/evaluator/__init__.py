"""Trajectory Evaluator

Ground Truth軌跡とEstimated軌跡を1対1でマッチングし、精度を評価するモジュール。
"""

from .domain import (
    GroundTruthStay,
    EstimatedStay,
    GroundTruthTrajectory,
    EstimatedTrajectory,
    MatchedPair,
    StayComparison,
    UnmatchedTrajectory,
    EvaluationResult,
    OverallMetrics,
)
from .usecase import (
    evaluate_trajectories,
    EvaluationConfig,
    check_stay_match,
    check_trajectory_match,
)
from .infrastructure import (
    load_ground_truth_trajectories,
    load_estimated_trajectories,
    save_evaluation_result,
)

__all__ = [
    # Domain
    "GroundTruthStay",
    "EstimatedStay",
    "GroundTruthTrajectory",
    "EstimatedTrajectory",
    "MatchedPair",
    "StayComparison",
    "UnmatchedTrajectory",
    "EvaluationResult",
    "OverallMetrics",
    # Usecase
    "evaluate_trajectories",
    "EvaluationConfig",
    "check_stay_match",
    "check_trajectory_match",
    # Infrastructure
    "load_ground_truth_trajectories",
    "load_estimated_trajectories",
    "save_evaluation_result",
]

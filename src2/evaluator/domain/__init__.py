"""Evaluator domain models

このモジュールは評価に使用するドメインモデル（データ構造）を提供する。

軌跡モデル (trajectory.py):
    - GroundTruthStay: GT滞在情報
    - EstimatedStay: Est滞在情報
    - GroundTruthTrajectory: GT軌跡
    - EstimatedTrajectory: Est軌跡

評価モデル (evaluation.py):
    - EvaluationConfig: 評価設定
    - RouteEvaluation: ルート評価結果（内部用）
    - StayEvaluation: ルート評価結果（出力用）
    - OverallMetrics: 全体評価指標
    - EvaluationResult: 評価結果全体
"""

from .trajectory import (
    GroundTruthStay,
    EstimatedStay,
    GroundTruthTrajectory,
    EstimatedTrajectory,
)
from .evaluation import (
    EvaluationConfig,
    RouteEvaluation,
    StayEvaluation,
    OverallMetrics,
    EvaluationResult,
)
from .pairwise import (
    PairwiseMovement,
    PairwiseMovementResult,
)

__all__ = [
    # 軌跡モデル
    "GroundTruthStay",
    "EstimatedStay",
    "GroundTruthTrajectory",
    "EstimatedTrajectory",
    # 評価モデル
    "EvaluationConfig",
    "RouteEvaluation",
    "StayEvaluation",
    "OverallMetrics",
    "EvaluationResult",
    "PairwiseMovement",
    "PairwiseMovementResult",
]

"""軌跡ベース評価のドメインモデル"""

from dataclasses import dataclass
from typing import List


@dataclass
class StayEvaluation:
    """ルート評価結果

    Note: 名前は StayEvaluation だが、実際にはルート単位の評価に使用。
    detector_id フィールドにルート名（例: "ABCD"）が入る。
    """
    detector_id: str
    gt_start: str      # GT滞在開始時刻（ISO 8601）
    gt_end: str        # GT滞在終了時刻（ISO 8601）
    tolerance_start: str  # 許容範囲開始
    tolerance_end: str    # 許容範囲終了
    gt_count: int      # この滞在に実際にいた人数
    est_count: int     # この滞在（±許容誤差）で検出された人数
    error: int         # |gt_count - est_count|
    # 詳細情報
    gt_trajectory_ids: List[str]   # 該当するGT軌跡ID
    est_trajectory_ids: List[str]  # 該当するEst軌跡ID


@dataclass
class OverallMetrics:
    """全体の評価指標"""
    total_stays: int                      # 評価したGT滞在の総数
    mae: float                            # Mean Absolute Error
    rmse: float                           # Root Mean Squared Error
    tracking_rate: float                  # 追跡率（人数が完全一致した割合）
    total_gt_count: int                   # GT軌跡の総数
    total_est_count: int                  # Est軌跡の総数
    total_absolute_error: int             # 絶対誤差の合計


@dataclass
class EvaluationResult:
    """評価結果全体"""
    metadata: dict
    overall_metrics: OverallMetrics
    stay_evaluations: List[StayEvaluation]

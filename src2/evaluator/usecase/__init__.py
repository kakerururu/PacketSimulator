"""Evaluator use cases

このモジュールは評価処理のユースケース（ビジネスロジック）を提供する。

モジュール構成:
    - evaluate_trajectories.py: メイン評価ロジック
    - route_utils.py: ルート名生成ユーティリティ
    - matching.py: GT/Est軌跡のマッチング判定
    - metrics.py: 評価メトリクス計算
"""

# メイン評価関数
from .evaluate_trajectories import evaluate_trajectories

# ルートユーティリティ
from .route_utils import create_route_with_timing

# マッチング
from .matching import check_trajectory_all_stays_match

# メトリクス計算
from .metrics import calculate_metrics, MetricsResult

# EvaluationConfigはdomainからインポートするよう案内
# 後方互換性のため、ここからもエクスポート
from ..domain.evaluation import EvaluationConfig

__all__ = [
    # メイン
    "evaluate_trajectories",
    # ユーティリティ
    "create_route_with_timing",
    "check_trajectory_all_stays_match",
    "calculate_metrics",
    "MetricsResult",
    # 設定（後方互換性）
    "EvaluationConfig",
]

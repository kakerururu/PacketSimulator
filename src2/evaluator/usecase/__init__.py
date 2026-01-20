"""Evaluator use cases（時間ビニング方式）

このモジュールは評価処理のユースケース（ビジネスロジック）を提供する。

モジュール構成:
    - evaluate_trajectories.py: メイン評価ロジック
    - route_utils.py: ルート名生成ユーティリティ（時間ビニング）
    - metrics.py: 評価メトリクス計算
    - pairwise_movement.py: 2地点間移動カウント
"""

# メイン評価関数
from .evaluate_trajectories import evaluate_trajectories

# ルートユーティリティ
from .route_utils import create_route_with_timing_binned, get_time_bin

# メトリクス計算
from .metrics import calculate_metrics, MetricsResult

# 2地点間移動カウント
from .pairwise_movement import calculate_pairwise_movements

# EvaluationConfigはdomainからインポートするよう案内
# 後方互換性のため、ここからもエクスポート
from ..domain.evaluation import EvaluationConfig

__all__ = [
    # メイン
    "evaluate_trajectories",
    # ユーティリティ
    "create_route_with_timing_binned",
    "get_time_bin",
    "calculate_metrics",
    "MetricsResult",
    # 設定（後方互換性）
    "EvaluationConfig",
    "calculate_pairwise_movements",
]

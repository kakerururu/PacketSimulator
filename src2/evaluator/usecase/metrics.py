"""評価メトリクス計算

責務: 評価指標（MAE, RMSE, 追跡率など）の計算ロジック。

指標の意味:
    - MAE (Mean Absolute Error): 平均絶対誤差。ルートあたり平均何人ずれているか
    - RMSE (Root Mean Squared Error): 二乗平均平方根誤差。大きな誤差に厳しい
    - Tracking Rate (追跡率): GT人数とEst人数が完全一致したルートの割合
"""

import math
from typing import List, Dict
from dataclasses import dataclass


@dataclass
class MetricsResult:
    """メトリクス計算結果

    Attributes:
        mae: Mean Absolute Error（平均絶対誤差）
        rmse: Root Mean Squared Error（二乗平均平方根誤差）
        tracking_rate: 追跡率（完全一致の割合）
        total_absolute_error: 絶対誤差の合計
        exact_match_count: 完全一致したルート数
        total_routes: 評価対象のルート総数
    """

    mae: float
    rmse: float
    tracking_rate: float
    total_absolute_error: int
    exact_match_count: int
    total_routes: int


def calculate_metrics(errors: List[int]) -> MetricsResult:
    """誤差リストから各種メトリクスを計算

    【計算される指標】

    1. MAE (Mean Absolute Error) - 平均絶対誤差
       - 計算式: Σ|error| / n
       - 意味: ルートあたり平均何人ずれているか
       - 範囲: 0 以上（0 が最良）
       - 例: errors = [0, 1, 2] → MAE = (0+1+2)/3 = 1.0

    2. RMSE (Root Mean Squared Error) - 二乗平均平方根誤差
       - 計算式: √(Σerror² / n)
       - 意味: MAEより大きな誤差にペナルティを与える
       - 特性: RMSE >= MAE。RMSE >> MAE の場合、外れ値がある
       - 例: errors = [0, 1, 2] → RMSE = √((0+1+4)/3) = √1.67 ≈ 1.29

    3. Tracking Rate (追跡率)
       - 計算式: (error=0のルート数) / 全ルート数
       - 意味: GT人数とEst人数がピッタリ一致したルートの割合
       - 範囲: 0.0 ~ 1.0（1.0 = 100% が最良）
       - 例: errors = [0, 0, 1] → Tracking Rate = 2/3 ≈ 66.7%

    【入力】
    errors: 各ルートの誤差（|GT人数 - Est人数|）のリスト
            例: [0, 0, 1, 2, 0]  # 5ルートの誤差

    【出力】
    MetricsResult: 計算結果を格納したデータクラス

    【エッジケース】
    - errors が空の場合: すべて 0.0 を返す

    Args:
        errors: 誤差値のリスト。各要素は |GT人数 - Est人数|

    Returns:
        MetricsResult: 計算されたメトリクス
    """

    total_routes = len(errors)
    # ================================================================
    # エッジケース: 誤差リストが空の場合
    # ================================================================

    if total_routes == 0:
        # 評価対象がない場合は、すべて0を返す
        return MetricsResult(
            mae=0.0,
            rmse=0.0,
            tracking_rate=0.0,
            total_absolute_error=0,
            exact_match_count=0,
            total_routes=0,
        )

    # ================================================================
    # 絶対誤差の合計を計算
    # ================================================================
    # 例: errors = [0, 1, 2, 1, 0] → total = 4
    total_absolute_error = sum(errors)

    # ================================================================
    # MAE (Mean Absolute Error) を計算
    # ================================================================
    # MAE = Σ|error| / n
    # 注: errors はすでに絶対値（|GT - Est|）なので、そのまま合計
    mae = total_absolute_error / total_routes

    # ================================================================
    # RMSE (Root Mean Squared Error) を計算
    # ================================================================
    # RMSE = √(Σerror² / n)
    #
    # 計算ステップ:
    # 1. 各誤差を2乗: [0, 1, 4, 1, 0]
    # 2. 合計: 6
    # 3. 平均: 6/5 = 1.2
    # 4. 平方根: √1.2 ≈ 1.095
    sum_squared_errors = sum(e**2 for e in errors)
    mean_squared_error = sum_squared_errors / total_routes
    rmse = math.sqrt(mean_squared_error)

    # ================================================================
    # Tracking Rate (追跡率) を計算
    # ================================================================
    # 完全一致 = 誤差が0のルート
    # 追跡率 = 完全一致数 / 全ルート数
    exact_match_count = sum(1 for e in errors if e == 0)
    tracking_rate = exact_match_count / total_routes

    # ================================================================
    # 結果を返す
    # ================================================================
    return MetricsResult(
        mae=mae,
        rmse=rmse,
        tracking_rate=tracking_rate,
        total_absolute_error=total_absolute_error,
        exact_match_count=exact_match_count,
        total_routes=total_routes,
    )


def format_metrics_summary(metrics: MetricsResult) -> str:
    """メトリクスを人間が読みやすい形式にフォーマット

    【出力例】
    MAE: 0.500 (ルートあたり平均0.5人のずれ)
    RMSE: 0.707
    追跡率: 75.0% (3/4ルートが完全一致)

    Args:
        metrics: 計算済みのメトリクス

    Returns:
        フォーマットされた文字列
    """
    lines = [
        f"MAE: {metrics.mae:.3f} (ルートあたり平均{metrics.mae:.1f}人のずれ)",
        f"RMSE: {metrics.rmse:.3f}",
        f"追跡率: {metrics.tracking_rate:.1%} ({metrics.exact_match_count}/{metrics.total_routes}ルートが完全一致)",
        f"総絶対誤差: {metrics.total_absolute_error}人",
    ]
    return "\n".join(lines)

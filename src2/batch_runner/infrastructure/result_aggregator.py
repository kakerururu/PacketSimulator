"""結果集約モジュール

複数回の実行結果から統計量を計算する。
"""

import math
from typing import List, Dict, Any

from ..domain.aggregated_result import MetricStatistics


def calculate_statistics(values: List[float]) -> MetricStatistics:
    """値のリストから統計量を計算

    Args:
        values: 数値のリスト

    Returns:
        統計情報

    Notes:
        95%信頼区間は t分布を使用して計算
        （サンプルサイズが小さい場合を考慮）
    """
    n = len(values)
    if n == 0:
        return MetricStatistics(
            mean=0.0,
            std=0.0,
            ci_95_lower=0.0,
            ci_95_upper=0.0,
            min=0.0,
            max=0.0,
        )

    # 平均
    mean = sum(values) / n

    # 標準偏差（不偏分散）
    if n > 1:
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0.0

    # 95%信頼区間（t分布の近似値を使用）
    # 自由度n-1のt分布の97.5パーセンタイル
    t_values = {
        1: 12.706,
        2: 4.303,
        3: 3.182,
        4: 2.776,
        5: 2.571,
        6: 2.447,
        7: 2.365,
        8: 2.306,
        9: 2.262,
        10: 2.228,
        15: 2.131,
        20: 2.086,
        25: 2.060,
        30: 2.042,
        40: 2.021,
        50: 2.009,
        100: 1.984,
    }

    # 最も近いt値を選択
    df = n - 1
    if df <= 0:
        t = 1.96  # フォールバック（正規分布の近似）
    elif df in t_values:
        t = t_values[df]
    elif df > 100:
        t = 1.96  # 正規分布の近似
    else:
        # 線形補間
        lower_df = max(k for k in t_values.keys() if k <= df)
        upper_df = min(k for k in t_values.keys() if k >= df)
        if lower_df == upper_df:
            t = t_values[lower_df]
        else:
            ratio = (df - lower_df) / (upper_df - lower_df)
            t = t_values[lower_df] + ratio * (t_values[upper_df] - t_values[lower_df])

    # 標準誤差
    se = std / math.sqrt(n) if n > 0 else 0.0

    # 信頼区間
    margin = t * se
    ci_95_lower = mean - margin
    ci_95_upper = mean + margin

    return MetricStatistics(
        mean=mean,
        std=std,
        ci_95_lower=ci_95_lower,
        ci_95_upper=ci_95_upper,
        min=min(values),
        max=max(values),
    )


def aggregate_metrics(
    run_results: List[Dict[str, Any]],
) -> Dict[str, MetricStatistics]:
    """複数回の実行結果からメトリクスを集約

    Args:
        run_results: 各実行の結果辞書のリスト

    Returns:
        メトリクス名 -> 統計情報のマップ

    Examples:
        >>> results = [
        ...     {"mae": 0.5, "rmse": 0.7, "exact_match_rate": 0.85},
        ...     {"mae": 0.6, "rmse": 0.8, "exact_match_rate": 0.80},
        ... ]
        >>> stats = aggregate_metrics(results)
        >>> stats["mae"].mean
        0.55
    """
    if not run_results:
        return {}

    # メトリクス名を取得
    metric_names = run_results[0].keys()

    # 各メトリクスの値を収集して統計を計算
    aggregated = {}
    for metric_name in metric_names:
        values = [r[metric_name] for r in run_results if metric_name in r]
        # 数値のみを対象にする
        if values and isinstance(values[0], (int, float)):
            aggregated[metric_name] = calculate_statistics(values)

    return aggregated

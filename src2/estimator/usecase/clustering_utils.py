"""クラスタリング用ユーティリティ関数

移動可能性の判定に使用する純粋関数群。
"""

from ..domain.detection_record import DetectionRecord


# =============================================================================
# 定数
# =============================================================================

# 最大滞在時間（15分 = 900秒）
# 同じ検出器で900秒以上の間隔があれば「別人」とみなす。これは滞留オプションが無効の場合に使用。
MAX_STAY_DURATION = 900.0


# =============================================================================
# 判定関数（純粋関数）
# =============================================================================


def is_sequence_anomaly(
    record1: DetectionRecord,
    record2: DetectionRecord,
    time_diff: float,
    min_travel_time: float,
    impossible_factor: float,
) -> bool:
    """シーケンス番号異常かチェック

    【判定条件】
    シーケンス番号の差 > 64  AND  時間的にありえない移動

    【背景】
    パケットのシーケンス番号は 0-4095 の範囲で循環する。
    同一デバイスからの連続パケットなら、シーケンス番号は近い値になるはず。

    シーケンス番号が大きく飛んでいる（> 64）のに、
    物理的にありえない短時間で検出された場合、
    これは「別人のパケット」である可能性が高い。

    【注意】
    この関数は現在、以下のように使用されている:
    - メインループ (_evaluate_candidate_record): ログ出力のみ（判定には影響しない）
    - 前方探索 (_evaluate_scan_record): 実際にスキップ判定に使用

    Args:
        record1: 前のレコード
        record2: 候補レコード
        time_diff: 2つのレコード間の時間差（秒）
        min_travel_time: 2つの検出器間の最小移動時間（秒）
        impossible_factor: ありえない移動判定の係数（デフォルト 0.8）

    Returns:
        True: シーケンス番号異常（別人の可能性が高い）
        False: 正常
    """
    seq_diff = abs(record2.sequence_number - record1.sequence_number)

    # 条件: シーケンス差 > 64 かつ 時間的にありえない
    return seq_diff > 64 and time_diff < min_travel_time * impossible_factor

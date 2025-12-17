"""軌跡マッチング判定

責務: GT軌跡とEst軌跡が「同一人物」とみなせるかの判定ロジック。
     許容誤差（tolerance）を考慮して、時刻的に近い軌跡をマッチングする。

マッチング条件:
    1. ルートパターンが完全一致（例: ABCD == ABCD）
    2. 滞在数が一致
    3. すべての滞在地点で、Est検出時刻がGT滞在時刻の許容範囲内
"""

from datetime import timedelta
from ..domain.trajectory import GroundTruthTrajectory, EstimatedTrajectory


def check_trajectory_all_stays_match(
    gt_traj: GroundTruthTrajectory,
    est_traj: EstimatedTrajectory,
    tolerance_seconds: float
) -> bool:
    """GT軌跡とEst軌跡がマッチするか判定

    【判定の目的】
    推定された軌跡(Est)が、実際の軌跡(GT)と「同一人物」とみなせるかを判定。
    時刻のズレが許容範囲内であれば、同一人物として扱う。

    【判定条件（すべて満たす必要あり）】
    1. ルートパターンが完全一致
       - 例: GT="ABCD" と Est="ABCD" → OK
       - 例: GT="ABCD" と Est="ABDC" → NG

    2. 滞在数が一致
       - 4地点のルートなら、両方とも4つの滞在を持つ必要がある

    3. 各滞在地点で検出器IDが一致
       - 同じ順序で同じ検出器を訪問している必要がある

    4. 各滞在地点でEst検出時刻がGT滞在時刻の許容範囲内
       - 許容範囲: [arrival_time - tolerance, departure_time + tolerance]
       - first_detection と last_detection の両方がこの範囲内である必要

    【許容範囲の計算イメージ】

        GT滞在時刻:    |----arrival----departure----|
        許容範囲:   |--tolerance--|           |--tolerance--|
                   ↓                                       ↓
        許容開始: arrival - tolerance      許容終了: departure + tolerance

        Est検出:       |--first--last--|  ← この範囲が許容範囲内なら OK

    【使用例】
        # 許容誤差 20分（1200秒）でマッチング判定
        is_match = check_trajectory_all_stays_match(gt_traj, est_traj, 1200.0)

    Args:
        gt_traj: Ground Truth軌跡（正解データ）
        est_traj: Estimated軌跡（推定結果）
        tolerance_seconds: 許容誤差（秒）。デフォルトは1200秒（20分）

    Returns:
        bool: すべての条件を満たす場合 True、それ以外は False
    """
    # ================================================================
    # 条件1: ルートパターンが完全一致するか
    # ================================================================
    # 例: "ABCD" != "DCBA" → False
    if gt_traj.route != est_traj.route:
        return False

    # ================================================================
    # 条件2: 滞在数が一致するか
    # ================================================================
    # 滞在数が異なる場合、同一人物とはみなせない
    # 例: GTが4滞在、Estが3滞在 → False
    if len(gt_traj.stays) != len(est_traj.stays):
        return False

    # ================================================================
    # 条件3 & 4: 各滞在地点での詳細チェック
    # ================================================================
    # 許容誤差をtimedeltaに変換（秒 → timedelta）
    tolerance_delta = timedelta(seconds=tolerance_seconds)

    # 各滞在をペアで比較
    for gt_stay, est_stay in zip(gt_traj.stays, est_traj.stays):

        # ------------------------------------------------------------
        # 条件3: 検出器IDが一致するか
        # ------------------------------------------------------------
        # 同じ順序で同じ検出器を訪問している必要がある
        if gt_stay.detector_id != est_stay.detector_id:
            return False

        # ------------------------------------------------------------
        # 条件4: Est検出時刻がGT滞在時刻の許容範囲内か
        # ------------------------------------------------------------
        # 許容範囲の開始: GTの到着時刻 - 許容誤差
        tolerance_start = gt_stay.arrival_time - tolerance_delta

        # 許容範囲の終了: GTの出発時刻 + 許容誤差
        tolerance_end = gt_stay.departure_time + tolerance_delta

        # Estの最初の検出時刻が許容範囲内か
        # tolerance_start <= first_detection <= tolerance_end
        if not (tolerance_start <= est_stay.first_detection <= tolerance_end):
            return False

        # Estの最後の検出時刻が許容範囲内か
        # tolerance_start <= last_detection <= tolerance_end
        if not (tolerance_start <= est_stay.last_detection <= tolerance_end):
            return False

    # ================================================================
    # すべての条件を満たした場合、マッチと判定
    # ================================================================
    return True

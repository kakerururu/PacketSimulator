"""2地点間移動人数の集計

軌跡内の全ての2地点ペア間の移動人数を、時間ビン付きで集計する。
"""

from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Set, Tuple

from ..domain.trajectory import GroundTruthTrajectory, EstimatedTrajectory
from ..domain.pairwise import PairwiseMovement, PairwiseMovementResult


def get_time_bin(dt: datetime, bin_minutes: int) -> str:
    """datetimeを時間ビンに変換

    Args:
        dt: 変換対象のdatetime
        bin_minutes: ビンの幅（分）

    Returns:
        ビン識別子（例: "0900~0930"）

    Examples:
        >>> get_time_bin(datetime(2024, 1, 1, 9, 15), 30)
        "0900~0930"
    """
    total_minutes = dt.hour * 60 + dt.minute
    bin_start = (total_minutes // bin_minutes) * bin_minutes
    bin_end = bin_start + bin_minutes

    # 24時間を超える場合
    if bin_end >= 24 * 60:
        bin_end = bin_end % (24 * 60)

    start_h, start_m = divmod(bin_start, 60)
    end_h, end_m = divmod(bin_end, 60)

    return f"{start_h:02d}{start_m:02d}~{end_h:02d}{end_m:02d}"


def _extract_pairwise_movements_gt(
    trajectories: List[GroundTruthTrajectory],
    all_detectors: Set[str],
    time_bin_minutes: int,
) -> Dict[Tuple[str, str, str, str], int]:
    """GT軌跡から2地点間移動を抽出

    軌跡内の全ての2地点ペア（i < j）について、移動をカウントする。
    完全ルート（全検知器を経由）のみを対象とする。

    Args:
        trajectories: GT軌跡リスト
        all_detectors: 全検知器IDのセット（完全ルート判定用）
        time_bin_minutes: 時間ビン幅（分）

    Returns:
        (origin, origin_bin, destination, destination_bin) -> カウント
    """
    counts: Dict[Tuple[str, str, str, str], int] = defaultdict(int)

    for traj in trajectories:
        # 完全ルート判定: 全検知器を経由しているか
        traj_detectors = set(traj.route)
        if traj_detectors != all_detectors:
            continue  # 部分ルートは除外

        stays = traj.stays

        # 全ての2地点ペア（i < j）を生成
        for i in range(len(stays)):
            for j in range(i + 1, len(stays)):
                origin_stay = stays[i]
                dest_stay = stays[j]

                origin = origin_stay.detector_id
                origin_bin = get_time_bin(origin_stay.arrival_time, time_bin_minutes)
                destination = dest_stay.detector_id
                dest_bin = get_time_bin(dest_stay.arrival_time, time_bin_minutes)

                key = (origin, origin_bin, destination, dest_bin)
                counts[key] += 1

    return counts


def _extract_pairwise_movements_est(
    trajectories: List[EstimatedTrajectory],
    all_detectors: Set[str],
    time_bin_minutes: int,
) -> Dict[Tuple[str, str, str, str], int]:
    """Est軌跡から2地点間移動を抽出

    GTと同じロジックだが、時刻はfirst_detectionを使用。

    Args:
        trajectories: Est軌跡リスト
        all_detectors: 全検知器IDのセット（完全ルート判定用）
        time_bin_minutes: 時間ビン幅（分）

    Returns:
        (origin, origin_bin, destination, destination_bin) -> カウント
    """
    counts: Dict[Tuple[str, str, str, str], int] = defaultdict(int)

    for traj in trajectories:
        # 完全ルート判定: 全検知器を経由しているか
        traj_detectors = set(traj.route)
        if traj_detectors != all_detectors:
            continue  # 部分ルートは除外

        stays = traj.stays

        # 全ての2地点ペア（i < j）を生成
        for i in range(len(stays)):
            for j in range(i + 1, len(stays)):
                origin_stay = stays[i]
                dest_stay = stays[j]

                origin = origin_stay.detector_id
                origin_bin = get_time_bin(origin_stay.first_detection, time_bin_minutes)
                destination = dest_stay.detector_id
                dest_bin = get_time_bin(dest_stay.first_detection, time_bin_minutes)

                key = (origin, origin_bin, destination, dest_bin)
                counts[key] += 1

    return counts


def calculate_pairwise_movements(
    gt_trajectories: List[GroundTruthTrajectory],
    est_trajectories: List[EstimatedTrajectory],
    time_bin_minutes: int = 30,
) -> PairwiseMovementResult:
    """2地点間移動人数を集計

    GT軌跡とEst軌跡それぞれについて、全ての2地点ペア間の
    移動人数を時間ビン付きで集計する。

    【処理フロー】
    1. GTから全検知器IDを取得（完全ルート判定用）
    2. GT軌跡から2地点間移動を抽出
    3. Est軌跡から2地点間移動を抽出
    4. 両方のキーをマージして結果を生成

    Args:
        gt_trajectories: Ground Truth軌跡リスト
        est_trajectories: 推定軌跡リスト
        time_bin_minutes: 時間ビン幅（分）、デフォルト30分

    Returns:
        PairwiseMovementResult: 2地点間移動の集計結果

    Examples:
        >>> result = calculate_pairwise_movements(
        ...     gt_trajectories, est_trajectories, time_bin_minutes=30
        ... )
        >>> print(result.movements[0])
        PairwiseMovement(origin='A', origin_bin='0900~0930', ...)
    """
    # GTから全検知器IDを取得（完全ルート判定用）
    all_detectors: Set[str] = set()
    for gt_traj in gt_trajectories:
        for stay in gt_traj.stays:
            all_detectors.add(stay.detector_id)

    # GT・Estそれぞれから移動をカウント
    gt_counts = _extract_pairwise_movements_gt(
        gt_trajectories, all_detectors, time_bin_minutes
    )
    est_counts = _extract_pairwise_movements_est(
        est_trajectories, all_detectors, time_bin_minutes
    )

    # 全てのキーをマージ
    all_keys = set(gt_counts.keys()) | set(est_counts.keys())

    # 結果を構築（ソートして一貫した出力順序に）
    movements = []
    for key in sorted(all_keys):
        origin, origin_bin, destination, dest_bin = key
        movements.append(
            PairwiseMovement(
                origin=origin,
                origin_bin=origin_bin,
                destination=destination,
                destination_bin=dest_bin,
                gt_count=gt_counts.get(key, 0),
                est_count=est_counts.get(key, 0),
            )
        )

    return PairwiseMovementResult(
        time_bin_minutes=time_bin_minutes,
        movements=movements,
    )

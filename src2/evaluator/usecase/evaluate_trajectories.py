"""軌跡全体ベースの評価

GTの各軌跡に対して、すべての地点で許容時間内に検出できたかを評価する。
"""

from dataclasses import dataclass
from typing import List, Dict, Set
from datetime import datetime, timedelta
import math
from collections import defaultdict

from ..domain.trajectory import GroundTruthTrajectory, EstimatedTrajectory
from ..domain.evaluation import (
    StayEvaluation,
    OverallMetrics,
    EvaluationResult,
)


@dataclass
class EvaluationConfig:
    """評価設定"""
    tolerance_seconds: float = 1200.0  # デフォルト: 20分


@dataclass
class RouteEvaluation:
    """ルートごとの評価結果"""
    route: str
    gt_count: int
    est_count: int
    error: int
    gt_trajectory_ids: List[str]
    est_trajectory_ids: List[str]


def create_route_with_timing(route: str, stays: List) -> str:
    """ルート名に時系列情報を付与

    各滞在地点の時刻情報を含めることで、同じ空間ルート（例: ABCD）でも
    異なる時間帯に通過した場合を区別できるようにする。

    例: ABCD_0900-0910_1000-1010_1100-1110_1200-1210

    Args:
        route: 空間的なルート（例: "ABCD"）
        stays: 滞在情報のリスト

    Returns:
        時系列情報を含むルート名
    """
    time_parts = []

    for stay in stays:
        if hasattr(stay, 'arrival_time') and hasattr(stay, 'departure_time'):
            # GT trajectory
            start = stay.arrival_time.strftime("%H%M")
            end = stay.departure_time.strftime("%H%M")
            time_parts.append(f"{start}-{end}")
        elif hasattr(stay, 'first_detection') and hasattr(stay, 'last_detection'):
            # Est trajectory
            start = stay.first_detection.strftime("%H%M")
            end = stay.last_detection.strftime("%H%M")
            time_parts.append(f"{start}-{end}")

    time_str = "_".join(time_parts)
    return f"{route}_{time_str}"


def check_trajectory_all_stays_match(
    gt_traj: GroundTruthTrajectory,
    est_traj: EstimatedTrajectory,
    tolerance_seconds: float
) -> bool:
    """軌跡のすべての滞在が許容範囲内かチェック

    Args:
        gt_traj: Ground Truth軌跡
        est_traj: Estimated軌跡
        tolerance_seconds: 許容誤差（秒）

    Returns:
        すべての滞在が許容範囲内の場合True
    """
    # 条件1: ルートが一致
    if gt_traj.route != est_traj.route:
        return False

    # 条件2: 滞在数が一致
    if len(gt_traj.stays) != len(est_traj.stays):
        return False

    # 条件3: すべての滞在が許容範囲内
    tolerance_delta = timedelta(seconds=tolerance_seconds)

    for gt_stay, est_stay in zip(gt_traj.stays, est_traj.stays):
        # 検出器IDが一致するか
        if gt_stay.detector_id != est_stay.detector_id:
            return False

        # 許容範囲を計算
        tolerance_start = gt_stay.arrival_time - tolerance_delta
        tolerance_end = gt_stay.departure_time + tolerance_delta

        # Est検出時刻が範囲内か
        if not (tolerance_start <= est_stay.first_detection <= tolerance_end):
            return False
        if not (tolerance_start <= est_stay.last_detection <= tolerance_end):
            return False

    return True


def evaluate_trajectories(
    gt_trajectories: List[GroundTruthTrajectory],
    est_trajectories: List[EstimatedTrajectory],
    config: EvaluationConfig,
    ground_truth_file: str,
    estimated_file: str
) -> EvaluationResult:
    """軌跡全体ベースで評価

    処理の流れ:
    1. すべての検出器IDを取得
    2. ルートパターン（時系列情報含む）ごとにGT人数を集計
    3. Est軌跡を処理:
       - 部分ルート（一部検出器のみ）→ 除外
       - 完全ルート（全検出器経由）→ GTと許容誤差（±600秒）でマッチング
         - マッチした場合: GTと同じルート名でカウント
         - マッチしない場合: 独自のルート名で別ルートとしてカウント
    4. 誤差を計算し、MAE/RMSE/正確一致率を算出

    Args:
        gt_trajectories: Ground Truth軌跡リスト
        est_trajectories: 推定軌跡リスト
        config: 評価設定
        ground_truth_file: Ground Truthファイルパス
        estimated_file: 推定結果ファイルパス

    Returns:
        EvaluationResult: 評価結果
    """
    # ルートパターンごとに集計
    route_stats: Dict[str, RouteEvaluation] = {}

    # 1. すべての検出器IDを取得
    all_detectors = set()
    for gt_traj in gt_trajectories:
        for stay in gt_traj.stays:
            all_detectors.add(stay.detector_id)

    # 2. GT軌跡を集計（時系列情報を含むルート名で）
    for gt_traj in gt_trajectories:
        route_with_timing = create_route_with_timing(gt_traj.route, gt_traj.stays)
        if route_with_timing not in route_stats:
            route_stats[route_with_timing] = RouteEvaluation(
                route=route_with_timing,
                gt_count=0,
                est_count=0,
                error=0,
                gt_trajectory_ids=[],
                est_trajectory_ids=[]
            )
        route_stats[route_with_timing].gt_count += 1
        route_stats[route_with_timing].gt_trajectory_ids.append(gt_traj.trajectory_id)

    # 3. Est軌跡を集計（許容誤差を考慮してマッチング）
    num_partial_routes = 0  # 部分ルートのカウント
    num_complete_routes = 0  # 完全ルートのカウント
    partial_route_info = []  # 部分ルート情報: (trajectory_id, route)

    for est_traj in est_trajectories:
        # 部分ルートは除外（すべての検出器を経由していない）
        est_detectors = set(est_traj.route)
        if est_detectors != all_detectors:
            num_partial_routes += 1
            partial_route_info.append({
                "trajectory_id": est_traj.trajectory_id,
                "route": est_traj.route
            })
            continue  # 不完全なルートはスキップ

        num_complete_routes += 1

        # 同じ空間ルート（例：ABDC）のGT軌跡を全て取得
        matching_gts = [gt for gt in gt_trajectories if gt.route == est_traj.route]

        # 許容誤差（±600秒）内でマッチするGTを探す
        matched_gt = None
        for gt_traj in matching_gts:
            if check_trajectory_all_stays_match(gt_traj, est_traj, config.tolerance_seconds):
                matched_gt = gt_traj
                break

        if matched_gt:
            # マッチしたGTのルート名（時系列情報付き）を使用
            route_with_timing = create_route_with_timing(matched_gt.route, matched_gt.stays)
        else:
            # マッチしなかった場合は独自のルート名を生成
            route_with_timing = create_route_with_timing(est_traj.route, est_traj.stays)

            # 新規ルートとして追加（GTに存在しない、またはGTと時刻が大きくズレている）
            if route_with_timing not in route_stats:
                route_stats[route_with_timing] = RouteEvaluation(
                    route=route_with_timing,
                    gt_count=0,  # GTに存在しない、または許容誤差外
                    est_count=0,
                    error=0,
                    gt_trajectory_ids=[],
                    est_trajectory_ids=[]
                )

        # すべての完全ルートをカウント
        route_stats[route_with_timing].est_count += 1
        route_stats[route_with_timing].est_trajectory_ids.append(est_traj.trajectory_id)

    # 各ルートの誤差を計算
    for route_eval in route_stats.values():
        route_eval.error = abs(route_eval.gt_count - route_eval.est_count)

    # StayEvaluation形式に変換（互換性のため）
    stay_evaluations = []
    for route_eval in route_stats.values():
        stay_eval = StayEvaluation(
            detector_id=route_eval.route,  # ルート名を入れる
            gt_start="",  # ルート評価なので空
            gt_end="",
            tolerance_start="",
            tolerance_end="",
            gt_count=route_eval.gt_count,
            est_count=route_eval.est_count,
            error=route_eval.error,
            gt_trajectory_ids=route_eval.gt_trajectory_ids,
            est_trajectory_ids=route_eval.est_trajectory_ids
        )
        stay_evaluations.append(stay_eval)

    # 全体指標を計算
    errors = [re.error for re in route_stats.values()]
    total_routes = len(route_stats)

    if total_routes > 0:
        mae = sum(errors) / total_routes
        rmse = math.sqrt(sum(e**2 for e in errors) / total_routes)
        exact_matches = sum(1 for e in errors if e == 0)
        exact_match_rate = exact_matches / total_routes
    else:
        mae = 0.0
        rmse = 0.0
        exact_match_rate = 0.0

    # Est軌跡総数を計算（条件を満たしたもの）
    total_est_count = sum(re.est_count for re in route_stats.values())

    overall_metrics = OverallMetrics(
        total_stays=total_routes,  # ルート数
        mae=mae,
        rmse=rmse,
        exact_match_rate=exact_match_rate,
        total_gt_count=len(gt_trajectories),
        total_est_count=total_est_count,
        total_absolute_error=sum(errors)
    )

    # メタデータ
    metadata = {
        "evaluation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ground_truth_file": ground_truth_file,
        "estimated_file": estimated_file,
        "tolerance_seconds": config.tolerance_seconds,
        "evaluation_method": "trajectory_based",
        "num_partial_routes": num_partial_routes,
        "num_complete_routes": num_complete_routes,
        "partial_routes": partial_route_info,
    }

    return EvaluationResult(
        metadata=metadata,
        overall_metrics=overall_metrics,
        stay_evaluations=stay_evaluations
    )

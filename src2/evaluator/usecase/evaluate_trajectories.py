"""軌跡全体ベースの評価

責務: GT軌跡とEst軌跡を比較し、推定精度を評価する。

【評価の考え方】
1. GTの各軌跡に対して、時系列情報を含むルート名を生成
2. Est軌跡を許容誤差でGTとマッチング
3. ルートごとのGT/Est人数を集計し、誤差を計算
4. MAE/RMSE/追跡率などの指標を算出

【評価対象】
- 完全ルート（すべての検出器を経由）のみを評価対象とする
- 部分ルート（一部の検出器のみ経由）は除外

【使用方法】
    from src2.evaluator.usecase.evaluate_trajectories import (
        evaluate_trajectories
    )
    from src2.evaluator.domain.evaluation import EvaluationConfig

    config = EvaluationConfig(tolerance_seconds=1200.0)
    result = evaluate_trajectories(gt_list, est_list, config, "gt.json", "est.json")
"""

from typing import List, Dict, Set
from datetime import datetime
import math

# ============================================================================
# ドメインモデルのインポート
# ============================================================================
from ..domain.trajectory import GroundTruthTrajectory, EstimatedTrajectory
from ..domain.evaluation import (
    EvaluationConfig,
    RouteEvaluation,
    StayEvaluation,
    OverallMetrics,
    EvaluationResult,
)

# ============================================================================
# 分割したユースケースモジュールのインポート
# ============================================================================
from .route_utils import create_route_with_timing
from .matching import check_trajectory_all_stays_match
from .metrics import calculate_metrics


# ============================================================================
# メイン評価関数
# ============================================================================


def evaluate_trajectories(
    gt_trajectories: List[GroundTruthTrajectory],
    est_trajectories: List[EstimatedTrajectory],
    config: EvaluationConfig,
    ground_truth_file: str,
    estimated_file: str
) -> EvaluationResult:
    """軌跡全体ベースで評価を実行

    【処理フロー】

    ┌─────────────────────────────────────────────────────────────┐
    │ 1. 準備処理                                                  │
    │    - すべての検出器IDを取得（完全ルート判定用）               │
    │    - route_stats 辞書を初期化                                │
    └─────────────────────────────────────────────────────────────┘
                                ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 2. GT軌跡の集計                                              │
    │    - 各GTに時系列ルート名を生成                              │
    │    - route_stats[ルート名].gt_count をインクリメント         │
    └─────────────────────────────────────────────────────────────┘
                                ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 3. Est軌跡の処理                                             │
    │    3a. 部分ルートは除外                                      │
    │    3b. 完全ルートをGTとマッチング                            │
    │        - マッチ成功: GTのルート名でカウント                  │
    │        - マッチ失敗: Est独自のルート名でカウント             │
    └─────────────────────────────────────────────────────────────┘
                                ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 4. 誤差計算                                                  │
    │    - 各ルートの error = |gt_count - est_count|              │
    └─────────────────────────────────────────────────────────────┘
                                ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 5. メトリクス計算                                            │
    │    - MAE, RMSE, 追跡率を算出                                 │
    └─────────────────────────────────────────────────────────────┘
                                ↓
    ┌─────────────────────────────────────────────────────────────┐
    │ 6. 結果を構築して返却                                        │
    │    - EvaluationResult として返す                             │
    └─────────────────────────────────────────────────────────────┘

    Args:
        gt_trajectories: Ground Truth軌跡リスト（正解データ）
        est_trajectories: 推定軌跡リスト（Estimatorの出力）
        config: 評価設定（許容誤差など）
        ground_truth_file: Ground Truthファイルパス（メタデータ用）
        estimated_file: 推定結果ファイルパス（メタデータ用）

    Returns:
        EvaluationResult: 評価結果（メタデータ、全体指標、詳細）
    """

    # ========================================================================
    # Phase 1: 準備処理
    # ========================================================================

    # ------------------------------------------------------------------------
    # 1a. ルート評価結果を格納する辞書を初期化
    # ------------------------------------------------------------------------
    # key: 時系列ルート名（例: "ABCD_0900-0910_..."）
    # value: RouteEvaluation オブジェクト
    route_stats: Dict[str, RouteEvaluation] = {}

    # ------------------------------------------------------------------------
    # 1b. すべての検出器IDを取得（完全ルート判定用）
    # ------------------------------------------------------------------------
    # GTに含まれる検出器IDを収集
    # 例: {"A", "B", "C", "D"}
    all_detectors: Set[str] = set()
    for gt_traj in gt_trajectories:
        for stay in gt_traj.stays:
            all_detectors.add(stay.detector_id)

    # ========================================================================
    # Phase 2: GT軌跡の集計
    # ========================================================================
    # 各GT軌跡に対して、時系列情報を含むルート名を生成し、
    # route_stats にGT人数を記録する

    for gt_traj in gt_trajectories:
        # --------------------------------------------------------------------
        # 2a. 時系列ルート名を生成
        # --------------------------------------------------------------------
        # 例: "ABCD" + stays → "ABCD_0900-0910_1000-1010_1100-1110_1200-1210"
        route_with_timing = create_route_with_timing(gt_traj.route, gt_traj.stays)

        # --------------------------------------------------------------------
        # 2b. route_stats に登録（初回のみ）
        # --------------------------------------------------------------------
        if route_with_timing not in route_stats:
            route_stats[route_with_timing] = RouteEvaluation(
                route=route_with_timing,
                gt_count=0,
                est_count=0,
                error=0,
                gt_trajectory_ids=[],
                est_trajectory_ids=[]
            )

        # --------------------------------------------------------------------
        # 2c. GT人数をインクリメント
        # --------------------------------------------------------------------
        route_stats[route_with_timing].gt_count += 1
        route_stats[route_with_timing].gt_trajectory_ids.append(gt_traj.trajectory_id)

    # ========================================================================
    # Phase 3: Est軌跡の処理
    # ========================================================================
    # 各Est軌跡を処理し、以下のいずれかを行う:
    # - 部分ルート → 除外（評価対象外）
    # - 完全ルート → GTとマッチングしてカウント

    # 部分ルート/完全ルートのカウント（メタデータ用）
    num_partial_routes = 0   # 除外された部分ルート数
    num_complete_routes = 0  # 評価対象の完全ルート数
    partial_route_info = []  # 除外された部分ルートの詳細

    for est_traj in est_trajectories:
        # --------------------------------------------------------------------
        # 3a. 部分ルートの判定と除外
        # --------------------------------------------------------------------
        # Est軌跡が経由した検出器の集合を取得
        # 例: "ABC" → {"A", "B", "C"}
        est_detectors = set(est_traj.route)

        # すべての検出器を経由していない場合は部分ルート
        if est_detectors != all_detectors:
            # 部分ルートは評価対象外としてスキップ
            num_partial_routes += 1
            partial_route_info.append({
                "trajectory_id": est_traj.trajectory_id,
                "route": est_traj.route
            })
            continue  # 次のEst軌跡へ

        # --------------------------------------------------------------------
        # 3b. 完全ルートの処理
        # --------------------------------------------------------------------
        num_complete_routes += 1

        # 同じ空間ルート（例："ABDC"）を持つGT軌跡を全て取得
        # マッチング候補として使用
        matching_gts = [gt for gt in gt_trajectories if gt.route == est_traj.route]

        # --------------------------------------------------------------------
        # 3c. GTとのマッチング
        # --------------------------------------------------------------------
        # 許容誤差内でマッチするGTを探す
        matched_gt = None
        for gt_traj in matching_gts:
            # 時刻的にマッチするか判定
            if check_trajectory_all_stays_match(gt_traj, est_traj, config.tolerance_seconds):
                matched_gt = gt_traj
                break  # 最初にマッチしたGTを採用

        # --------------------------------------------------------------------
        # 3d. ルート名の決定とカウント
        # --------------------------------------------------------------------
        if matched_gt:
            # マッチ成功: GTのルート名（時系列情報付き）を使用
            # → GTと同じルートとしてカウントされる
            route_with_timing = create_route_with_timing(matched_gt.route, matched_gt.stays)
        else:
            # マッチ失敗: Est独自のルート名を生成
            # → 新規ルートとしてカウントされる（GTに存在しないか、時刻が大きくズレている）
            route_with_timing = create_route_with_timing(est_traj.route, est_traj.stays)

            # 新規ルートとして route_stats に登録
            if route_with_timing not in route_stats:
                route_stats[route_with_timing] = RouteEvaluation(
                    route=route_with_timing,
                    gt_count=0,  # GTに存在しないルート
                    est_count=0,
                    error=0,
                    gt_trajectory_ids=[],
                    est_trajectory_ids=[]
                )

        # Est人数をインクリメント
        route_stats[route_with_timing].est_count += 1
        route_stats[route_with_timing].est_trajectory_ids.append(est_traj.trajectory_id)

    # ========================================================================
    # Phase 4: 誤差計算
    # ========================================================================
    # 各ルートの誤差 = |GT人数 - Est人数|

    for route_eval in route_stats.values():
        route_eval.error = abs(route_eval.gt_count - route_eval.est_count)

    # ========================================================================
    # Phase 5: メトリクス計算
    # ========================================================================

    # 誤差リストを作成
    errors = [re.error for re in route_stats.values()]

    # メトリクスを計算
    metrics_result = calculate_metrics(errors)

    # Est軌跡総数を計算（完全ルートのみ）
    total_est_count = sum(re.est_count for re in route_stats.values())

    # OverallMetrics オブジェクトを構築
    overall_metrics = OverallMetrics(
        total_stays=metrics_result.total_routes,  # ルート数
        mae=metrics_result.mae,
        rmse=metrics_result.rmse,
        tracking_rate=metrics_result.tracking_rate,
        total_gt_count=len(gt_trajectories),
        total_est_count=total_est_count,
        total_absolute_error=metrics_result.total_absolute_error
    )

    # ========================================================================
    # Phase 6: 結果の構築
    # ========================================================================

    # ------------------------------------------------------------------------
    # 6a. RouteEvaluation → StayEvaluation への変換
    # ------------------------------------------------------------------------
    # 互換性のため、内部用の RouteEvaluation を出力用の StayEvaluation に変換
    stay_evaluations = []
    for route_eval in route_stats.values():
        stay_eval = StayEvaluation(
            detector_id=route_eval.route,  # ルート名を格納
            gt_start="",                   # ルート評価では使用しない
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

    # ------------------------------------------------------------------------
    # 6b. メタデータの構築
    # ------------------------------------------------------------------------
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

    # ------------------------------------------------------------------------
    # 6c. EvaluationResult を構築して返却
    # ------------------------------------------------------------------------
    return EvaluationResult(
        metadata=metadata,
        overall_metrics=overall_metrics,
        stay_evaluations=stay_evaluations
    )

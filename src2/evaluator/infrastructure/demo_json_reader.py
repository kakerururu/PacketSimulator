"""デモデータJSON読み込み機能

責務: デモ用フォーマットのJSONファイルを読み込み、ドメインオブジェクトに変換する。

【デモフォーマット vs 通常フォーマット】

デモ用データ（src2_demo/）は通常のフォーマットと異なるため、専用のローダーを提供。

主な違い:
- GT: arrival/departure (通常は arrival_time/departure_time)
- GT: walker_id をtrajectory_idとしても使用
- Est: estimated_trajectory_id または cluster_id (通常は trajectory_id)

【使用場面】
- python -m src2.evaluator.main --demo
- python -m src2.evaluator.main_dev
"""

import json
from datetime import datetime
from typing import List

from ..domain.trajectory import (
    GroundTruthTrajectory,
    GroundTruthStay,
    EstimatedTrajectory,
    EstimatedStay,
)


# ============================================================================
# 日時フォーマット定数
# ============================================================================

# デモフォーマットも通常と同じ日時形式を使用
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


# ============================================================================
# Ground Truth 読み込み（デモフォーマット）
# ============================================================================


def load_demo_ground_truth_trajectories(file_path: str) -> List[GroundTruthTrajectory]:
    """デモ用Ground Truth JSONを読み込む

    デモフォーマットの特徴:
    - arrival/departure (通常は arrival_time/departure_time)
    - walker_id をtrajectory_idとしても使用
    - hashed_id を integrated_payload_id として使用

    【処理フロー】
    1. JSONファイルを読み込む
    2. trajectories 配列を走査
    3. デモフォーマットを通常フォーマットに変換しながら処理
    4. 軌跡リストを返す

    Args:
        file_path: JSONファイルパス
                  例: "src2_demo/ground_truth_trajectories.json"

    Returns:
        Ground Truth軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
    """
    # ========================================================================
    # JSONファイル読み込み
    # ========================================================================
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ========================================================================
    # 軌跡オブジェクトに変換
    # ========================================================================
    trajectories = []

    for traj_data in data["trajectories"]:
        # --------------------------------------------------------------------
        # 滞在情報を変換（デモフォーマット対応）
        # --------------------------------------------------------------------
        stays = []
        for stay_data in traj_data["stays"]:
            # デモフォーマット: "arrival" / "departure"
            # 通常フォーマット: "arrival_time" / "departure_time"
            arrival = datetime.strptime(stay_data["arrival"], DATETIME_FORMAT)
            departure = datetime.strptime(stay_data["departure"], DATETIME_FORMAT)

            stay = GroundTruthStay(
                detector_id=stay_data["detector_id"],
                arrival_time=arrival,
                departure_time=departure,
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        # --------------------------------------------------------------------
        # 軌跡オブジェクトを構築（デモフォーマット対応）
        # --------------------------------------------------------------------
        # デモフォーマットでは walker_id を trajectory_id としても使用
        trajectory = GroundTruthTrajectory(
            trajectory_id=traj_data["walker_id"],
            walker_id=traj_data["walker_id"],
            route=traj_data["route"],
            stays=stays,
            model=None,
            # デモフォーマット: hashed_id → integrated_payload_id
            integrated_payload_id=traj_data.get("hashed_id")
        )
        trajectories.append(trajectory)

    return trajectories


# ============================================================================
# Estimated 読み込み（デモフォーマット）
# ============================================================================


def load_demo_estimated_trajectories(file_path: str) -> List[EstimatedTrajectory]:
    """デモ用Estimated JSONを読み込む

    デモフォーマットの特徴:
    - estimated_trajectory_id または cluster_id を trajectory_id として使用
    - first_detection / last_detection は通常と同じ

    【処理フロー】
    1. JSONファイルを読み込む
    2. trajectories 配列を走査
    3. trajectory_id を適切なフィールドから取得
    4. 軌跡リストを返す

    Args:
        file_path: JSONファイルパス
                  例: "src2_demo/estimated_trajectories.json"

    Returns:
        推定軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
    """
    # ========================================================================
    # JSONファイル読み込み
    # ========================================================================
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ========================================================================
    # 軌跡オブジェクトに変換
    # ========================================================================
    trajectories = []

    for traj_data in data["trajectories"]:
        # --------------------------------------------------------------------
        # 滞在情報を変換
        # --------------------------------------------------------------------
        stays = []
        for stay_data in traj_data["stays"]:
            first = datetime.strptime(stay_data["first_detection"], DATETIME_FORMAT)
            last = datetime.strptime(stay_data["last_detection"], DATETIME_FORMAT)

            stay = EstimatedStay(
                detector_id=stay_data["detector_id"],
                num_detections=stay_data["num_detections"],
                first_detection=first,
                last_detection=last,
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        # --------------------------------------------------------------------
        # trajectory_id を取得（デモフォーマット対応）
        # --------------------------------------------------------------------
        # 優先順位:
        # 1. estimated_trajectory_id (デモフォーマット1)
        # 2. cluster_id (デモフォーマット2)
        # 3. trajectory_id (通常フォーマット)
        # 4. 自動生成 (フォールバック)
        traj_id = traj_data.get(
            "estimated_trajectory_id",
            traj_data.get(
                "cluster_id",
                traj_data.get(
                    "trajectory_id",
                    f"demo_traj_{len(trajectories)}"
                )
            )
        )

        # --------------------------------------------------------------------
        # 軌跡オブジェクトを構築
        # --------------------------------------------------------------------
        trajectory = EstimatedTrajectory(
            trajectory_id=traj_id,
            route=traj_data["route"],
            stays=stays,
            cluster_ids=traj_data.get("cluster_ids")
        )
        trajectories.append(trajectory)

    return trajectories

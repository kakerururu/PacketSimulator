"""JSON読み込み機能

責務: GT/Est軌跡のJSONファイルを読み込み、ドメインオブジェクトに変換する。

【対応フォーマット】
このモジュールは「通常フォーマット」のJSONを読み込む。
デモ用フォーマットは demo_json_reader.py を使用。

【通常フォーマットの例】

GT (ground_truth/trajectories.json):
{
    "trajectories": [
        {
            "trajectory_id": "gt_traj_1",
            "walker_id": "Walker_1",
            "route": "ABCD",
            "stays": [
                {
                    "detector_id": "A",
                    "arrival_time": "2025-01-01 09:00:00.000000",
                    "departure_time": "2025-01-01 09:10:00.000000",
                    "duration_seconds": 600.0
                },
                ...
            ]
        }
    ]
}

Est (estimated/trajectories.json):
{
    "trajectories": [
        {
            "trajectory_id": "est_traj_1",
            "route": "ABCD",
            "stays": [
                {
                    "detector_id": "A",
                    "num_detections": 10,
                    "first_detection": "2025-01-01 09:02:00.000000",
                    "last_detection": "2025-01-01 09:08:00.000000",
                    "duration_seconds": 360.0
                },
                ...
            ]
        }
    ]
}
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

# 通常フォーマットで使用する日時形式
# 例: "2025-01-01 09:00:00.000000"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


# ============================================================================
# Ground Truth 読み込み
# ============================================================================


def load_ground_truth_trajectories(file_path: str) -> List[GroundTruthTrajectory]:
    """Ground Truth JSONを読み込む

    JSONファイルからGT軌跡を読み込み、GroundTruthTrajectoryオブジェクトに変換する。

    【処理フロー】
    1. JSONファイルを読み込む
    2. trajectories 配列を走査
    3. 各軌跡に対して:
       - stays 配列を GroundTruthStay に変換
       - GroundTruthTrajectory を構築
    4. 軌跡リストを返す

    Args:
        file_path: JSONファイルパス
                  例: "src2_result/ground_truth/trajectories.json"

    Returns:
        Ground Truth軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
        KeyError: 必須フィールドがない場合
        ValueError: 日時形式が不正な場合
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
            # 日時文字列を datetime に変換
            arrival = datetime.strptime(stay_data["arrival_time"], DATETIME_FORMAT)
            departure = datetime.strptime(stay_data["departure_time"], DATETIME_FORMAT)

            stay = GroundTruthStay(
                detector_id=stay_data["detector_id"],
                arrival_time=arrival,
                departure_time=departure,
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        # --------------------------------------------------------------------
        # 軌跡オブジェクトを構築
        # --------------------------------------------------------------------
        trajectory = GroundTruthTrajectory(
            trajectory_id=traj_data["trajectory_id"],
            walker_id=traj_data["walker_id"],
            route=traj_data["route"],
            stays=stays,
            model=traj_data.get("model"),  # オプショナル
            integrated_payload_id=traj_data.get("integrated_payload_id")  # オプショナル
        )
        trajectories.append(trajectory)

    return trajectories


# ============================================================================
# Estimated 読み込み
# ============================================================================


def load_estimated_trajectories(file_path: str) -> List[EstimatedTrajectory]:
    """Estimated JSONを読み込む

    JSONファイルからEst軌跡を読み込み、EstimatedTrajectoryオブジェクトに変換する。

    【処理フロー】
    1. JSONファイルを読み込む
    2. trajectories 配列を走査
    3. 各軌跡に対して:
       - stays 配列を EstimatedStay に変換
       - EstimatedTrajectory を構築
    4. 軌跡リストを返す

    Args:
        file_path: JSONファイルパス
                  例: "src2_result/estimated/trajectories.json"

    Returns:
        推定軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
        KeyError: 必須フィールドがない場合
        ValueError: 日時形式が不正な場合
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
            # 日時文字列を datetime に変換
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
        # 軌跡オブジェクトを構築
        # --------------------------------------------------------------------
        trajectory = EstimatedTrajectory(
            trajectory_id=traj_data["trajectory_id"],
            route=traj_data["route"],
            stays=stays,
            cluster_ids=traj_data.get("cluster_ids")  # オプショナル
        )
        trajectories.append(trajectory)

    return trajectories

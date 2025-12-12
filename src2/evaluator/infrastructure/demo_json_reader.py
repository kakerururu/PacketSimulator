"""デモデータJSON読み込み機能

デモ用のGT/Estデータは通常のフォーマットと異なるため、
専用のローダーを提供する。
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


def load_demo_ground_truth_trajectories(file_path: str) -> List[GroundTruthTrajectory]:
    """デモ用Ground Truth JSONを読み込み

    デモフォーマット:
    - arrival/departure (通常は arrival_time/departure_time)
    - walker_id (trajectory_idの代わり)

    Args:
        file_path: JSONファイルパス

    Returns:
        Ground Truth軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    trajectories = []
    for traj_data in data["trajectories"]:
        stays = []
        for stay_data in traj_data["stays"]:
            stay = GroundTruthStay(
                detector_id=stay_data["detector_id"],
                arrival_time=datetime.strptime(
                    stay_data["arrival"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                departure_time=datetime.strptime(
                    stay_data["departure"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        trajectory = GroundTruthTrajectory(
            trajectory_id=traj_data["walker_id"],  # walker_idをtrajectory_idとして使用
            walker_id=traj_data["walker_id"],
            route=traj_data["route"],
            stays=stays,
            model=None,
            integrated_payload_id=traj_data.get("hashed_id")
        )
        trajectories.append(trajectory)

    return trajectories


def load_demo_estimated_trajectories(file_path: str) -> List[EstimatedTrajectory]:
    """デモ用Estimated JSONを読み込み

    デモフォーマット:
    - first_detection/last_detection (そのまま)
    - estimated_trajectory_id (trajectory_idの代わり)

    Args:
        file_path: JSONファイルパス

    Returns:
        推定軌跡リスト

    Raises:
        FileNotFoundError: ファイルが存在しない場合
        json.JSONDecodeError: JSONの形式が不正な場合
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    trajectories = []
    for traj_data in data["trajectories"]:
        stays = []
        for stay_data in traj_data["stays"]:
            stay = EstimatedStay(
                detector_id=stay_data["detector_id"],
                num_detections=stay_data["num_detections"],
                first_detection=datetime.strptime(
                    stay_data["first_detection"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                last_detection=datetime.strptime(
                    stay_data["last_detection"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        trajectory = EstimatedTrajectory(
            trajectory_id=traj_data.get("estimated_trajectory_id", traj_data.get("cluster_id", f"demo_traj_{len(trajectories)}")),
            route=traj_data["route"],
            stays=stays,
            cluster_ids=traj_data.get("cluster_ids")
        )
        trajectories.append(trajectory)

    return trajectories

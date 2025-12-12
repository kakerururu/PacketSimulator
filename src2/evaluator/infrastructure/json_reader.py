"""JSON読み込み機能"""

import json
from datetime import datetime
from typing import List
from ..domain.trajectory import (
    GroundTruthTrajectory,
    GroundTruthStay,
    EstimatedTrajectory,
    EstimatedStay,
)


def load_ground_truth_trajectories(file_path: str) -> List[GroundTruthTrajectory]:
    """Ground Truth JSONを読み込み

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
                    stay_data["arrival_time"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                departure_time=datetime.strptime(
                    stay_data["departure_time"],
                    "%Y-%m-%d %H:%M:%S.%f"
                ),
                duration_seconds=stay_data["duration_seconds"]
            )
            stays.append(stay)

        trajectory = GroundTruthTrajectory(
            trajectory_id=traj_data["trajectory_id"],
            walker_id=traj_data["walker_id"],
            route=traj_data["route"],
            stays=stays,
            model=traj_data.get("model"),
            integrated_payload_id=traj_data.get("integrated_payload_id")
        )
        trajectories.append(trajectory)

    return trajectories


def load_estimated_trajectories(file_path: str) -> List[EstimatedTrajectory]:
    """Estimated JSONを読み込み

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
            trajectory_id=traj_data["trajectory_id"],
            route=traj_data["route"],
            stays=stays,
            cluster_ids=traj_data.get("cluster_ids")
        )
        trajectories.append(trajectory)

    return trajectories

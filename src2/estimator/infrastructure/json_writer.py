"""推定結果JSON出力"""

import json
from pathlib import Path
from datetime import datetime
from typing import List
from ..domain.estimated_trajectory import EstimatedTrajectory
from ...shared.utils.datetime_utils import format_timestamp


def write_estimated_trajectories(
    trajectories: List[EstimatedTrajectory],
    output_file: str = "src2_result/estimated/trajectories.json",
    estimation_method: str = "stub",
) -> None:
    """推定軌跡リストをJSONファイルに出力

    Args:
        trajectories: 推定軌跡リスト
        output_file: 出力先JSONファイルパス
        estimation_method: 推定手法名（メタデータ用）

    Examples:
        >>> from ..domain.estimated_trajectory import EstimatedTrajectory
        >>> trajectories = []
        >>> write_estimated_trajectories(trajectories, "test_output.json", "stub")
    """
    # 出力ディレクトリを作成
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # クラスタ数を計算
    all_cluster_ids = set()
    for traj in trajectories:
        all_cluster_ids.update(traj.cluster_ids)

    # JSON構造を構築
    output_data = {
        "metadata": {
            "estimation_timestamp": format_timestamp(datetime.now()),
            "num_clusters": len(all_cluster_ids),
            "num_trajectories": len(trajectories),
            "estimation_method": estimation_method,
        },
        "trajectories": [
            {
                "trajectory_id": traj.trajectory_id,
                "cluster_ids": traj.cluster_ids,
                "route": traj.route,
                "stays": [
                    {
                        "detector_id": stay.detector_id,
                        "detections": [
                            {
                                "timestamp": format_timestamp(det.timestamp),
                                "hashed_id": det.hashed_id,
                                "sequence_number": det.sequence_number,
                                "is_judged": det.is_judged,
                            }
                            for det in stay.detections
                        ],
                        "first_detection": format_timestamp(stay.first_detection),
                        "last_detection": format_timestamp(stay.last_detection),
                        "estimated_arrival": format_timestamp(stay.estimated_arrival),
                        "estimated_departure": format_timestamp(stay.estimated_departure),
                        "estimated_duration_seconds": stay.estimated_duration_seconds,
                        "num_detections": stay.num_detections,
                    }
                    for stay in traj.stays
                ],
            }
            for traj in trajectories
        ],
    }

    # JSONファイルに書き込み
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

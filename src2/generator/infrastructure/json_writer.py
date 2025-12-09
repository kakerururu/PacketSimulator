"""Ground Truth JSON出力モジュール"""

import json
from pathlib import Path
from typing import List
from datetime import datetime
from ..domain.trajectory import Trajectory
from .utils import format_timestamp
from .config_loader import load_detectors, load_simulation_settings


def write_ground_truth(
    trajectories: List[Trajectory],
) -> None:
    """Ground Truth JSONを書き込む

    設定ファイルから必要な情報を直接読み込んで出力する。

    Args:
        trajectories: 軌跡のリスト

    Notes:
        - plan.mdの仕様に従った詳細なGround Truthを出力
        - 到着・出発・滞在時間を含む完全な情報
        - num_walkers, num_detectorsは設定ファイルから自動取得

    Examples:
        >>> from datetime import datetime
        >>> from ..domain.stay import Stay
        >>> stay = Stay("A", datetime(2024, 1, 14, 11, 0, 0),
        ...              datetime(2024, 1, 14, 11, 5, 0), 300.0)
        >>> traj = Trajectory("gt_traj_1", "Walker_1", "ABCD", stays=[stay])
        >>> write_ground_truth([traj])
    """
    # 設定ファイルから情報を読み込み
    detectors = load_detectors()
    simulation_settings = load_simulation_settings()

    # 出力ディレクトリを作成
    output_path = Path("src2_result/ground_truth/trajectories.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # メタデータ
    metadata = {
        "generation_timestamp": format_timestamp(datetime.now()),
        "num_walkers": simulation_settings["num_walkers_to_simulate"],
        "num_detectors": len(detectors),
        "num_trajectories": len(trajectories),
    }

    # 軌跡データ
    trajectory_list = []
    for traj in trajectories:
        trajectory_list.append(
            {
                "trajectory_id": traj.trajectory_id,
                "walker_id": traj.walker_id,  # 単一IDに変更済み
                "route": traj.route,
                "stays": [
                    {
                        "detector_id": stay.detector_id,
                        "arrival_time": format_timestamp(stay.arrival_time),
                        "departure_time": format_timestamp(stay.departure_time),
                        "duration_seconds": stay.duration_seconds,
                    }
                    for stay in traj.stays
                ],
            }
        )

    # JSON出力
    output_data = {"metadata": metadata, "trajectories": trajectory_list}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

"""推定された軌跡"""

from dataclasses import dataclass
from typing import List
from .estimated_stay import EstimatedStay


@dataclass
class EstimatedTrajectory:
    """推定された1つの軌跡

    クラスタリングと経路推定によって得られた軌跡。
    cluster_ids は、この軌跡を構成するクラスタのID群。

    Examples:
        >>> from datetime import datetime
        >>> from .estimated_stay import EstimatedStay
        >>> stay_a = EstimatedStay(
        ...     detector_id="A",
        ...     first_detection=datetime(2024, 1, 14, 11, 0, 5, 123000),
        ...     last_detection=datetime(2024, 1, 14, 11, 4, 55, 789000),
        ...     estimated_duration_seconds=290.666,
        ...     num_detections=21
        ... )
        >>> trajectory = EstimatedTrajectory(
        ...     trajectory_id="est_traj_1",
        ...     cluster_ids=["cluster_1"],
        ...     route="ABCD",
        ...     stays=[stay_a]
        ... )
    """

    trajectory_id: str  # 軌跡ID（例: "est_traj_1"）
    cluster_ids: List[str]  # クラスタID群（例: ["cluster_1"]）
    route: str  # 経路文字列（例: "ABCD"）
    stays: List[EstimatedStay]  # 滞在リスト

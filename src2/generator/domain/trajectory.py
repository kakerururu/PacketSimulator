from dataclasses import dataclass
from typing import List
from .stay import Stay


@dataclass
class Trajectory:
    """1つの軌跡（Ground Truth）

    通行人が複数の検出器を訪問した経路の実際の記録。
    シミュレーションで生成されるグランドトゥルースデータ。

    Examples:
        >>> from datetime import datetime
        >>> stay_a = Stay("A", datetime(2024, 1, 14, 11, 0, 0),
        ...               datetime(2024, 1, 14, 11, 5, 0), 300.0)
        >>> stay_b = Stay("B", datetime(2024, 1, 14, 11, 6, 0),
        ...               datetime(2024, 1, 14, 11, 11, 0), 300.0)
        >>> trajectory = Trajectory(
        ...     trajectory_id="gt_traj_1",
        ...     walker_id="Walker_1",
        ...     route="AB",
        ...     timeline=[stay_a, stay_b]
        ... )
    """

    trajectory_id: str  # 軌跡ID（例: "gt_traj_1"）
    walker_id: str  # この軌跡を構成する通行人のID（例: "Walker_1"）
    route: str  # ルート（例: "ABCD"）
    timeline: List[Stay]  # 滞在情報のリスト（時系列順）

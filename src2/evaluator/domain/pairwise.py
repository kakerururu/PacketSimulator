"""2地点間移動のドメインモデル

2つの検知器間の移動人数を時間ビン付きで表現する。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class PairwiseMovement:
    """2地点間の移動カウント

    Attributes:
        origin: 出発検知器ID (例: "A")
        origin_bin: 出発時間ビン (例: "0900~0930")
        destination: 到着検知器ID (例: "B")
        destination_bin: 到着時間ビン (例: "1000~1030")
        gt_count: Ground Truth人数
        est_count: 推定人数

    Examples:
        >>> movement = PairwiseMovement(
        ...     origin="A",
        ...     origin_bin="0900~0930",
        ...     destination="B",
        ...     destination_bin="1000~1030",
        ...     gt_count=30,
        ...     est_count=24
        ... )
    """

    origin: str
    origin_bin: str
    destination: str
    destination_bin: str
    gt_count: int
    est_count: int

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "origin": self.origin,
            "origin_bin": self.origin_bin,
            "destination": self.destination,
            "destination_bin": self.destination_bin,
            "gt_count": self.gt_count,
            "est_count": self.est_count,
        }


@dataclass
class PairwiseMovementResult:
    """2地点間移動の集計結果

    Attributes:
        time_bin_minutes: 時間ビン幅（分）
        movements: 移動カウントのリスト

    Examples:
        >>> result = PairwiseMovementResult(
        ...     time_bin_minutes=30,
        ...     movements=[movement1, movement2]
        ... )
    """

    time_bin_minutes: int
    movements: List[PairwiseMovement] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "time_bin_minutes": self.time_bin_minutes,
            "movements": [m.to_dict() for m in self.movements],
        }

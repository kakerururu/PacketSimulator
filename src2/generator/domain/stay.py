from dataclasses import dataclass
from datetime import datetime


@dataclass
class Stay:
    """1つの検出器での滞在（Ground Truth）

    通行人が1つの検出器エリアに滞在した期間の実際の記録。
    シミュレーションで生成される正解データ。

    Examples:
        >>> from datetime import datetime
        >>> stay = Stay(
        ...     detector_id="A",
        ...     arrival_time=datetime(2024, 1, 14, 11, 0, 0),
        ...     departure_time=datetime(2024, 1, 14, 11, 5, 0),
        ...     duration_seconds=300.0
        ... )
    """
    detector_id: str           # 滞在した検出器のID（例: "A"）
    arrival_time: datetime     # 到着時刻
    departure_time: datetime   # 出発時刻
    duration_seconds: float    # 滞在時間（秒）

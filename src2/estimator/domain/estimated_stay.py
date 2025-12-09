"""推定された滞在情報"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class EstimatedStay:
    """推定された1つの検出器での滞在

    検出レコードのクラスタリング結果から推定された滞在情報。

    Examples:
        >>> from datetime import datetime
        >>> stay = EstimatedStay(
        ...     detector_id="A",
        ...     first_detection=datetime(2024, 1, 14, 11, 0, 5, 123000),
        ...     last_detection=datetime(2024, 1, 14, 11, 4, 55, 789000),
        ...     estimated_duration_seconds=290.666,
        ...     num_detections=21
        ... )
    """

    detector_id: str  # 検出器ID
    first_detection: datetime  # 最初の検出時刻
    last_detection: datetime  # 最後の検出時刻
    estimated_duration_seconds: float  # 推定滞在時間（秒）
    num_detections: int  # 検出数

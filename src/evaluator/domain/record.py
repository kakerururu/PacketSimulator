from dataclasses import dataclass
from datetime import datetime


@dataclass
class DetectionRecord:
    """
    検出器によって記録されたスマートフォンの検出レコードを表すデータクラス。
    """

    timestamp: datetime
    hashed_payload: str
    walker_id: str
    detector_id: str
    detector_x: float
    detector_y: float
    sequence_number: int
    is_judged: bool = False

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Walker:
    """
    シミュレーションにおける通行人（人）を表すデータクラス。
    各ウォーカーは一意のID、割り当てられたスマートフォンモデル、
    動的ペイロードID（存在する場合）、および移動ルートを持つ。
    """

    id: str
    model: str
    assigned_payload_id: Optional[
        str
    ]  # 確定でユニークなペイロードID（存在しない場合はNone）
    route: str


@dataclass
class DetectionEvent:
    """
    検出器によって記録されたスマートフォンの検出イベントを表すデータクラス。
    """

    timestamp: datetime
    walker_id: str
    hashed_payload: str
    detector_id: str
    detector_x: float
    detector_y: float
    sequence_number: int

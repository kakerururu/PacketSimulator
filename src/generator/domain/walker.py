from dataclasses import dataclass
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

"""検出レコード（Estimator用）"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class DetectionRecord:
    """検出ログから読み込んだレコード

    Estimatorでは walker_id は使用しない（Ground Truth情報のため）。
    is_judged フラグはクラスタリング処理で使用される。

    Examples:
        >>> from datetime import datetime
        >>> record = DetectionRecord(
        ...     timestamp=datetime(2024, 1, 14, 11, 0, 5, 123000),
        ...     walker_id="Walker_1",
        ...     hashed_id="C_01_base_hash",
        ...     detector_id="A",
        ...     sequence_number=100,
        ...     is_judged=False
        ... )
    """

    timestamp: datetime  # 検出時刻（ミリ秒精度）
    walker_id: str  # Ground Truth情報（Estimatorでは使用しない）
    hashed_id: str  # ペイロードのハッシュ値
    detector_id: str  # 検出器ID
    sequence_number: int  # シーケンス番号（0-4095）
    is_judged: bool = False  # クラスタリング処理済みフラグ
    cluster_id: str = ""  # 所属クラスタID（クラスタリング時に設定）

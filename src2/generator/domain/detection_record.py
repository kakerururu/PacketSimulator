from dataclasses import dataclass
from datetime import datetime


@dataclass
class DetectionRecord:
    """検出レコード（ログに記録される1行）

    検出器がスマートフォンのBluetooth信号を検出した記録。
    CSVファイルに出力される1行に対応する。

    Examples:
        >>> from datetime import datetime
        >>> record = DetectionRecord(
        ...     timestamp=datetime(2024, 1, 14, 11, 0, 5, 123000),
        ...     walker_id="Walker_1",
        ...     hashed_payload="C_01_base_payload",
        ...     detector_id="A",
        ...     sequence_number=100
        ... )
    """

    timestamp: datetime  # 検出時刻（ミリ秒精度）
    walker_id: str  # 通行人ID（Ground Truth用、実運用では存在しない）
    hashed_id: str  # ペイロードのハッシュ値（例: "C_01_base_payload"）
    detector_id: str  # 検出器ID（例: "A"）
    sequence_number: int  # シーケンス番号（0-4095）

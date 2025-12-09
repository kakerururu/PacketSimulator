from dataclasses import dataclass


@dataclass
class Detector:
    """検出器 (全モジュールで共通)

    スマートフォンのBluetooth信号を検出するセンサー。
    各検出器は固有のIDと座標を持つ。

    Examples:
        >>> detector_a = Detector(id="A", x=-10000.0, y=10000.0)
        >>> detector_b = Detector(id="B", x=10000.0, y=10000.0)
        >>> detector_c = Detector(id="C", x=10000.0, y=-10000.0)
        >>> detector_d = Detector(id="D", x=-10000.0, y=-10000.0)
    """
    id: str          # 検出器ID（例: "A", "B", "C", "D"）
    x: float         # X座標（メートル）
    y: float         # Y座標（メートル）

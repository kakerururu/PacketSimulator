"""距離計算ユーティリティ"""

import math
from ..domain.detector import Detector


def calculate_euclidean_distance(det1: Detector, det2: Detector) -> float:
    """2つの検出器間のユークリッド距離を計算

    Args:
        det1: 検出器1
        det2: 検出器2

    Returns:
        ユークリッド距離 (メートル)

    Examples:
        >>> from src2.shared.domain.detector import Detector
        >>> det_a = Detector(id="A", x=0.0, y=0.0)
        >>> det_b = Detector(id="B", x=100.0, y=0.0)
        >>> calculate_euclidean_distance(det_a, det_b)
        100.0
    """
    return math.sqrt((det2.x - det1.x) ** 2 + (det2.y - det1.y) ** 2)


def calculate_min_travel_time(det1: Detector, det2: Detector, speed: float) -> float:
    """検出器間の最小移動時間を計算

    Args:
        det1: 検出器1
        det2: 検出器2
        speed: 移動速度 (m/s)

    Returns:
        最小移動時間 (秒)

    Examples:
        >>> from src2.shared.domain.detector import Detector
        >>> det_a = Detector(id="A", x=0.0, y=0.0)
        >>> det_b = Detector(id="B", x=140.0, y=0.0)
        >>> calculate_min_travel_time(det_a, det_b, 1.4)
        100.0
    """
    distance = calculate_euclidean_distance(det1, det2)
    return distance / speed if speed > 0 else 0.0

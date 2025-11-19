import math
import random
from domain.detector import Detector


def calculate_travel_time(
    ax: float, ay: float, bx: float, by: float, speed: float, variation_factor: float
) -> float:
    """
    2つの座標間のユークリッド距離を計算し、定義された速度とばらつき要因に基づいて移動時間を算出します。
    """
    distance = math.sqrt((bx - ax) ** 2 + (by - ay) ** 2)
    base_time = distance / speed if speed > 0 else 0
    # ランダムなばらつきを追加
    variation = (
        base_time * variation_factor * (random.random() * 2 - 1)
    )  # -variation_factorから+variation_factorの範囲
    travel_time = max(0, base_time + variation)
    return travel_time


def calculate_min_travel_time(det1: Detector, det2: Detector, speed: float) -> float:
    """検知器AからBへの最小移動時間を計算（ばらつきなし）"""
    distance = math.sqrt((det2.x - det1.x) ** 2 + (det2.y - det1.y) ** 2)
    return distance / speed if speed > 0 else 0

"""滞在リスト生成ユースケース

責務: 通行人の滞在リスト生成と移動時間計算
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict
from ..domain.stay import Stay
from ...shared.domain.detector import Detector
from ..infrastructure.config_loader import load_simulation_settings


def calculate_moving_time_from_detector_to_detector(
    from_detector: Detector,
    to_detector: Detector,
    walker_speed: float,
    variation_factor: float,
) -> float:
    """2つの検出器間の移動時間を計算

    Args:
        from_detector: 出発検出器
        to_detector: 到着検出器
        walker_speed: 通行人の移動速度 (m/s)
        variation_factor: 移動速度のばらつき係数

    Returns:
        移動時間（秒）
    """
    # ユークリッド距離
    distance = (
        (to_detector.x - from_detector.x) ** 2 + (to_detector.y - from_detector.y) ** 2
    ) ** 0.5

    base_time = distance / walker_speed if walker_speed > 0 else 0

    # ランダムなばらつきを追加
    variation = base_time * variation_factor * (random.random() * 2 - 1)
    travel_time = max(0, base_time + variation)

    return travel_time


def generate_stays(
    route: str,
    detectors: Dict[str, Detector],
    start_time: datetime,
) -> List[Stay]:
    """ルートに基づいて滞在リストを生成

    設定ファイルから滞在時間や移動速度などのパラメータを読み込み、
    通行人の各検出器での滞在情報を生成します。

    Args:
        route: ルート文字列 (例: "ABCD")
        detectors: 検出器の辞書 {id: Detector}
        start_time: シミュレーション開始時刻

    Returns:
        滞在情報のリスト。各要素はStayオブジェクト。

    Examples:
        >>> from datetime import datetime
        >>> from ...shared.domain.detector import Detector
        >>> detectors = {
        ...     "A": Detector("A", 0.0, 0.0),
        ...     "B": Detector("B", 10.0, 0.0),
        ... }
        >>> start = datetime(2024, 1, 14, 11, 0, 0)
        >>> stays = generate_stays("AB", detectors, start)
        >>> len(stays)
        2
        >>> stays[0].detector_id
        'A'
        >>> stays[0].arrival_time
        datetime.datetime(2024, 1, 14, 11, 0)
        >>> 180 <= stays[0].duration_seconds <= 420
        True
        >>> stays[1].detector_id
        'B'
    """
    # 設定ファイルから数値パラメータを読み込む
    settings = load_simulation_settings()
    stay_duration_min = settings["stay_duration_min_seconds"]
    stay_duration_max = settings["stay_duration_max_seconds"]
    walker_speed = settings["walker_speed"]
    variation_factor = settings["variation_factor"]

    stays = []
    current_time = start_time

    # ルート文字列から順番通りの検出器リストを作成
    route_detectors = [detectors[detector_id] for detector_id in route]

    # リストにおけるインデックスとリスト内の要素の値を取得しながらループ
    # i=0,detector=検出器A
    for i, detector in enumerate(route_detectors):
        # 到着時刻
        arrival_time = current_time

        # 滞在時間を設定値の範囲でランダムに決定
        stay_duration = random.uniform(stay_duration_min, stay_duration_max)
        departure_time = arrival_time + timedelta(seconds=stay_duration)

        stays.append(
            Stay(
                detector_id=detector.id,
                arrival_time=arrival_time,
                departure_time=departure_time,
                duration_seconds=stay_duration,
            )
        )

        # 次の検出器への移動時間を計算
        if i < len(route_detectors) - 1:
            # 次の検出器の時間を設定するための処理
            next_detector = route_detectors[i + 1]
            duration_time_to_next_detector = (
                calculate_moving_time_from_detector_to_detector(
                    detector, next_detector, walker_speed, variation_factor
                )
            )
            current_time = departure_time + timedelta(
                seconds=duration_time_to_next_detector
            )

    return stays

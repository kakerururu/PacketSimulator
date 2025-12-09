"""シミュレーション実行ユースケース

責務: 各ユースケースを組み合わせてシミュレーション全体を実行
"""

from datetime import datetime
from typing import List, Tuple
from ..domain.trajectory import Trajectory
from ..domain.detection_record import DetectionRecord
from ..domain.payload_config import PayloadDefinitionsDict
from ...shared.domain.detector import Detector
from . import walker_generation
from . import stay_generation
from . import record_generation


def run_simulation(
    detectors: List[Detector],
    payload_definitions: PayloadDefinitionsDict,
    model_names: List[str],
    model_probabilities: List[float],
    num_walkers: int,
    start_time: datetime,
) -> Tuple[List[Trajectory], List[DetectionRecord]]:
    """シミュレーション全体を実行

    Args:
        detectors: 検出器のリスト
        payload_definitions: ペイロード定義
        model_names: モデル名のリスト
        model_probabilities: モデルの選択確率
        num_walkers: 生成する通行人の数
        start_time: シミュレーション開始時刻

    Returns:
        (軌跡リスト, 検出レコードリスト) のタプル
    """
    # 検出器を辞書に変換
    detector_dict = {d.id: d for d in detectors}

    # 通行人生成
    walkers = walker_generation.generate_walkers(
        num_walkers=num_walkers,
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities,
    )

    trajectories = []
    all_records = []

    # 各通行人の軌跡とレコード生成
    for i, walker in enumerate(walkers):
        # 滞在リスト生成
        stays = stay_generation.generate_stays(
            route=walker.route,
            detectors=detector_dict,
            start_time=start_time,
        )

        # 軌跡作成
        trajectory = Trajectory(
            trajectory_id=f"gt_traj_{i + 1}",
            walker_id=walker.id,
            route=walker.route,
            stays=stays,
        )
        trajectories.append(trajectory)

        # レコード生成
        records = record_generation.generate_detection_records(
            walker=walker,
            stays=stays,
            payload_definitions=payload_definitions,
        )
        all_records.extend(records)

    return trajectories, all_records

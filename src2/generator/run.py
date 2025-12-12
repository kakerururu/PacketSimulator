"""Generator プログラマブルAPI

バッチ実行やテストからプログラム的に呼び出すためのインターフェース。
既存のmain.pyは変更せず、このモジュールで引数による制御を提供する。
"""

import random
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

from .domain.trajectory import Trajectory
from .domain.detection_record import DetectionRecord
from .infrastructure.config_loader import (
    load_detectors,
    load_payloads,
    load_simulation_settings,
)
from .infrastructure.csv_writer import write_detector_logs
from .infrastructure.json_writer import write_ground_truth
from .usecase import simulation


def run_generator(
    num_walkers: int,
    output_dir: str,
    seed: Optional[int] = None,
    start_time: Optional[datetime] = None,
) -> Tuple[List[Trajectory], List[DetectionRecord]]:
    """プログラムから呼び出し可能なGenerator

    シミュレーションを実行し、指定されたディレクトリに結果を出力する。

    Args:
        num_walkers: 生成する通行人の数
        output_dir: 出力ディレクトリ（この下にground_truth/, detector_logs/が作成される）
        seed: 乱数シード（Noneの場合はランダム）
        start_time: シミュレーション開始時刻（デフォルト: 2024-01-14 11:00:00）

    Returns:
        (軌跡リスト, 検出レコードリスト) のタプル

    Examples:
        >>> trajectories, records = run_generator(
        ...     num_walkers=50,
        ...     output_dir="experiments/run_001",
        ...     seed=42
        ... )
    """
    # 乱数シードを設定
    if seed is not None:
        random.seed(seed)

    # デフォルト開始時刻
    if start_time is None:
        start_time = datetime(2024, 1, 14, 11, 0, 0)

    # 出力パスを構築
    output_path = Path(output_dir)
    ground_truth_file = str(output_path / "ground_truth" / "trajectories.json")
    detector_logs_dir = str(output_path / "detector_logs")

    # 設定ファイルを読み込み
    detectors = load_detectors()
    payload_definitions, model_names, model_probabilities = load_payloads()

    # シミュレーション実行
    trajectories, detection_records = simulation.run_simulation(
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities,
        num_walkers=num_walkers,
        start_time=start_time,
    )

    # Ground Truth JSONを出力
    write_ground_truth(trajectories, output_file=ground_truth_file)

    # 検出ログCSVを出力
    write_detector_logs(detection_records, output_dir_path=detector_logs_dir)

    return trajectories, detection_records

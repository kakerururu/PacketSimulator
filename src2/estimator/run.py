"""Estimator プログラマブルAPI

バッチ実行やテストからプログラム的に呼び出すためのインターフェース。
既存のmain.pyは変更せず、このモジュールで引数による制御を提供する。
"""

from pathlib import Path
from typing import List

from .domain.estimated_trajectory import EstimatedTrajectory
from .infrastructure.csv_reader import read_detector_logs
from .infrastructure.json_writer import write_estimated_trajectories
from .usecase.group_by_payload import group_records_by_payload
from .usecase.estimate_trajectories import estimate_trajectories


def run_estimator(
    input_dir: str,
    output_dir: str,
    verbose: bool = False,
) -> List[EstimatedTrajectory]:
    """プログラムから呼び出し可能なEstimator

    検出ログを読み込み、軌跡推定を実行し、結果を出力する。

    Args:
        input_dir: 入力ディレクトリ（detector_logs/が含まれる）
        output_dir: 出力ディレクトリ（この下にestimated/が作成される）
        verbose: 詳細ログを出力するか

    Returns:
        推定軌跡のリスト

    Examples:
        >>> trajectories = run_estimator(
        ...     input_dir="experiments/run_001",
        ...     output_dir="experiments/run_001"
        ... )
    """
    # パスを構築
    detector_logs_dir = str(Path(input_dir) / "detector_logs")
    estimated_file = str(Path(output_dir) / "estimated" / "trajectories.json")

    # 検出ログCSVを読み込み
    detection_records = read_detector_logs(detector_logs_dir)
    if verbose:
        print(f"読み込んだレコード数: {len(detection_records)}")

    # ペイロードごとにグループ化
    grouped_records = group_records_by_payload(detection_records)
    if verbose:
        print(f"グループ数: {len(grouped_records)}")

    # 軌跡推定（複数パスクラスタリング）
    # verbose=Falseの場合は標準出力を抑制
    import sys
    import io

    if not verbose:
        # 標準出力を一時的に抑制
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

    try:
        estimated_trajectories, _ = estimate_trajectories(
            grouped_records=grouped_records,
            max_passes=10,
            output_per_pass=False,  # バッチ実行時は中間出力しない
        )
    finally:
        if not verbose:
            sys.stdout = old_stdout

    # 推定結果JSONを出力
    write_estimated_trajectories(
        estimated_trajectories,
        output_file=estimated_file,
        estimation_method="trajectory_estimation",
    )

    return estimated_trajectories

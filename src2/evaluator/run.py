"""Evaluator プログラマブルAPI

バッチ実行やテストからプログラム的に呼び出すためのインターフェース。
既存のmain.pyは変更せず、このモジュールで引数による制御を提供する。
"""

from pathlib import Path

from .domain.evaluation import EvaluationResult
from .usecase.evaluate_trajectories import evaluate_trajectories, EvaluationConfig
from .infrastructure.json_reader import (
    load_ground_truth_trajectories,
    load_estimated_trajectories,
)
from .infrastructure.json_writer import save_evaluation_result


def run_evaluator(
    ground_truth_path: str,
    estimated_path: str,
    output_path: str,
    tolerance_seconds: float = 600.0,
) -> EvaluationResult:
    """プログラムから呼び出し可能なEvaluator

    Ground Truthと推定結果を比較し、評価結果を出力する。

    Args:
        ground_truth_path: Ground Truth JSONファイルパス
        estimated_path: 推定結果JSONファイルパス
        output_path: 評価結果JSONの出力パス
        tolerance_seconds: 時刻の許容誤差（秒）

    Returns:
        EvaluationResult: 評価結果

    Examples:
        >>> result = run_evaluator(
        ...     ground_truth_path="experiments/run_001/ground_truth/trajectories.json",
        ...     estimated_path="experiments/run_001/estimated/trajectories.json",
        ...     output_path="experiments/run_001/evaluation/results.json"
        ... )
    """
    # データ読み込み
    gt_trajectories = load_ground_truth_trajectories(ground_truth_path)
    est_trajectories = load_estimated_trajectories(estimated_path)

    # 評価実行
    config = EvaluationConfig(tolerance_seconds=tolerance_seconds)
    result = evaluate_trajectories(
        gt_trajectories,
        est_trajectories,
        config,
        ground_truth_file=ground_truth_path,
        estimated_file=estimated_path,
    )

    # 出力ディレクトリを作成
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 結果を保存
    save_evaluation_result(result, output_path)

    return result

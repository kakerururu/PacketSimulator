"""Evaluator プログラマブルAPI

バッチ実行やテストからプログラム的に呼び出すためのインターフェース。
既存のmain.pyは変更せず、このモジュールで引数による制御を提供する。

【評価方式】
時間ビニング方式を採用。GT・Est両方に同じビニングルールを適用し、
同じルート名の軌跡を同一ルートとしてカウントする。
"""

import csv
from pathlib import Path

from .domain.evaluation import EvaluationResult
from .domain.pairwise import PairwiseMovementResult
from .usecase.evaluate_trajectories import evaluate_trajectories, EvaluationConfig
from .usecase.pairwise_movement import calculate_pairwise_movements
from .infrastructure.json_reader import (
    load_ground_truth_trajectories,
    load_estimated_trajectories,
)
from .infrastructure.json_writer import save_evaluation_result


def _save_pairwise_csv(pairwise_result: PairwiseMovementResult, output_path: str) -> None:
    """2地点間移動カウントをCSVで保存"""
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["origin", "origin_bin", "destination", "destination_bin", "gt_count", "est_count"])
        for m in pairwise_result.movements:
            writer.writerow([m.origin, m.origin_bin, m.destination, m.destination_bin, m.gt_count, m.est_count])


def run_evaluator(
    ground_truth_path: str,
    estimated_path: str,
    output_path: str,
    time_bin_minutes: int = 30,
) -> EvaluationResult:
    """プログラムから呼び出し可能なEvaluator

    Ground Truthと推定結果を比較し、評価結果を出力する。

    Args:
        ground_truth_path: Ground Truth JSONファイルパス
        estimated_path: 推定結果JSONファイルパス
        output_path: 評価結果JSONの出力パス
        time_bin_minutes: 時間ビンの幅（分）。デフォルト30分。

    Returns:
        EvaluationResult: 評価結果

    Examples:
        >>> result = run_evaluator(
        ...     ground_truth_path="experiments/run_001/ground_truth/trajectories.json",
        ...     estimated_path="experiments/run_001/estimated/trajectories.json",
        ...     output_path="experiments/run_001/evaluation/results.json",
        ...     time_bin_minutes=30
        ... )
    """
    # データ読み込み
    gt_trajectories = load_ground_truth_trajectories(ground_truth_path)
    est_trajectories = load_estimated_trajectories(estimated_path)

    # 評価実行
    config = EvaluationConfig(time_bin_minutes=time_bin_minutes)
    result = evaluate_trajectories(
        gt_trajectories,
        est_trajectories,
        config,
        ground_truth_file=ground_truth_path,
        estimated_file=estimated_path,
    )

    # 2地点間移動カウントを計算
    pairwise_result = calculate_pairwise_movements(
        gt_trajectories,
        est_trajectories,
        time_bin_minutes=time_bin_minutes,
    )
    result.pairwise_movements = pairwise_result

    # 出力ディレクトリを作成
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 結果を保存（JSONにはpairwise_movementsを含めない）
    result.pairwise_movements = None
    save_evaluation_result(result, output_path)
    result.pairwise_movements = pairwise_result  # 戻り値用に復元

    # 2地点間移動カウントをCSVで保存
    csv_path = str(output_dir / "pairwise_movements.csv")
    _save_pairwise_csv(pairwise_result, csv_path)

    return result

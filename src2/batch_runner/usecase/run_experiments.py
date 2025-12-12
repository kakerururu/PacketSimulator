"""実験実行のユースケース"""

from pathlib import Path
from typing import List, Dict, Any

from ..domain.experiment_config import ExperimentConfig
from ..domain.aggregated_result import ConditionResult, AggregatedResult
from ..infrastructure.result_aggregator import aggregate_metrics
from ..infrastructure.experiment_writer import (
    write_experiment_config,
    write_condition_summary,
    write_final_summary,
    write_seed_file,
)
from ...generator.run import run_generator
from ...estimator.run import run_estimator
from ...evaluator.run import run_evaluator


def run_single_experiment(
    num_walkers: int,
    run_dir: str,
    seed: int,
) -> Dict[str, Any]:
    """1回のシミュレーションを実行

    Args:
        num_walkers: 通行人数
        run_dir: 実行結果の出力ディレクトリ
        seed: 乱数シード

    Returns:
        評価結果のメトリクス辞書
    """
    # シードを記録
    write_seed_file(run_dir, seed)

    # 1. データ生成
    run_generator(
        num_walkers=num_walkers,
        output_dir=run_dir,
        seed=seed,
    )

    # 2. 軌跡推定
    run_estimator(
        input_dir=run_dir,
        output_dir=run_dir,
        verbose=False,
    )

    # 3. 評価
    ground_truth_path = str(Path(run_dir) / "ground_truth" / "trajectories.json")
    estimated_path = str(Path(run_dir) / "estimated" / "trajectories.json")
    evaluation_path = str(Path(run_dir) / "evaluation" / "results.json")

    result = run_evaluator(
        ground_truth_path=ground_truth_path,
        estimated_path=estimated_path,
        output_path=evaluation_path,
    )

    # 評価結果からメトリクスを抽出
    metrics = result.overall_metrics
    return {
        "mae": metrics.mae,
        "mse": metrics.mse,
        "rmse": metrics.rmse,
        "exact_match_rate": metrics.exact_match_rate,
        "total_gt_count": metrics.total_gt_count,
        "total_est_count": metrics.total_est_count,
        "total_absolute_error": metrics.total_absolute_error,
    }


def run_condition(
    num_walkers: int,
    num_runs: int,
    condition_dir: str,
    config: ExperimentConfig,
) -> ConditionResult:
    """1つの条件（num_walkers）で複数回実行

    Args:
        num_walkers: 通行人数
        num_runs: 実行回数
        condition_dir: 条件の出力ディレクトリ
        config: 実験設定

    Returns:
        条件の結果
    """
    run_results: List[Dict[str, Any]] = []

    for run_idx in range(num_runs):
        run_num = run_idx + 1
        run_dir = str(Path(condition_dir) / f"run_{run_num:03d}")
        seed = config.get_seed(num_walkers, run_idx)

        # 進捗表示
        print(f"[{num_walkers}人] {run_num}/{num_runs} 完了...")

        # 1回のシミュレーションを実行
        metrics = run_single_experiment(
            num_walkers=num_walkers,
            run_dir=run_dir,
            seed=seed,
        )
        run_results.append(metrics)

    # メトリクスを集約
    metrics_stats = aggregate_metrics(run_results)

    # 条件のサマリーを表示
    mae_stats = metrics_stats["mae"]
    print(f"[{num_walkers}人] {num_runs}/{num_runs} 完了 ✓")
    print(f"  → MAE: {mae_stats.mean:.3f} ± {mae_stats.std:.3f}")

    # 結果を構築
    condition_result = ConditionResult(
        num_walkers=num_walkers,
        num_runs=num_runs,
        metrics=metrics_stats,
        run_results=run_results,
    )

    # 条件のサマリーを保存
    summary_path = str(Path(condition_dir) / "summary.json")
    write_condition_summary(condition_result, summary_path)

    return condition_result


def run_experiments(config: ExperimentConfig) -> AggregatedResult:
    """バッチ実験を実行

    Args:
        config: 実験設定

    Returns:
        全体の集約結果
    """
    experiment_id = config.get_experiment_id()
    experiment_dir = str(Path(config.output_dir) / experiment_id)

    print("=== バッチ実験開始 ===")
    print(f"条件: num_walkers = {config.num_walkers_list}, 各{config.num_runs}回実行")
    print(f"出力先: {experiment_dir}")
    print()

    # 実験設定を保存
    write_experiment_config(config, experiment_dir)

    # 各条件を実行
    condition_results: List[ConditionResult] = []

    for num_walkers in config.num_walkers_list:
        condition_dir = str(Path(experiment_dir) / f"walkers_{num_walkers:03d}")
        print()

        result = run_condition(
            num_walkers=num_walkers,
            num_runs=config.num_runs,
            condition_dir=condition_dir,
            config=config,
        )
        condition_results.append(result)

    # 全体の結果を構築
    aggregated_result = AggregatedResult(
        experiment_id=experiment_id,
        config=config.to_dict(),
        conditions=condition_results,
    )

    # 最終サマリーを保存
    final_summary_path = str(Path(experiment_dir) / "final_summary.json")
    write_final_summary(aggregated_result, final_summary_path)

    print()
    print("=== 実験完了 ===")
    print(f"結果: {experiment_dir}/")

    return aggregated_result

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
    time_bins: List[int],
) -> Dict[int, Dict[str, Any]]:
    """1回のシミュレーションを実行

    Args:
        num_walkers: 通行人数
        run_dir: 実行結果の出力ディレクトリ
        seed: 乱数シード
        time_bins: 評価する時間ビンのリスト（例: [15, 30, 60]）

    Returns:
        時間ビンごとの評価結果メトリクス辞書
        例: {15: {...}, 30: {...}, 60: {...}}
    """
    # シードを記録
    write_seed_file(run_dir, seed)

    # 1. データ生成（1回だけ）
    run_generator(
        num_walkers=num_walkers,
        output_dir=run_dir,
        seed=seed,
    )

    # 2. 軌跡推定（1回だけ）
    run_estimator(
        input_dir=run_dir,
        output_dir=run_dir,
        verbose=False,
    )

    # 3. 評価（各時間ビンで実行）
    ground_truth_path = str(Path(run_dir) / "ground_truth" / "trajectories.json")
    estimated_path = str(Path(run_dir) / "estimated" / "trajectories.json")

    results_by_bin: Dict[int, Dict[str, Any]] = {}

    for time_bin in time_bins:
        # 時間ビンごとに別ディレクトリに出力
        if len(time_bins) > 1:
            evaluation_path = str(Path(run_dir) / "evaluation" / f"results_bin{time_bin}.json")
        else:
            evaluation_path = str(Path(run_dir) / "evaluation" / "results.json")

        result = run_evaluator(
            ground_truth_path=ground_truth_path,
            estimated_path=estimated_path,
            output_path=evaluation_path,
            time_bin_minutes=time_bin,
        )

        # 評価結果からメトリクスを抽出
        metrics = result.overall_metrics
        results_by_bin[time_bin] = {
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "tracking_rate": metrics.tracking_rate,
            "total_gt_count": metrics.total_gt_count,
            "total_est_count": metrics.total_est_count,
            "total_absolute_error": metrics.total_absolute_error,
        }

    return results_by_bin


def run_condition(
    num_walkers: int,
    num_runs: int,
    condition_dir: str,
    config: ExperimentConfig,
) -> Dict[int, ConditionResult]:
    """1つの条件（num_walkers）で複数回実行

    Args:
        num_walkers: 通行人数
        num_runs: 実行回数
        condition_dir: 条件の出力ディレクトリ
        config: 実験設定

    Returns:
        時間ビンごとの条件結果
        例: {15: ConditionResult, 30: ConditionResult, 60: ConditionResult}
    """
    time_bins = config.get_time_bins_to_evaluate()

    # 時間ビンごとの結果を格納
    run_results_by_bin: Dict[int, List[Dict[str, Any]]] = {
        tb: [] for tb in time_bins
    }

    for run_idx in range(num_runs):
        run_num = run_idx + 1
        run_dir = str(Path(condition_dir) / f"run_{run_num:03d}")
        seed = config.get_seed(num_walkers, run_idx)

        # 進捗表示
        print(f"[{num_walkers}人] {run_num}/{num_runs} 実行中...")

        # 1回のシミュレーションを実行（全時間ビンで評価）
        metrics_by_bin = run_single_experiment(
            num_walkers=num_walkers,
            run_dir=run_dir,
            seed=seed,
            time_bins=time_bins,
        )

        # 各時間ビンの結果を振り分け
        for tb, metrics in metrics_by_bin.items():
            run_results_by_bin[tb].append(metrics)

    # 時間ビンごとに集約
    condition_results: Dict[int, ConditionResult] = {}

    for tb in time_bins:
        run_results = run_results_by_bin[tb]
        metrics_stats = aggregate_metrics(run_results)

        condition_result = ConditionResult(
            num_walkers=num_walkers,
            num_runs=num_runs,
            metrics=metrics_stats,
            run_results=run_results,
            time_bin=tb,
        )
        condition_results[tb] = condition_result

        # 条件のサマリーを保存
        if len(time_bins) > 1:
            summary_path = str(Path(condition_dir) / f"summary_bin{tb}.json")
        else:
            summary_path = str(Path(condition_dir) / "summary.json")
        write_condition_summary(condition_result, summary_path)

    # 結果表示
    print(f"[{num_walkers}人] {num_runs}/{num_runs} 完了 ✓")
    if len(time_bins) > 1:
        # 比較モード: 各時間ビンのMAEを表示
        for tb in time_bins:
            mae_stats = condition_results[tb].metrics["mae"]
            print(f"  → {tb}分ビン MAE: {mae_stats.mean:.3f} ± {mae_stats.std:.3f}")
    else:
        # 通常モード
        mae_stats = condition_results[time_bins[0]].metrics["mae"]
        print(f"  → MAE: {mae_stats.mean:.3f} ± {mae_stats.std:.3f}")

    return condition_results


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

    time_bins = config.get_time_bins_to_evaluate()
    if config.is_compare_mode:
        print(f"比較モード: 時間ビン = {time_bins}分")
    else:
        print(f"時間ビン: {time_bins[0]}分")

    print(f"出力先: {experiment_dir}")
    print()

    # 実験設定を保存
    write_experiment_config(config, experiment_dir)

    # 各条件を実行
    # 結果はフラットなリストに展開（比較モードでは複数time_bin分）
    condition_results: List[ConditionResult] = []

    for num_walkers in config.num_walkers_list:
        condition_dir = str(Path(experiment_dir) / f"walkers_{num_walkers:03d}")
        print()

        results_by_bin = run_condition(
            num_walkers=num_walkers,
            num_runs=config.num_runs,
            condition_dir=condition_dir,
            config=config,
        )

        # 時間ビンでソートしてリストに追加
        for tb in sorted(results_by_bin.keys()):
            condition_results.append(results_by_bin[tb])

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

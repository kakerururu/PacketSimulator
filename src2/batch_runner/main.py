"""バッチ実験実行 エントリーポイント

num_walkersを変化させながら複数回シミュレーションを実行し、
統計結果を収集する。

Usage:
    python -m src2.batch_runner.main --num-walkers 50 100 200 --runs 30

Examples:
    # 3条件 × 30回 = 90回のシミュレーション（毎回異なるランダムシード）
    python -m src2.batch_runner.main \\
        --num-walkers 50 100 200 \\
        --runs 30 \\
        --output-dir experiments/

    # 再現性のためにシードを固定
    python -m src2.batch_runner.main \\
        --num-walkers 10 20 \\
        --runs 3 \\
        --seed 42
"""

import argparse
import random

from .domain.experiment_config import ExperimentConfig
from .usecase.run_experiments import run_experiments


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="バッチ実験実行: num_walkersを変化させながら複数回シミュレーションを実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src2.batch_runner.main --num-walkers 50 100 200 --runs 30
  python -m src2.batch_runner.main --num-walkers 10 20 --runs 3 --seed 42
        """,
    )
    parser.add_argument(
        "--num-walkers",
        type=int,
        nargs="+",
        required=True,
        help="評価するnum_walkersのリスト（例: 50 100 200）",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=30,
        help="各条件での実行回数（デフォルト: 30）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="experiments/",
        help="出力ディレクトリ（デフォルト: experiments/）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="乱数シードのベース値（省略時: ランダム、指定時: 再現可能）",
    )

    args = parser.parse_args()

    # シードが指定されていない場合はランダムに生成
    if args.seed is None:
        base_seed = random.randint(0, 2**31 - 1)
        print(f"ランダムシード使用: {base_seed}")
        print("（再現するには --seed {0} を指定）".format(base_seed))
    else:
        base_seed = args.seed
        print(f"固定シード使用: {base_seed}")

    # 実験設定を構築
    config = ExperimentConfig(
        num_walkers_list=args.num_walkers,
        num_runs=args.runs,
        output_dir=args.output_dir,
        base_seed=base_seed,
    )

    # 実験を実行
    result = run_experiments(config)

    # 最終結果を表示
    print()
    print("=" * 60)
    print("最終結果サマリー")
    print("=" * 60)
    for cond in result.conditions:
        mae = cond.metrics["mae"]
        rmse = cond.metrics["rmse"]
        tracking_rate = cond.metrics["tracking_rate"]

        print(f"\n【{cond.num_walkers}人】 ({cond.num_runs}回実行)")
        print(f"  MAE:  {mae.mean:.3f} ± {mae.std:.3f} (95%CI: [{mae.ci_95_lower:.3f}, {mae.ci_95_upper:.3f}])")
        print(f"  RMSE: {rmse.mean:.3f} ± {rmse.std:.3f} (95%CI: [{rmse.ci_95_lower:.3f}, {rmse.ci_95_upper:.3f}])")
        print(f"  追跡率: {tracking_rate.mean:.1%} ± {tracking_rate.std:.1%}")

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()

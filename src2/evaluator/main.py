"""Evaluator エントリーポイント

時間ビニング方式による評価を実行する。
GT・Est両方に同じビニングルールを適用し、同じルート名の軌跡を同一ルートとしてカウントする。
"""

import argparse
import csv
import math
from pathlib import Path
from .usecase.evaluate_trajectories import evaluate_trajectories, EvaluationConfig
from .usecase.pairwise_movement import calculate_pairwise_movements
from .infrastructure.json_reader import (
    load_ground_truth_trajectories,
    load_estimated_trajectories
)
from .infrastructure.demo_json_reader import (
    load_demo_ground_truth_trajectories,
    load_demo_estimated_trajectories
)
from .infrastructure.json_writer import save_evaluation_result
from .infrastructure.logger import save_evaluation_logs


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="軌跡推定精度の評価（時間ビニング方式）"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="デモデータモード（src2_demo/のデータを使用）"
    )
    parser.add_argument(
        "--ground-truth",
        default=None,
        help="Ground Truth軌跡JSONのパス (デフォルト: 通常モード=src2_result/ground_truth/trajectories.json, デモモード=src2_demo/ground_truth_trajectories.json)"
    )
    parser.add_argument(
        "--estimated",
        default=None,
        help="推定軌跡JSONのパス (デフォルト: 通常モード=src2_result/estimated/trajectories.json, デモモード=src2_demo/estimated_trajectories.json)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="評価結果JSONの出力パス (デフォルト: 通常モード=src2_result/evaluation/results.json, デモモード=src2_demo/evaluation/results.json)"
    )
    parser.add_argument(
        "--time-bin",
        type=int,
        default=30,
        help="時間ビンの幅（分） (デフォルト: 30)"
    )
    parser.add_argument(
        "--time-bin",
        type=int,
        default=30,
        help="時間ビン幅（分）、2地点間移動カウントで使用 (デフォルト: 30)"
    )
    args = parser.parse_args()

    # デモモードの場合はデフォルトパスを上書き
    if args.demo:
        if args.ground_truth is None:
            args.ground_truth = "src2_demo/ground_truth_trajectories.json"
        if args.estimated is None:
            args.estimated = "src2_demo/estimated_trajectories.json"
        if args.output is None:
            args.output = "src2_demo/evaluation/results.json"
    else:
        # 通常モードのデフォルト
        if args.ground_truth is None:
            args.ground_truth = "src2_result/ground_truth/trajectories.json"
        if args.estimated is None:
            args.estimated = "src2_result/estimated/trajectories.json"
        if args.output is None:
            args.output = "src2_result/evaluation/results.json"

    print("=" * 60)
    mode_str = "【デモモード】" if args.demo else ""
    print(f"軌跡推定の評価（時間ビニング方式） {mode_str}")
    print("=" * 60)

    # 1. データ読み込み
    print(f"\n[1/3] データ読み込み中...")
    print(f"  Ground Truth: {args.ground_truth}")
    try:
        # デモモードの場合は専用ローダーを使用
        if args.demo:
            gt_trajectories = load_demo_ground_truth_trajectories(args.ground_truth)
        else:
            gt_trajectories = load_ground_truth_trajectories(args.ground_truth)
        print(f"    ✓ {len(gt_trajectories)}個のGround Truth軌跡を読み込みました")
    except FileNotFoundError:
        print(f"    ✗ エラー: ファイルが見つかりません: {args.ground_truth}")
        return
    except Exception as e:
        print(f"    ✗ Ground Truth読み込みエラー: {e}")
        return

    print(f"  推定結果: {args.estimated}")
    try:
        # デモモードの場合は専用ローダーを使用
        if args.demo:
            est_trajectories = load_demo_estimated_trajectories(args.estimated)
        else:
            est_trajectories = load_estimated_trajectories(args.estimated)
        num_est_loaded = len(est_trajectories)
        print(f"    ✓ {num_est_loaded}個の推定軌跡を読み込みました")
    except FileNotFoundError:
        print(f"    ✗ エラー: ファイルが見つかりません: {args.estimated}")
        return
    except Exception as e:
        print(f"    ✗ 推定結果読み込みエラー: {e}")
        return

    # 2. 評価実行
    print(f"\n[2/3] 評価実行中...")
    config = EvaluationConfig(time_bin_minutes=args.time_bin)
    print(f"  時間ビニング: {config.time_bin_minutes}分")

    result = evaluate_trajectories(
        gt_trajectories,
        est_trajectories,
        config,
        ground_truth_file=args.ground_truth,
        estimated_file=args.estimated
    )
    print(f"    ✓ 評価完了")

    # 3. 結果出力
    print(f"\n[3/5] 結果保存中...")
    print(f"  JSON出力先: {args.output}")
    try:
        save_evaluation_result(result, args.output)
        print(f"    ✓ JSON保存完了")
    except Exception as e:
        print(f"    ✗ 保存エラー: {e}")
        return

    # 4. 2地点間移動カウントをCSVで保存
    print(f"\n[4/5] 2地点間移動カウント計算中...")
    print(f"  時間ビン幅: {args.time_bin}分")
    pairwise_stats = None  # サマリー表示用に保存
    try:
        pairwise_result = calculate_pairwise_movements(
            gt_trajectories,
            est_trajectories,
            time_bin_minutes=args.time_bin,
        )

        # CSV保存
        output_dir = Path(args.output).parent
        csv_path = output_dir / "pairwise_movements.csv"

        movements = pairwise_result.movements
        errors = [abs(m.gt_count - m.est_count) for m in movements]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "origin", "origin_bin", "destination", "destination_bin",
                "gt_count", "est_count", "error"
            ])
            for m, error in zip(movements, errors):
                writer.writerow([
                    m.origin, m.origin_bin, m.destination, m.destination_bin,
                    m.gt_count, m.est_count, error
                ])

            # サマリー
            if movements:
                total = len(errors)
                mae = sum(errors) / total
                rmse = math.sqrt(sum(e**2 for e in errors) / total)
                exact_match = sum(1 for e in errors if e == 0)
                match_rate = exact_match / total

                writer.writerow([])
                writer.writerow(["# Summary"])
                writer.writerow(["total_movements", total])
                writer.writerow(["mae", f"{mae:.3f}"])
                writer.writerow(["rmse", f"{rmse:.3f}"])
                writer.writerow(["exact_match", exact_match])
                writer.writerow(["match_rate", f"{match_rate:.1%}"])

        print(f"    ✓ CSV保存完了: {csv_path}")
        if movements:
            print(f"    [Pairwise] 一致率: {match_rate:.1%} ({exact_match}/{total})")
            pairwise_stats = {
                "total": total,
                "exact_match": exact_match,
                "match_rate": match_rate,
                "mae": mae,
                "rmse": rmse,
                "time_bin": args.time_bin,
            }
    except Exception as e:
        print(f"    ✗ 2地点間移動カウントエラー: {e}")
        # 致命的ではないので続行

    # 5. 評価ログ出力
    print(f"\n[5/5] 評価ログ保存中...")
    try:
        # デモモードの場合はログディレクトリを変更
        log_dir = "src2_demo/evaluate_log" if args.demo else "src2_result/evaluate_log"
        log_files = save_evaluation_logs(result, log_dir=log_dir)
        print(f"    ✓ ログ保存完了:")
        print(f"      - サマリー: {log_files['summary']}")
        print(f"      - ルート評価詳細: {log_files['route_evaluations']}")
    except Exception as e:
        print(f"    ✗ ログ保存エラー: {e}")
        # ログ保存失敗は致命的ではないので続行

    # 5. サマリー表示
    print("\n" + "=" * 60)
    print("評価結果サマリー（時間ビニング方式）")
    print("=" * 60)

    print(f"\n【データ概要】")
    print(f"  GT軌跡:  {result.overall_metrics.total_gt_count}個")
    print(f"  Est軌跡: {num_est_loaded}個 (読み込み)")

    # メタデータから完全/部分ルート数を取得
    num_partial = result.metadata.get('num_partial_routes', 0)
    num_complete = result.metadata.get('num_complete_routes', 0)
    num_valid = result.overall_metrics.total_est_count

    print(f"\n【Est軌跡の分類】")
    print(f"")
    print(f"  部分ルート:     {num_partial}個 → 評価対象外")
    print(f"    └ 一部の検出器のみ経由 (例: ABC, DCB)")

    # 部分ルートの詳細を表示
    if num_partial > 0:
        partial_routes = result.metadata.get('partial_routes', [])
        if partial_routes:
            print(f"    └ 詳細:")
            for pr in partial_routes:
                print(f"      - {pr['trajectory_id']}: {pr['route']}")

    print(f"")
    print(f"  完全ルート:     {num_complete}個 → 評価対象")
    print(f"    └ すべての検出器(A,B,C,D)を経由")
    print(f"")
    print(f"【評価方法】")
    print(f"  時間ビニング: {config.time_bin_minutes}分")
    print(f"")
    print(f"  1. GT・Est両方の軌跡に同じビニングルールを適用")
    print(f"     例: 09:05着 → 0900ビン（30分ビンの場合）")
    print(f"")
    print(f"  2. ルート名を生成")
    print(f"     例: ABCD_0900_1000_1100_1200")
    print(f"")
    print(f"  3. 同じルート名 → 同一ルートとしてカウント")
    print(f"")
    print(f"  処理結果:")
    print(f"    統計に含む:     {num_valid}個 (すべての完全ルート)")

    print(f"\n【誤差指標】")
    print(f"  総絶対誤差:       {result.overall_metrics.total_absolute_error}人 (全ルートの誤差合計)")

    print(f"\n【精度指標】")
    print(f"  MAE (平均絶対誤差):      {result.overall_metrics.mae:.3f}")
    print(f"    → ルートあたり平均で{result.overall_metrics.mae:.2f}人ずれている")
    print(f"    → 0に近いほど良い（0が完璧）")

    print(f"\n  RMSE (二乗平均平方根誤差): {result.overall_metrics.rmse:.3f}")
    print(f"    → MAEより大きな誤差に厳しい指標")
    print(f"    → 0に近いほど良い（0が完璧）")
    if result.overall_metrics.rmse > result.overall_metrics.mae:
        print(f"    → RMSE > MAE なので、誤差にバラつきがある")

    print(f"\n  追跡率:                    {result.overall_metrics.tracking_rate:.1%}")
    print(f"    → GT人数とEst人数がピッタリ一致したルートの割合")
    print(f"    → 100%が理想")

    # ルート別の統計（アルファベット順）
    print(f"\n【ルート別の統計】")
    print(f"")
    print(f"  {'ルート':<8} {'GT人数':>6} {'Est人数':>7} {'誤差':>4} {'正確一致':>8}")
    print(f"  {'-'*8} {'-'*6} {'-'*7} {'-'*4} {'-'*8}")
    sorted_evaluations = sorted(result.stay_evaluations, key=lambda x: x.detector_id)
    for se in sorted_evaluations:
        match_status = "✓" if se.error == 0 else "✗"
        print(f"  {se.detector_id:<8} {se.gt_count:>6} {se.est_count:>7} {se.error:>4} {match_status:>8}")

    # 2地点間移動カウントの結果
    if pairwise_stats:
        print(f"\n【2地点間移動カウント】")
        print(f"  時間ビン幅: {pairwise_stats['time_bin']}分")
        print(f"  移動ペア数: {pairwise_stats['total']}個")
        print(f"  一致率:     {pairwise_stats['match_rate']:.1%} ({pairwise_stats['exact_match']}/{pairwise_stats['total']})")
        print(f"  MAE:        {pairwise_stats['mae']:.3f}")
        print(f"  RMSE:       {pairwise_stats['rmse']:.3f}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        # パイプやページャーを使用した時のエラーを無視
        import sys
        import os
        # stdout/stderrを閉じる際のエラーを抑制
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        sys.exit(0)

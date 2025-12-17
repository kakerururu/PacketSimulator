"""Evaluator DEVモード - デモデータ用エントリーポイント

estimator の DEVモード (main_dev.py) で出力された推定データを使用して評価を実行する。
- Ground Truth: src2_demo/ground_truth_trajectories.json
- 推定結果: src2_demo/estimated_trajectories.json
- 評価結果: src2_demo/evaluation/results.json
"""

from .usecase.evaluate_trajectories import evaluate_trajectories, EvaluationConfig
from .infrastructure.demo_json_reader import (
    load_demo_ground_truth_trajectories,
    load_demo_estimated_trajectories
)
from .infrastructure.json_writer import save_evaluation_result
from .infrastructure.logger import save_evaluation_logs


def main_dev():
    """DEVモード実行関数（デモデータ用）"""
    # パス設定
    ground_truth_path = "src2_demo/ground_truth_trajectories.json"
    estimated_path = "src2_demo/estimated_trajectories.json"
    output_path = "src2_demo/evaluation/results.json"
    log_dir = "src2_demo/evaluate_log"
    tolerance_seconds = 1200.0  # 20分

    print("=== 軌跡推定の評価開始 (DEVモード) ===")
    print("📁 使用データ: src2_demo/\n")

    # 1. データ読み込み
    print("[Phase 1] データ読み込み中...")
    print(f"  Ground Truth: {ground_truth_path}")
    try:
        gt_trajectories = load_demo_ground_truth_trajectories(ground_truth_path)
        print(f"  ✓ {len(gt_trajectories)}個のGround Truth軌跡を読み込みました")
    except FileNotFoundError:
        print(f"  ✗ エラー: ファイルが見つかりません: {ground_truth_path}")
        return
    except Exception as e:
        print(f"  ✗ Ground Truth読み込みエラー: {e}")
        return

    print(f"  推定結果: {estimated_path}")
    try:
        est_trajectories = load_demo_estimated_trajectories(estimated_path)
        num_est_loaded = len(est_trajectories)
        print(f"  ✓ {num_est_loaded}個の推定軌跡を読み込みました")
    except FileNotFoundError:
        print(f"  ✗ エラー: ファイルが見つかりません: {estimated_path}")
        print("  → 先に estimator の DEVモードを実行してください:")
        print("    python -m src2.estimator.main_dev")
        return
    except Exception as e:
        print(f"  ✗ 推定結果読み込みエラー: {e}")
        return

    # 2. 評価実行
    print(f"\n[Phase 2] 評価実行中...")
    config = EvaluationConfig(tolerance_seconds=tolerance_seconds)
    print(f"  許容誤差: {config.tolerance_seconds}秒 ({config.tolerance_seconds/60:.1f}分)")

    result = evaluate_trajectories(
        gt_trajectories,
        est_trajectories,
        config,
        ground_truth_file=ground_truth_path,
        estimated_file=estimated_path
    )
    print(f"  ✓ 評価完了")

    # 3. 結果保存
    print(f"\n[Phase 3] 結果保存中...")
    print(f"  JSON出力先: {output_path}")
    try:
        save_evaluation_result(result, output_path)
        print(f"  ✓ JSON保存完了")
    except Exception as e:
        print(f"  ✗ 保存エラー: {e}")
        return

    # 4. 評価ログ出力
    print(f"\n[Phase 4] 評価ログ保存中...")
    try:
        log_files = save_evaluation_logs(result, log_dir=log_dir)
        print(f"  ✓ ログ保存完了:")
        print(f"    - サマリー: {log_files['summary']}")
        print(f"    - ルート評価詳細: {log_files['route_evaluations']}")
    except Exception as e:
        print(f"  ✗ ログ保存エラー: {e}")

    # 5. サマリー表示
    print("\n=== 軌跡推定の評価完了 (DEVモード) ===")
    print("\n📊 評価結果サマリー:")
    print(f"   - GT軌跡数: {result.overall_metrics.total_gt_count}")
    print(f"   - Est軌跡数: {num_est_loaded} (読み込み)")
    print(f"   - 評価対象: {result.overall_metrics.total_est_count} (完全ルート)")

    print(f"\n📈 精度指標:")
    print(f"   - MAE: {result.overall_metrics.mae:.3f}")
    print(f"   - RMSE: {result.overall_metrics.rmse:.3f}")
    print(f"   - 追跡率: {result.overall_metrics.tracking_rate:.1%}")
    print(f"   - 総絶対誤差: {result.overall_metrics.total_absolute_error}人")

    # ルート別の統計
    print(f"\n📋 ルート別統計:")
    print(f"   {'ルート':<8} {'GT':>4} {'Est':>4} {'誤差':>4}")
    print(f"   {'-'*8} {'-'*4} {'-'*4} {'-'*4}")
    sorted_evaluations = sorted(result.stay_evaluations, key=lambda x: x.detector_id)
    for se in sorted_evaluations:
        print(f"   {se.detector_id:<8} {se.gt_count:>4} {se.est_count:>4} {se.error:>4}")


if __name__ == "__main__":
    # python -m src2.evaluator.main_dev
    main_dev()

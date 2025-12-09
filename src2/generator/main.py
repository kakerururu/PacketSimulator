"""Generator メインエントリーポイント"""

from datetime import datetime
from .infrastructure.config_loader import (
    load_detectors,
    load_payloads,
    load_simulation_settings,
)
from .infrastructure.csv_writer import write_detector_logs
from .infrastructure.json_writer import write_ground_truth
from .usecase import simulation


def main():
    """メイン実行関数"""
    config_dir = "config"

    print("=== シミュレーションデータ生成開始 ===")

    # 設定ファイルを読み込み
    print("設定ファイルを読み込み中...")
    detectors = load_detectors()
    payload_definitions, model_names, model_probabilities = load_payloads()
    settings = load_simulation_settings(config_dir)

    # 設定情報を表示
    print(f"検出器数: {len(detectors)}")
    print(f"シミュレートする通行人数: {settings['num_walkers_to_simulate']}人")
    print(f"各検出器での検出数: {settings['payloads_per_detector_per_walker']}個")
    print(f"連続ペイロード数: {settings['num_consecutive_payloads']}個")
    print(f"通行人の移動速度: {settings['walker_speed']} m/s")
    print(
        f"滞在時間: {settings['stay_duration_min_seconds']}-{settings['stay_duration_max_seconds']}秒"
    )

    # シミュレーション実行
    print("\nシミュレーション実行中...")
    trajectories, detection_records = simulation.run_simulation(
        detectors=detectors,
        payload_definitions=payload_definitions,
        model_names=model_names,
        model_probabilities=model_probabilities,
        num_walkers=settings["num_walkers_to_simulate"],
        start_time=datetime(2024, 1, 14, 11, 0, 0),
    )

    print(f"生成された軌跡数: {len(trajectories)}")
    print(f"生成された検出レコード数: {len(detection_records)}")

    # Ground Truth JSONを出力
    print("\nGround Truth JSONを出力中...")
    write_ground_truth(trajectories)
    print("✓ Ground Truth JSON出力完了: src2_result/ground_truth/trajectories.json")

    # 検出ログCSVを出力
    print("\n検出ログCSVを出力中...")
    write_detector_logs(detection_records)
    print("✓ 検出ログCSV出力完了: src2_result/detector_logs/")

    print("\n=== シミュレーションデータ生成完了 ===")


if __name__ == "__main__":
    # python -m src2.generator.main
    main()

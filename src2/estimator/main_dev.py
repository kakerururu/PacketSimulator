"""Estimator DEVモード - デモデータ用エントリーポイント

デモデータ (src2_demo/detector_logs/) を使用して推定を実行する。
ありえない移動が含まれているデータで動作確認ができる。
"""

from .infrastructure.csv_reader import read_detector_logs
from .infrastructure.json_writer import write_estimated_trajectories
from .infrastructure.grouped_records_writer import export_grouped_records
from .infrastructure.clustering_writer import export_clustering_results
from .usecase.group_by_payload import group_records_by_payload
from .usecase.estimate_trajectories import estimate_trajectories
from ..generator.infrastructure.config_loader import load_detectors


def main_dev():
    """DEVモード実行関数（デモデータ用）"""
    print("=== 軌跡推定開始 (DEVモード) ===" )
    print("📁 使用データ: src2_demo/detector_logs/\n")

    # 0. 検出器設定を読み込み
    print("[Phase 0] 検出器設定を読み込み中...")
    detectors_list = load_detectors()
    detectors = {d.id: d for d in detectors_list}
    print(f"✓ 読み込んだ検出器数: {len(detectors)}")

    # 1. 検出ログCSVを読み込み（DEVモード: デモデータのパスを指定）
    print("\n[Phase 1] 検出ログCSVを読み込み中...")
    detection_records = read_detector_logs(detector_logs_dir="src2_demo/detector_logs")
    print(f"✓ 読み込んだレコード数: {len(detection_records)}")

    # 2. ペイロードごとにグループ化（類似ハッシュ値の統合）
    print("\n[Phase 2] ペイロードごとにグループ化中...")
    print("  - 類似ハッシュ値を統合（例: C_XX_base_hash + C_XX_sub_hash → C_XX_integrated）")
    grouped_records = group_records_by_payload(detection_records)
    print(f"✓ グループ化完了: {len(grouped_records)} 個のユニークなハッシュ値")

    # 各グループの詳細を表示
    print("\n  【グループ化の詳細】")
    for hash_id, records in grouped_records.items():
        print(f"    - {hash_id}: {len(records)} レコード")

    # 3. グループ化されたレコードをCSV出力（DEVモード専用ディレクトリ）
    print("\n[Phase 3] グループ化されたレコードをCSV出力中...")
    export_result = export_grouped_records(
        grouped_records,
        output_dir="src2_demo/grouped_records"
    )
    print(f"✓ 出力完了: {export_result['num_payloads']} ファイル")
    print(f"  出力先: src2_demo/grouped_records/")
    if export_result["index_file"]:
        print(f"  インデックス: {export_result['index_file']}")

    # 4. 軌跡推定（複数パスのクラスタリング）
    print("\n[Phase 4] 軌跡推定中...")
    print("  - is_judged=False のレコードに対して反復的にクラスタリング")
    print("  - 各パスで物理的に可能な移動を追跡")
    print("  - 使用したレコードを is_judged=True にマーク")
    print("  - 新規判定レコードが0になるまで継続（最大10パス）")
    print("  - 各パスの結果をCSV出力")
    estimated_trajectories, updated_grouped_records = estimate_trajectories(
        grouped_records=grouped_records,
        detectors=detectors,
        max_passes=10,
        output_per_pass=True,
        output_base_dir="src2_demo/clustering_results"
    )
    print(f"\n✓ 推定された軌跡数: {len(estimated_trajectories)}")

    # 推定された軌跡の詳細を表示
    print("\n  【推定された軌跡】")
    for traj in estimated_trajectories:
        num_records = sum(stay.num_detections for stay in traj.stays)
        print(f"    - {traj.trajectory_id}: 経路={traj.route}, レコード数={num_records}")

    # 5. 最終結果をCSV出力（DEVモード専用ディレクトリ）
    print("\n[Phase 5] 最終結果をCSV出力中...")
    estimation_result = export_clustering_results(
        updated_grouped_records,
        output_dir="src2_demo/clustering_results/final"
    )
    print(f"✓ 出力完了: {estimation_result['num_payloads']} ファイル")
    print(f"  出力先: src2_demo/clustering_results/final/")
    print(f"  使用済みレコード: {estimation_result['total_judged']}")
    print(f"  未使用レコード: {estimation_result['total_unjudged']}")

    # 6. 推定結果JSONを出力（DEVモード専用ディレクトリ）
    print("\n[Phase 6] 推定結果JSONを出力中...")
    write_estimated_trajectories(
        estimated_trajectories,
        output_file="src2_demo/estimated_trajectories.json",
        estimation_method="trajectory_estimation_dev"
    )
    print("✓ 推定結果JSON出力完了: src2_demo/estimated_trajectories.json")

    print("\n=== 軌跡推定完了 (DEVモード) ===")
    print("\n📊 推定結果:")
    print(f"   - 形成されたクラスタ（軌跡）数: {len(estimated_trajectories)}")
    print(f"   - 使用されたレコード: {estimation_result['total_judged']}")
    print(f"   - 未使用のレコード: {estimation_result['total_unjudged']}")

    if estimation_result['total_unjudged'] > 0:
        print("\n⚠️  未使用レコードが残っています")
        print("   → 複数パス後も到達可能な移動が見つからなかったレコードです")
        print("   → 詳細は src2_demo/clustering_results/final/ の Is_Judged=False を確認")


if __name__ == "__main__":
    # python -m src2.estimator.main_dev
    main_dev()

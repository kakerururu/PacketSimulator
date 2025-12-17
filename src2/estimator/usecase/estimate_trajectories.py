"""軌跡推定のメインロジック

複数パスのクラスタリングを実行し、検出レコードから軌跡を推定する。
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from pathlib import Path
from ..domain.detection_record import DetectionRecord
from ..domain.estimated_trajectory import EstimatedTrajectory
from ..domain.clustering_config import ClusteringConfig
from ..infrastructure.config_loader import (
    load_clustering_config,
    load_estimator_settings,
)
from .clustering import run_single_clustering_pass


def estimate_trajectories(
    grouped_records: Dict[str, List[DetectionRecord]],
    config: Optional[ClusteringConfig] = None,
    max_passes: Optional[int] = None,
    output_per_pass: bool = False,
    output_base_dir: Optional[str] = None,
) -> Tuple[List[EstimatedTrajectory], Dict[str, List[DetectionRecord]]]:
    """軌跡推定を実行（複数パスクラスタリング）

    is_judged=False のレコードに対して反復的にクラスタリングを行う。
    新規判定レコードが0になるか、最大パス数に達したら終了する。

    設定は config/simulation_settings.jsonc と config/estimator_settings.jsonc から
    自動的に読み込まれる。明示的に config を渡すことも可能。

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト
        config: クラスタリング設定（省略時は設定ファイルから読み込み）
        max_passes: 最大パス数（省略時は設定ファイルから読み込み）
        output_per_pass: 各パスの結果をCSV出力するか（デフォルトFalse）
        output_base_dir: 出力ディレクトリのベースパス（output_per_pass=Trueの場合に使用）

    Returns:
        (推定軌跡リスト, 更新されたグループ化レコード)

    終了条件:
        - 新規にTrue化されたレコードが0個の場合（これ以上進捗なし）
        - または最大パス数に達した場合（安全装置）
    """
    # 設定ファイルから読み込み（引数で指定されていない場合）
    if config is None:
        config = load_clustering_config()

    if max_passes is None:
        est_settings = load_estimator_settings()
        max_passes = est_settings.get("max_passes", 10)

    all_trajectories: List[EstimatedTrajectory] = []
    pass_num = 1
    cluster_counter_state = defaultdict(int)  # クラスタカウンターの状態をパス間で共有

    print(f"\n{'=' * 60}")
    print(f"複数パスクラスタリング開始（最大{max_passes}パス、新規判定0で終了）")
    print(f"{'=' * 60}\n")

    while pass_num <= max_passes:
        print(f"\n{'=' * 60}")
        print(f"パス {pass_num}/{max_passes} 開始")
        print(f"{'=' * 60}\n")

        # 現在の is_judged=True レコード数を計算
        judged_before = sum(
            1
            for records in grouped_records.values()
            for rec in records
            if rec.is_judged
        )

        # クラスタリング実行（単一スキャン）
        trajectories, grouped_records, cluster_counter_state = (
            run_single_clustering_pass(
                grouped_records=grouped_records,
                config=config,
                cluster_counter_state=cluster_counter_state,
            )
        )

        # パス後の is_judged=True レコード数を計算
        judged_after = sum(
            1
            for records in grouped_records.values()
            for rec in records
            if rec.is_judged
        )

        # 新規に判定されたレコード数
        newly_judged = judged_after - judged_before

        print(f"\n{'=' * 60}")
        print(f"パス {pass_num} 結果:")
        print(f"  - 新規クラスタ数: {len(trajectories)}")
        print(f"  - 新規判定レコード数: {newly_judged}")
        print(
            f"  - 累計判定レコード数: {judged_after}/{sum(len(records) for records in grouped_records.values())}"
        )
        print(f"{'=' * 60}\n")

        # 各パスの結果をCSV出力（オプション）
        if output_per_pass and output_base_dir:
            from ..infrastructure.clustering_writer import export_clustering_results

            pass_output_dir = str(Path(output_base_dir) / f"pass_{pass_num}")
            print(f"  パス {pass_num} の結果をCSV出力中...")
            pass_result = export_clustering_results(
                grouped_records, output_dir=pass_output_dir, clean_before=True
            )
            print(f"  ✓ 出力完了: {pass_output_dir}/")
            print(
                f"    - 使用済み: {pass_result['total_judged']}, 未使用: {pass_result['total_unjudged']}\n"
            )

        # 全軌跡リストに追加
        all_trajectories.extend(trajectories)

        # 終了条件チェック: 新規クラスタがない場合
        if newly_judged == 0:
            print(f"終了条件達成: 新規判定レコードなし（パス{pass_num}で終了）\n")
            break

        pass_num += 1

    # 最大パス数到達の場合
    if pass_num > max_passes:
        print(f"終了条件達成: 最大パス数{max_passes}に到達\n")

    # 最終統計
    total_records = sum(len(records) for records in grouped_records.values())
    total_judged = sum(
        1 for records in grouped_records.values() for rec in records if rec.is_judged
    )
    print(f"\n{'=' * 60}")
    print(f"複数パスクラスタリング完了")
    print(f"  - 総パス数: {pass_num if pass_num <= max_passes else max_passes}")
    print(f"  - 総クラスタ数: {len(all_trajectories)}")
    print(
        f"  - 総判定レコード数: {total_judged}/{total_records} ({total_judged / total_records * 100:.1f}%)"
    )
    print(f"  - 未判定レコード数: {total_records - total_judged}")
    print(f"{'=' * 60}\n")

    return all_trajectories, grouped_records

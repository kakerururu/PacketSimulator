"""軌跡推定のメインロジック

複数パスのクラスタリングを実行し、検出レコードから軌跡を推定する。
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from pathlib import Path
from ..domain.detection_record import DetectionRecord
from ..domain.estimated_trajectory import EstimatedTrajectory
from ...shared.domain.detector import Detector
from .clustering import cluster_records


def estimate_trajectories(
    grouped_records: Dict[str, List[DetectionRecord]],
    detectors: Dict[str, Detector],
    walker_speed: float = 1.4,
    impossible_factor: float = 0.8,
    allow_long_stays: bool = False,
    max_passes: int = 10,
    output_per_pass: bool = False,
    output_base_dir: Optional[str] = None,
) -> Tuple[List[EstimatedTrajectory], Dict[str, List[DetectionRecord]]]:
    """軌跡推定を実行（複数パスクラスタリング）

    is_judged=False のレコードに対して反復的にクラスタリングを行う。
    新規判定レコードが0になるか、最大パス数に達したら終了する。

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト
        detectors: 検出器の辞書 {detector_id: Detector}
        walker_speed: 歩行速度 (m/s)
        impossible_factor: ありえない移動判定の係数（デフォルト0.8）
        allow_long_stays: 長時間滞在を許可するか（デフォルトFalse）
        max_passes: 最大パス数（デフォルト10、安全装置）
        output_per_pass: 各パスの結果をCSV出力するか（デフォルトFalse）
        output_base_dir: 出力ディレクトリのベースパス（output_per_pass=Trueの場合に使用）

    Returns:
        (推定軌跡リスト, 更新されたグループ化レコード)

    終了条件:
        - 新規にTrue化されたレコードが0個の場合（これ以上進捗なし）
        - または最大パス数に達した場合（安全装置）

    Examples:
        >>> from datetime import datetime
        >>> from ...shared.domain.detector import Detector
        >>> detectors = {
        ...     "A": Detector(id="A", x=0.0, y=0.0),
        ...     "B": Detector(id="B", x=100.0, y=0.0)
        ... }
        >>> records = {
        ...     "hash_1": [
        ...         DetectionRecord(
        ...             timestamp=datetime(2024, 1, 14, 11, 0, 0),
        ...             walker_id="Walker_1",
        ...             hashed_id="hash_1",
        ...             detector_id="A",
        ...             sequence_number=100,
        ...             is_judged=False
        ...         )
        ...     ]
        ... }
        >>> trajectories, updated_records = estimate_trajectories(records, detectors)
    """
    all_trajectories: List[EstimatedTrajectory] = []
    pass_num = 1
    cluster_counter_state = defaultdict(int)  # クラスタカウンターの状態をパス間で共有

    print(f"\n{'='*60}")
    print(f"複数パスクラスタリング開始（最大{max_passes}パス、新規判定0で終了）")
    print(f"{'='*60}\n")

    while pass_num <= max_passes:
        print(f"\n{'='*60}")
        print(f"パス {pass_num}/{max_passes} 開始")
        print(f"{'='*60}\n")

        # 現在の is_judged=True レコード数を計算
        judged_before = sum(
            1 for records in grouped_records.values() for rec in records if rec.is_judged
        )

        # クラスタリング実行（単一スキャン）
        trajectories, grouped_records, cluster_counter_state = cluster_records(
            grouped_records=grouped_records,
            detectors=detectors,
            walker_speed=walker_speed,
            impossible_factor=impossible_factor,
            allow_long_stays=allow_long_stays,
            cluster_counter_state=cluster_counter_state,
        )

        # パス後の is_judged=True レコード数を計算
        judged_after = sum(
            1 for records in grouped_records.values() for rec in records if rec.is_judged
        )

        # 新規に判定されたレコード数
        newly_judged = judged_after - judged_before

        print(f"\n{'='*60}")
        print(f"パス {pass_num} 結果:")
        print(f"  - 新規クラスタ数: {len(trajectories)}")
        print(f"  - 新規判定レコード数: {newly_judged}")
        print(f"  - 累計判定レコード数: {judged_after}/{sum(len(records) for records in grouped_records.values())}")
        print(f"{'='*60}\n")

        # 各パスの結果をCSV出力（オプション）
        if output_per_pass and output_base_dir:
            from ..infrastructure.clustering_writer import export_clustering_results

            pass_output_dir = str(Path(output_base_dir) / f"pass_{pass_num}")
            print(f"  パス {pass_num} の結果をCSV出力中...")
            pass_result = export_clustering_results(
                grouped_records,
                output_dir=pass_output_dir,
                clean_before=True
            )
            print(f"  ✓ 出力完了: {pass_output_dir}/")
            print(f"    - 使用済み: {pass_result['total_judged']}, 未使用: {pass_result['total_unjudged']}\n")

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
    print(f"\n{'='*60}")
    print(f"複数パスクラスタリング完了")
    print(f"  - 総パス数: {pass_num if pass_num <= max_passes else max_passes}")
    print(f"  - 総クラスタ数: {len(all_trajectories)}")
    print(f"  - 総判定レコード数: {total_judged}/{total_records} ({total_judged/total_records*100:.1f}%)")
    print(f"  - 未判定レコード数: {total_records - total_judged}")
    print(f"{'='*60}\n")

    return all_trajectories, grouped_records

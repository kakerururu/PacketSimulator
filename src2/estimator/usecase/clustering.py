"""レコードのクラスタリング

=============================================================================
【アルゴリズム概要】
=============================================================================

このモジュールは、同一ハッシュ値を持つ複数のパケット検知レコードを
「物理的制約」に基づいて個々人の移動経路に分離する。

【核心的アイデア】
人間は瞬間移動できない。したがって、2つの検出器間の「最小移動時間」より
短い時間で移動したレコードは「別人のもの」と判断できる。

【主要パラメータ】
- walker_speed: 歩行速度（デフォルト 1.4 m/s）
- impossible_factor: ありえない移動判定係数（デフォルト 0.8）
  → 最小移動時間の80%未満で到着 = ありえない

【アルゴリズムフロー】

  レコードを時系列順に走査
         │
         ▼
  ┌────────────────────┐
  │ 候補レコードを評価  │ → _evaluate_candidate_record()
  └────────────────────┘
         │
    ┌────┴────┐
    │同じ検出器？│
    └────┬────┘
         │
    YES─┴─NO
    │     │
    ▼     ▼
  ┌─────┐  ┌──────────────┐
  │滞在判定│  │移動可能性判定  │
  └─────┘  └──────────────┘
    │         │
    │    ┌────┴────┐
    │    │ありえない？│
    │    └────┬────┘
    │         │
    │    YES─┴─NO
    │     │     │
    │     ▼     ▼
    │  ┌────────┐ ┌──────────┐
    │  │前方探索 │ │クラスタ追加│
    │  └────────┘ └──────────┘
    │     │         → _forward_search()
    ▼     ▼
  ┌────────────────────────────┐
  │ 到達可能なレコードを発見？   │
  └────────────────────────────┘
         │
    YES─┴─NO
    │     │
    ▼     ▼
  継続   クラスタ終了

【前方探索とは】
ありえない移動を検出した場合、現在のレコードをスキップして
先のレコードの中から「到達可能」なものを探す処理。

【複数パス処理】
1回のクラスタリングでは各ハッシュグループから1つのクラスタのみ抽出。
is_judged=False のレコードが残っている限り、複数回呼び出して
すべてのレコードをクラスタ化する。

=============================================================================
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# ドメインオブジェクト
from ..domain.detection_record import DetectionRecord
from ..domain.estimated_stay import EstimatedStay
from ..domain.estimated_trajectory import EstimatedTrajectory
from ..domain.cluster_state import ClusterState
from ..domain.clustering_config import ClusteringConfig
from ..domain.record_action import RecordAction, ForwardSearchAction

# 共有ユーティリティ
from ...shared.domain.detector import Detector
from ...shared.utils.distance_calculator import calculate_min_travel_time

# クラスタリング用ユーティリティ（純粋関数群）
from .clustering_utils import (
    MAX_STAY_DURATION,
    is_sequence_anomaly,
    is_impossible_movement,
    is_valid_stay_duration,
)


# =============================================================================
# レコード評価関数
# =============================================================================


def _evaluate_candidate_record(
    state: ClusterState,
    candidate: DetectionRecord,
    config: ClusteringConfig,
) -> Tuple[RecordAction, bool]:
    """候補レコードを評価してアクションを決定

    メインループで次の候補レコードを評価し、取るべきアクションを返す。

    Args:
        state: 現在のクラスタ状態
        candidate: 評価対象の候補レコード
        config: クラスタリング設定

    Returns:
        (RecordAction, add_to_route)
        - RecordAction: 取るべきアクション
        - add_to_route: クラスタ追加時に経路にも追加するか
    """
    prev_record = state.prev_record
    prev_det_id = prev_record.detector_id
    cand_det_id = candidate.detector_id
    current_detector = state.route_sequence[-1] if state.route_sequence else None

    # === 同じ検出器での滞在判定 ===
    if cand_det_id == current_detector:
        if config.allow_long_stays:
            return RecordAction.ADD_TO_CLUSTER, False

        stay_time_diff = (candidate.timestamp - prev_record.timestamp).total_seconds()
        if is_valid_stay_duration(stay_time_diff):
            return RecordAction.ADD_TO_CLUSTER, False
        else:
            print(
                f"[{state.cluster_id}] 滞在時間超過検出: "
                f"{cand_det_id}での滞在時間={stay_time_diff:.1f}s > 最大={MAX_STAY_DURATION:.1f}s "
                f"→ 前方探索開始"
            )
            return RecordAction.FORWARD_SEARCH, False

    # === 異なる検出器への移動判定 ===
    time_diff = (candidate.timestamp - prev_record.timestamp).total_seconds()
    det_prev = config.detectors[prev_det_id]
    det_cand = config.detectors[cand_det_id]
    min_travel_time = calculate_min_travel_time(det_prev, det_cand, config.walker_speed)

    # シーケンス番号異常チェック（ログ出力のみ）
    if is_sequence_anomaly(
        prev_record, candidate, time_diff, min_travel_time, config.impossible_factor
    ):
        seq_diff = abs(candidate.sequence_number - prev_record.sequence_number)
        print(
            f"[{state.cluster_id}] シーケンス番号異常検出: "
            f"{prev_det_id}→{cand_det_id} "
            f"(seq差={seq_diff} > 64, 時間差={time_diff:.1f}s < 必要時間={min_travel_time:.1f}s) "
            f"→ 前方探索"
        )

    # ありえない移動チェック
    if is_impossible_movement(time_diff, min_travel_time, config.impossible_factor):
        print(
            f"[{state.cluster_id}] ありえない移動検出: "
            f"{prev_det_id}→{cand_det_id} "
            f"(時間差: {time_diff:.1f}s < 必要時間: {min_travel_time:.1f}s)"
        )
        return RecordAction.FORWARD_SEARCH, False

    return RecordAction.ADD_TO_CLUSTER, True


def _evaluate_scan_record(
    state: ClusterState,
    scan_record: DetectionRecord,
    config: ClusteringConfig,
) -> ForwardSearchAction:
    """前方探索中のレコードを評価

    Args:
        state: 現在のクラスタ状態
        scan_record: 評価対象のレコード
        config: クラスタリング設定

    Returns:
        ForwardSearchAction: 取るべきアクション
    """
    if scan_record.is_judged:
        return ForwardSearchAction.SKIP

    prev_record = state.prev_record
    prev_det_id = prev_record.detector_id
    current_detector = state.route_sequence[-1] if state.route_sequence else None

    # === 同じ検出器での滞在継続判定 ===
    if scan_record.detector_id == current_detector:
        if config.allow_long_stays:
            return ForwardSearchAction.ADD_AND_CONTINUE

        stay_time_diff = (
            scan_record.timestamp - prev_record.timestamp
        ).total_seconds()
        if is_valid_stay_duration(stay_time_diff):
            return ForwardSearchAction.ADD_AND_CONTINUE
        return ForwardSearchAction.SKIP

    # === ループ回避 ===
    if scan_record.detector_id in state.route_sequence:
        return ForwardSearchAction.SKIP

    # === 到達可能性を判定 ===
    scan_time_diff = (scan_record.timestamp - prev_record.timestamp).total_seconds()
    det_prev = config.detectors[prev_det_id]
    det_scan = config.detectors[scan_record.detector_id]
    min_t_scan = calculate_min_travel_time(det_prev, det_scan, config.walker_speed)

    # シーケンス番号異常はスキップ（前方探索では実際に判定に使用）
    if is_sequence_anomaly(
        prev_record, scan_record, scan_time_diff, min_t_scan, config.impossible_factor
    ):
        return ForwardSearchAction.SKIP

    if is_impossible_movement(scan_time_diff, min_t_scan, config.impossible_factor):
        return ForwardSearchAction.SKIP

    return ForwardSearchAction.FOUND


# =============================================================================
# 前方探索
# =============================================================================


def _forward_search(
    state: ClusterState,
    records: List[DetectionRecord],
    start_idx: int,
    config: ClusteringConfig,
) -> Optional[int]:
    """前方探索: 到達可能なレコードを探す

    Args:
        state: 現在のクラスタ状態
        records: レコードリスト
        start_idx: 探索開始インデックス
        config: クラスタリング設定

    Returns:
        到達可能なレコードのインデックス、見つからなければ None
    """
    scan_idx = start_idx

    while scan_idx < len(records):
        scan_record = records[scan_idx]
        action = _evaluate_scan_record(state, scan_record, config)

        if action == ForwardSearchAction.SKIP:
            scan_idx += 1
            continue

        if action == ForwardSearchAction.ADD_AND_CONTINUE:
            state.add_record(scan_record, add_to_route=False)
            scan_idx += 1
            continue

        if action == ForwardSearchAction.FOUND:
            print(
                f"[{state.cluster_id}] 到達可能レコード発見: "
                f"{state.prev_record.detector_id}→{scan_record.detector_id} "
                f"(idx {start_idx}→{scan_idx}までスキップ)"
            )
            return scan_idx

        scan_idx += 1

    print(f"[{state.cluster_id}] 到達可能レコードなし、クラスタ終了")
    return None


# =============================================================================
# 1つのハッシュグループをクラスタリング
# =============================================================================


def _cluster_one_group(
    records: List[DetectionRecord],
    cluster_id: str,
    config: ClusteringConfig,
) -> Optional[Tuple[List[DetectionRecord], List[str]]]:
    """1つのハッシュグループから1つのクラスタを抽出

    Args:
        records: レコードリスト（時系列順）
        cluster_id: 作成するクラスタのID
        config: クラスタリング設定

    Returns:
        (cluster_records, route_sequence) または None
    """
    # 最初の未使用レコードを探す
    start_idx = 0
    while start_idx < len(records) and records[start_idx].is_judged:
        start_idx += 1

    if start_idx >= len(records):
        return None

    # クラスタ状態を初期化
    first_record = records[start_idx]
    state = ClusterState(
        cluster_id=cluster_id,
        cluster_records=[],
        route_sequence=[],
        prev_record=first_record,
    )
    state.add_record(first_record, add_to_route=True)

    # メインループ
    idx = start_idx + 1
    while idx < len(records):
        candidate = records[idx]

        if candidate.is_judged:
            idx += 1
            continue

        action, add_to_route = _evaluate_candidate_record(state, candidate, config)

        if action == RecordAction.ADD_TO_CLUSTER:
            state.add_record(candidate, add_to_route=add_to_route)
            idx += 1

        elif action == RecordAction.FORWARD_SEARCH:
            found_idx = _forward_search(state, records, idx, config)
            if found_idx is not None:
                found_record = records[found_idx]
                state.add_record(found_record, add_to_route=True)
                idx = found_idx + 1
            else:
                break

        elif action == RecordAction.SKIP:
            idx += 1

    return state.cluster_records, state.route_sequence


# =============================================================================
# メイン関数
# =============================================================================


def cluster_records(
    grouped_records: Dict[str, List[DetectionRecord]],
    detectors: Dict[str, Detector],
    walker_speed: float = 1.4,
    impossible_factor: float = 0.8,
    allow_long_stays: bool = False,
    cluster_counter_state: Optional[Dict[str, int]] = None,
) -> Tuple[List[EstimatedTrajectory], Dict[str, List[DetectionRecord]], Dict[str, int]]:
    """レコードをクラスタリングして軌跡を形成

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト
        detectors: 検出器の辞書 {detector_id: Detector}
        walker_speed: 歩行速度 (m/s)
        impossible_factor: ありえない移動判定の係数
        allow_long_stays: 長時間滞在を許可するか
        cluster_counter_state: クラスタカウンターの状態

    Returns:
        (推定軌跡リスト, 更新されたグループ化レコード, 更新されたクラスタカウンター)
    """
    config = ClusteringConfig(
        detectors=detectors,
        walker_speed=walker_speed,
        impossible_factor=impossible_factor,
        allow_long_stays=allow_long_stays,
    )

    estimated_trajectories: List[EstimatedTrajectory] = []

    if cluster_counter_state is None:
        cluster_counter = defaultdict(int)
    else:
        cluster_counter = (
            cluster_counter_state
            if isinstance(cluster_counter_state, defaultdict)
            else defaultdict(int, cluster_counter_state)
        )

    for integrated_hash, records in grouped_records.items():
        if not records:
            continue

        cluster_counter[integrated_hash] += 1
        cluster_id = f"{integrated_hash}_cluster{cluster_counter[integrated_hash]}"

        result = _cluster_one_group(records, cluster_id, config)
        if result is None:
            continue

        cluster_recs, route_sequence = result

        if len(route_sequence) >= 2:
            stays = _create_estimated_stays(cluster_recs, detectors)

            trajectory = EstimatedTrajectory(
                trajectory_id=f"est_traj_{len(estimated_trajectories) + 1}",
                cluster_ids=[cluster_id],
                route="".join(route_sequence),
                stays=stays,
            )
            estimated_trajectories.append(trajectory)

            print(
                f"[{cluster_id}] クラスタ形成: "
                f"経路={''.join(route_sequence)}, "
                f"レコード数={len(cluster_recs)}"
            )

    return estimated_trajectories, grouped_records, cluster_counter


# =============================================================================
# ユーティリティ関数
# =============================================================================


def _create_estimated_stays(
    cluster_records: List[DetectionRecord],
    detectors: Dict[str, Detector],
) -> List[EstimatedStay]:
    """クラスタのレコードからEstimatedStayリストを作成"""
    records_by_detector: Dict[str, List[DetectionRecord]] = defaultdict(list)
    for rec in cluster_records:
        records_by_detector[rec.detector_id].append(rec)

    detector_order = sorted(
        records_by_detector.keys(),
        key=lambda d: min(r.timestamp for r in records_by_detector[d]),
    )

    stays: List[EstimatedStay] = []
    for detector_id in detector_order:
        det_records = sorted(
            records_by_detector[detector_id], key=lambda r: r.timestamp
        )
        first_detection = det_records[0].timestamp
        last_detection = det_records[-1].timestamp
        duration = (last_detection - first_detection).total_seconds()

        stays.append(
            EstimatedStay(
                detector_id=detector_id,
                first_detection=first_detection,
                last_detection=last_detection,
                estimated_duration_seconds=duration,
                num_detections=len(det_records),
            )
        )

    return stays

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from ..domain.detection_record import DetectionRecord
from ..domain.estimated_stay import EstimatedStay
from ..domain.estimated_trajectory import EstimatedTrajectory
from ..domain.cluster_state import ClusterState
from ..domain.clustering_config import ClusteringConfig
from ..domain.record_action import RecordAction, ForwardSearchAction
from ...shared.domain.detector import Detector
from ...shared.utils.distance_calculator import calculate_min_travel_time
from .clustering_utils import (
    MAX_STAY_DURATION,
    is_sequence_anomaly,
)


def _judge_candidate_record(
    state: ClusterState,
    candidate_record: DetectionRecord,
    config: ClusteringConfig,
) -> RecordAction:
    """候補レコードを判定してアクションを決定

    メインループで次の候補レコードを判定し、取るべきアクションを返す。

    【判定条件】

    1. 同じ検出器での滞在:
       - allow_long_stays=True → 無条件で追加 (ADD_AS_STAY)
       - allow_long_stays=False → 滞在時間 <= 900秒なら追加 (ADD_AS_STAY)、超過なら前方探索

    2. 異なる検出器への移動:
       - 時間差 >= 最小移動時間 × 0.8 → 追加 (ADD_AS_MOVE)（到達可能）
       - 時間差 < 最小移動時間 × 0.8 → 前方探索（ありえない移動）

    Args:
        state: 現在のクラスタ状態
        candidate_record: 評価対象の候補レコード
        config: クラスタリング設定

    Returns:
        RecordAction: 取るべきアクション
        - ADD_AS_STAY: 同じ検出器での滞在継続（cluster_recordsにレコードを追加、推定経路には追加しない）
        - ADD_AS_MOVE: 新しい検出器への移動（cluster_recordsにレコードを追加、推定経路にも検出器IDを追加）
        - FORWARD_SEARCH: 前方探索を開始
    """
    prev_record = state.prev_record
    prev_det_id = prev_record.detector_id
    cand_det_id = candidate_record.detector_id
    current_detector = state.route_sequence[-1] if state.route_sequence else None

    # =========================================================================
    # 同じ検出器での滞在判定
    # =========================================================================
    if cand_det_id == current_detector:
        if config.allow_long_stays:  # 長時間滞在を許可
            return RecordAction.ADD_AS_STAY

        stay_time = (candidate_record.timestamp - prev_record.timestamp).total_seconds()
        if stay_time <= MAX_STAY_DURATION:
            return RecordAction.ADD_AS_STAY  # 滞在時間内
        else:
            print(
                f"[{state.cluster_id}] 滞在時間超過検出: "
                f"{cand_det_id}での滞在時間={stay_time:.1f}s > 最大={MAX_STAY_DURATION:.1f}s "
                f"→ 前方探索開始"
            )
            return RecordAction.FORWARD_SEARCH  # 滞在時間超過しているので前方探索

    # =========================================================================
    # 異なる検出器への移動判定
    # =========================================================================
    else:
        move_time = (candidate_record.timestamp - prev_record.timestamp).total_seconds()
        min_travel_time = calculate_min_travel_time(
            config.detectors[prev_det_id],  # 検知器のIDを指定してその検知器の情報を取得
            config.detectors[cand_det_id],
            config.walker_speed,
        )

        # ありえない移動かの判定。impossible_factorによって誤差を考慮
        if move_time < min_travel_time * config.impossible_factor:
            print(
                f"[{state.cluster_id}] ありえない移動検出: "
                f"{prev_det_id}→{cand_det_id} "
                f"(移動時間={move_time:.1f}s < 最小移動時間{min_travel_time:.1f}s×{config.impossible_factor}"
            )
            return RecordAction.FORWARD_SEARCH
        else:
            # 正常な移動 → cluster_recordsにレコードを追加、推定経路にも検出器IDを追加
            return RecordAction.ADD_AS_MOVE


def _evaluate_scan_record(
    state: ClusterState,
    scan_record: DetectionRecord,
    config: ClusteringConfig,
) -> ForwardSearchAction:
    """前方探索中のレコードを評価

    前方探索で各レコードを評価し、取るべきアクションを返す。

    【処理フロー】

        スキャン対象レコード
              │
              ▼
         ┌─────────┐
         │使用済み？│
         └─────────┘
              │
         YES─┴─NO
          │     │
          ▼     ▼
        SKIP   続行
                │
                ▼
         ┌───────────┐
         │同じ検出器？│
         └───────────┘
              │
         YES─┴─NO
          │     │
          ▼     ▼
        滞在判定  移動判定
          │       │
          ▼       ▼
        ADD_    FOUND
        CONTINUE  or SKIP

    【メインループとの違い】
    - シーケンス番号異常: 前方探索では実際にスキップ判定に使用
    - ループ回避: 既に推定経路に含まれる検出器はスキップ

    【各アクションの意味】
    - SKIP: このレコードをスキップして次へ
    - ADD_AND_CONTINUE: cluster_recordsにレコードを追加して探索継続（まだ次の検出器未発見）
    - FOUND: 到達可能なレコード発見！探索終了

    Args:
        state: 現在のクラスタ状態
        scan_record: 評価対象のレコード
        config: クラスタリング設定

    Returns:
        ForwardSearchAction: 取るべきアクション
    """
    # =========================================================================
    # 使用済みチェック
    # =========================================================================
    if scan_record.is_judged:
        return ForwardSearchAction.SKIP

    prev_record = state.prev_record
    prev_det_id = prev_record.detector_id
    current_detector = state.route_sequence[-1] if state.route_sequence else None

    # =========================================================================
    # 同じ検出器での滞在継続判定
    # =========================================================================
    # 同じ検出器のレコードは「滞在の継続」として扱う。
    # cluster_recordsにレコードを追加しつつ、次の検出器を探し続ける。
    if scan_record.detector_id == current_detector:
        if config.allow_long_stays:
            return ForwardSearchAction.ADD_AND_CONTINUE

        stay_time_diff = (scan_record.timestamp - prev_record.timestamp).total_seconds()
        if stay_time_diff <= MAX_STAY_DURATION:
            return ForwardSearchAction.ADD_AND_CONTINUE  # 滞在時間内
        return ForwardSearchAction.SKIP  # 滞在時間超過

    # =========================================================================
    # ループ回避
    # =========================================================================
    # 既に推定経路に含まれている検出器は、ループを避けるためスキップ。
    # 例: 推定経路が A→B→C の場合、A や B には戻らない
    if scan_record.detector_id in state.route_sequence:
        return ForwardSearchAction.SKIP

    # =========================================================================
    # 到達可能性を判定
    # =========================================================================
    scan_time_diff = (scan_record.timestamp - prev_record.timestamp).total_seconds()
    det_prev = config.detectors[prev_det_id]
    det_scan = config.detectors[scan_record.detector_id]
    min_t_scan = calculate_min_travel_time(det_prev, det_scan, config.walker_speed)

    # シーケンス番号異常チェック
    # 【重要】前方探索では実際にスキップ判定に使用（メインループとの違い）
    if is_sequence_anomaly(
        prev_record, scan_record, scan_time_diff, min_t_scan, config.impossible_factor
    ):
        return ForwardSearchAction.SKIP

    # ありえない移動チェック
    if scan_time_diff < min_t_scan * config.impossible_factor:
        return ForwardSearchAction.SKIP

    # 到達可能なレコード発見！
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

    「ありえない移動」または「滞在時間超過」を検出した場合に呼び出される。
    先のレコードを順にスキャンし、到達可能なレコードを探す。

    【処理の流れ】

    例: 現在位置が検出器A（idx=5）で、ありえない移動を検出した場合

      idx  検出器  評価結果
      ───────────────────────
       5    B     ← ありえない移動を検出（この関数が呼ばれる）
       6    B     SKIP（まだありえない）
       7    A     ADD_AND_CONTINUE（滞在継続、cluster_recordsにレコードを追加）
       8    C     SKIP（ループ：推定経路に含まれる場合）
       9    D     FOUND！（到達可能）← このインデックスを返す

    【同じ検出器のレコードについて】
    前方探索中に同じ検出器のレコードを見つけた場合は、
    「滞在の継続」としてcluster_recordsにレコードを追加しつつ探索を継続する。
    これにより、prev_record が更新され、後続の到達可能性判定が正確になる。

    Args:
        state: 現在のクラスタ状態（探索中に更新される）
        records: レコードリスト
        start_idx: 探索開始インデックス
        config: クラスタリング設定

    Returns:
        到達可能なレコードのインデックス、見つからなければ None
    """
    scan_idx = start_idx

    while scan_idx < len(records):
        scan_record = records[scan_idx]

        # レコードを評価
        action = _evaluate_scan_record(state, scan_record, config)

        if action == ForwardSearchAction.SKIP:
            # このレコードをスキップして次へ
            scan_idx += 1
            continue

        if action == ForwardSearchAction.ADD_AND_CONTINUE:
            # 同じ検出器での滞在継続
            # → cluster_recordsにレコードを追加して、次の検出器を探し続ける
            state.add_record(scan_record, add_to_route=False)
            scan_idx += 1
            continue

        if action == ForwardSearchAction.FOUND:
            # 到達可能なレコード発見！
            print(
                f"[{state.cluster_id}] 到達可能レコード発見: "
                f"{state.prev_record.detector_id}→{scan_record.detector_id} "
                f"(idx {start_idx}→{scan_idx}までスキップ)"
            )
            return scan_idx

        scan_idx += 1

    # リストの最後まで探索したが、到達可能なレコードが見つからなかった
    # → このクラスタは終了
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

    レコードリストを時系列順に走査し、物理的に可能な移動を追跡して
    1つのクラスタ（= 1人分の推定経路）を構築する。

    【処理の流れ】

    1. 最初の未使用レコードを探す
    2. ClusterState を初期化
    3. メインループ:
       - 候補レコードを判定 (_judge_candidate_record)
       - ADD_AS_STAY → cluster_recordsにレコードを追加（推定経路には追加しない）
       - ADD_AS_MOVE → cluster_recordsにレコードを追加、推定経路にも検出器IDを追加
       - FORWARD_SEARCH → 前方探索で到達可能なレコードを探す
    4. cluster_recordsと推定経路を返す

    【重要】
    この関数は1つのクラスタのみを抽出する。
    同じハッシュグループに複数人のレコードが混在している場合、
    残りのレコードは次のパスで処理される。

    Args:
        records: レコードリスト（時系列順）
        cluster_id: 作成するクラスタのID
        config: クラスタリング設定

    Returns:
        (cluster_records, route_sequence) または None（未使用レコードがない場合）
    """
    # =========================================================================
    # 最初の未使用レコードを探す
    # =========================================================================
    start_idx = 0
    while start_idx < len(records) and records[start_idx].is_judged:
        start_idx += 1

    if start_idx >= len(records):
        # 全てのレコードが使用済み
        return None

    # =========================================================================
    # クラスタ状態を初期化
    # =========================================================================
    first_record = records[start_idx]
    state = ClusterState(
        cluster_id=cluster_id,
        cluster_records=[],
        route_sequence=[],
        prev_record=first_record,
    )
    # 最初のレコードを追加（推定経路にも検出器IDを追加）
    state.add_record(first_record, add_to_route=True)

    # =========================================================================
    # メインループ: レコードを順に評価
    # =========================================================================
    idx = start_idx + 1
    while idx < len(records):
        candidate = records[idx]

        # 使用済みはスキップ
        if candidate.is_judged:
            idx += 1
            continue

        # 候補レコードを判定
        action = _judge_candidate_record(state, candidate, config)

        if action == RecordAction.ADD_AS_STAY:
            # 滞在継続: cluster_recordsにレコードを追加（推定経路には追加しない）
            state.add_record(candidate, add_to_route=False)
            idx += 1

        elif action == RecordAction.ADD_AS_MOVE:
            # 移動: cluster_recordsにレコードを追加、推定経路にも検出器IDを追加
            state.add_record(candidate, add_to_route=True)
            idx += 1

        elif action == RecordAction.FORWARD_SEARCH:
            # 前方探索を実行
            found_idx = _forward_search(state, records, idx, config)
            if found_idx is not None:
                # 到達可能なレコードを採用（新検出器への移動なので推定経路にも追加）
                found_record = records[found_idx]
                state.add_record(found_record, add_to_route=True)
                idx = found_idx + 1
            else:
                # 到達可能なレコードなし → クラスタ終了
                break

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

    各ハッシュ値のレコード列を時系列順に読み、物理的に可能な移動を追跡して
    クラスタを形成する。使用したレコードは is_judged=True にマークする。

    【単一パス処理】
    この関数は1回のスキャンのみを実行する。
    各ハッシュグループから1つのクラスタのみを抽出する。

    【複数パス処理の必要性】
    同じハッシュ値を持つ複数人のレコードが混在している場合、
    1回の呼び出しでは全てを分離できない。
    is_judged=False のレコードが残っている限り、複数回呼び出すことで
    反復的にクラスタリングを行う。

    【呼び出し例】
    ```python
    cluster_counter = None
    for pass_num in range(max_passes):
        trajectories, records, cluster_counter = cluster_records(
            records, detectors, cluster_counter_state=cluster_counter
        )
        if not trajectories:
            break  # 新しいクラスタが作れなくなったら終了
    ```

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト
        detectors: 検出器の辞書 {detector_id: Detector}
        walker_speed: 歩行速度 (m/s)、デフォルト 1.4
        impossible_factor: ありえない移動判定の係数、デフォルト 0.8
        allow_long_stays: 長時間滞在を許可するか、デフォルト False
        cluster_counter_state: クラスタカウンターの状態（パス間で永続化）

    Returns:
        (推定軌跡リスト, 更新されたグループ化レコード, 更新されたクラスタカウンター)
    """
    # 設定をまとめる
    config = ClusteringConfig(
        detectors=detectors,
        walker_speed=walker_speed,
        impossible_factor=impossible_factor,
        allow_long_stays=allow_long_stays,
    )

    estimated_trajectories: List[EstimatedTrajectory] = []

    # クラスタカウンターの初期化（パス間で永続化）
    if cluster_counter_state is None:
        cluster_counter = defaultdict(int)
    else:
        cluster_counter = (
            cluster_counter_state
            if isinstance(cluster_counter_state, defaultdict)
            else defaultdict(int, cluster_counter_state)
        )

    # =========================================================================
    # ハッシュ値ごとに処理
    # =========================================================================
    for integrated_hash, records in grouped_records.items():
        if not records:
            continue

        # クラスタIDを生成（例: "C_01_integrated_cluster1"）
        cluster_counter[integrated_hash] += 1
        cluster_id = f"{integrated_hash}_cluster{cluster_counter[integrated_hash]}"

        # 1つのクラスタを抽出
        result = _cluster_one_group(records, cluster_id, config)
        if result is None:
            continue

        cluster_recs, route_sequence = result

        # クラスタが有効なら（2つ以上の検出器を訪問）、軌跡として保存
        # 1つの検出器のみの場合は「移動」とみなさない
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
                f"推定経路={''.join(route_sequence)}, "
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
    """クラスタのレコードからEstimatedStayリストを作成

    クラスタに属するレコードを検出器ごとにグループ化し、
    各検出器での滞在情報を算出する。

    【処理の流れ】
    1. レコードを検出器IDでグループ化
    2. 各検出器の最初の検出時刻でソート
    3. 各検出器について EstimatedStay を作成

    Args:
        cluster_records: クラスタのレコードリスト
        detectors: 検出器の辞書

    Returns:
        EstimatedStayのリスト（検出順）
    """
    # 検出器ごとにグループ化
    records_by_detector: Dict[str, List[DetectionRecord]] = defaultdict(list)
    for rec in cluster_records:
        records_by_detector[rec.detector_id].append(rec)

    # 検出順にソート（各検出器の最初の検出時刻順）
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

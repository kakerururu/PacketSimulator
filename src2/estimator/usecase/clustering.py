"""レコードのクラスタリング

統合されたハッシュ値ごとのレコード列を上から下まで読み、
物理的に可能な移動を追跡してクラスタを形成する。

このモジュールは単一パスのクラスタリングロジックを提供する。
複数パスで呼び出されることを想定している。
"""

from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from ..domain.detection_record import DetectionRecord
from ..domain.estimated_stay import EstimatedStay
from ..domain.estimated_trajectory import EstimatedTrajectory
from ...shared.domain.detector import Detector
from ...shared.utils.distance_calculator import calculate_min_travel_time


def cluster_records(
    grouped_records: Dict[str, List[DetectionRecord]],
    detectors: Dict[str, Detector],
    walker_speed: float = 1.4,
    impossible_factor: float = 0.8,
    allow_long_stays: bool = False,
    cluster_counter_state: Optional[Dict[str, int]] = None,
) -> Tuple[List[EstimatedTrajectory], Dict[str, List[DetectionRecord]], Dict[str, int]]:
    """レコードをクラスタリングして軌跡を形成

    各ハッシュ値のレコード列を上から下まで読み、
    物理的に可能な移動を追跡してクラスタを形成する。
    使用したレコードは is_judged=True にマークする。

    この関数は1回のスキャンのみを実行する。
    複数回呼び出すことで、is_judged=False のレコードに対して
    反復的にクラスタリングを行うことができる。

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト
        detectors: 検出器の辞書 {detector_id: Detector}
        walker_speed: 歩行速度 (m/s)
        impossible_factor: ありえない移動判定の係数（デフォルト0.8）
        allow_long_stays: 長時間滞在を許可するか（デフォルトFalse）
        cluster_counter_state: クラスタカウンターの状態（パス間で永続化）

    Returns:
        (推定軌跡リスト, 更新されたグループ化レコード, 更新されたクラスタカウンター)

    Examples:
        >>> from datetime import datetime
        >>> from ...shared.domain.detector import Detector
        >>> detectors = {
        ...     "A": Detector(id="A", x=0.0, y=0.0),
        ...     "B": Detector(id="B", x=100.0, y=0.0)
        ... }
        >>> records = {
        ...     "C_01_integrated": [
        ...         DetectionRecord(
        ...             timestamp=datetime(2024, 1, 14, 11, 0, 0),
        ...             walker_id="Walker_1",
        ...             hashed_id="C_01_base_hash",
        ...             detector_id="A",
        ...             sequence_number=100,
        ...             is_judged=False
        ...         )
        ...     ]
        ... }
        >>> trajectories, updated_records, counter_state = cluster_records(records, detectors)
    """
    estimated_trajectories: List[EstimatedTrajectory] = []

    # クラスタカウンターの初期化（パス間で永続化）
    if cluster_counter_state is None:
        cluster_counter = defaultdict(int)
    else:
        # 既存の状態を引き継ぐ（defaultdictとして扱う）
        if isinstance(cluster_counter_state, defaultdict):
            cluster_counter = cluster_counter_state
        else:
            cluster_counter = defaultdict(int, cluster_counter_state)

    # ハッシュ値ごとに処理
    for integrated_hash, records in grouped_records.items():
        if not records:
            continue

        # クラスタリング実行
        # NOTE: is_judged フラグはリセットせず、前回の状態を保持する
        # これにより複数回呼び出された際に既に判定済みのレコードをスキップできる
        idx = 0
        while idx < len(records):
            # is_judged=False のレコードを探す
            if records[idx].is_judged:
                idx += 1
                continue

            # 新しいクラスタを開始
            cluster_counter[integrated_hash] += 1
            cluster_id = f"{integrated_hash}_cluster{cluster_counter[integrated_hash]}"

            # クラスタのレコードと経路を追跡
            cluster_records: List[DetectionRecord] = []
            route_sequence: List[str] = []

            # 最初のレコードを追加
            current_record = records[idx]
            current_record.is_judged = True
            current_record.cluster_id = cluster_id
            cluster_records.append(current_record)
            route_sequence.append(current_record.detector_id)
            prev_record = current_record

            # 次のレコードから順に追跡
            idx += 1
            while idx < len(records):
                candidate_record = records[idx]

                # 既に使用済みのレコードはスキップ
                if candidate_record.is_judged:
                    idx += 1
                    continue

                prev_det_id = prev_record.detector_id
                cand_det_id = candidate_record.detector_id
                trigger_forward_search = False  # 前方探索トリガーフラグ

                # 同じ検出器の場合の処理
                if cand_det_id == route_sequence[-1]:
                    if allow_long_stays:
                        # 長時間滞在を許可 → 無条件で追加
                        candidate_record.is_judged = True
                        candidate_record.cluster_id = cluster_id
                        cluster_records.append(candidate_record)
                        prev_record = candidate_record
                        idx += 1
                        continue
                    else:
                        # 長時間滞在を許可しない → 滞在時間をチェック
                        stay_time_diff = (
                            candidate_record.timestamp - prev_record.timestamp
                        ).total_seconds()
                        # TODO: この値は検討の余地あり
                        # - 現在: 15分（900秒）にハードコード
                        # - 検出エリアの特性によって適切な値は異なる
                        #   - 通路・歩道: 数分が妥当
                        #   - 公園・ショッピングモール: 数時間も妥当
                        # - 将来的には設定ファイルから読み込むか、検出器ごとに設定可能にする検討が必要
                        max_stay_duration = 900.0  # 15分

                        if stay_time_diff > max_stay_duration:
                            # 最大滞在時間を超過 → このレコードをスキップして前方探索へ
                            print(
                                f"[{cluster_id}] 滞在時間超過検出: "
                                f"{cand_det_id}での滞在時間={stay_time_diff:.1f}s > 最大={max_stay_duration:.1f}s "
                                f"→ 前方探索開始"
                            )
                            # 前方探索ロジックを実行（異なる検出器への到達可能なレコードを探す）
                            # この場合、前方探索のトリガーとして扱う
                            trigger_forward_search = True
                        else:
                            # 妥当な滞在時間 → 追加
                            candidate_record.is_judged = True
                            candidate_record.cluster_id = cluster_id
                            cluster_records.append(candidate_record)
                            prev_record = candidate_record
                            idx += 1
                            continue

                # 時間差を計算
                time_diff = (
                    candidate_record.timestamp - prev_record.timestamp
                ).total_seconds()

                # 最小移動時間を計算
                det_prev = detectors[prev_det_id]
                det_cand = detectors[cand_det_id]
                min_travel_time = calculate_min_travel_time(
                    det_prev, det_cand, walker_speed
                )

                # シーケンス番号フィルタ: 大きなシーケンス差がある場合
                seq_diff = abs(
                    candidate_record.sequence_number - prev_record.sequence_number
                )
                # ありえない移動の判定（シーケンス番号チェック含む）
                is_impossible_movement = time_diff < min_travel_time * impossible_factor
                is_sequence_anomaly = seq_diff > 64 and is_impossible_movement

                if is_sequence_anomaly:
                    print(
                        f"[{cluster_id}] シーケンス番号異常検出: "
                        f"{prev_det_id}→{cand_det_id} "
                        f"(seq差={seq_diff} > 64, 時間差={time_diff:.1f}s < 必要時間={min_travel_time:.1f}s) "
                        f"→ 前方探索"
                    )
                    # 前方探索に進む（下記のありえない移動処理と同じロジックを使う）

                # ありえない移動または長時間滞在の判定（シーケンス異常も含む）
                if is_impossible_movement or trigger_forward_search:
                    # ありえない移動または長時間滞在 → 前方を探索して到達可能なレコードを探す
                    if is_impossible_movement:
                        print(
                            f"[{cluster_id}] ありえない移動検出: "
                            f"{prev_det_id}→{cand_det_id} "
                            f"(時間差: {time_diff:.1f}s < 必要時間: {min_travel_time:.1f}s)"
                        )

                    # 前方探索: 到達可能なレコードを探す
                    scan_idx = idx
                    found_idx = None

                    while scan_idx < len(records):
                        scan_record = records[scan_idx]

                        # 既に使用済みはスキップ
                        if scan_record.is_judged:
                            scan_idx += 1
                            continue

                        # 同じ検出器の場合は滞在の継続として扱う
                        if scan_record.detector_id == route_sequence[-1]:
                            if allow_long_stays:
                                # 長時間滞在を許可 → 無条件で追加
                                scan_record.is_judged = True
                                scan_record.cluster_id = cluster_id
                                cluster_records.append(scan_record)
                                prev_record = scan_record
                                scan_idx += 1
                                continue
                            else:
                                # 滞在時間をチェック
                                stay_time_diff = (
                                    scan_record.timestamp - prev_record.timestamp
                                ).total_seconds()
                                max_stay_duration = 900.0  # 15分

                                if stay_time_diff <= max_stay_duration:
                                    # 妥当な滞在時間 → クラスタに追加して次の検出器を探し続ける
                                    scan_record.is_judged = True
                                    scan_record.cluster_id = cluster_id
                                    cluster_records.append(scan_record)
                                    prev_record = scan_record
                                    scan_idx += 1
                                    continue
                                else:
                                    # 滞在時間超過 → スキップ
                                    scan_idx += 1
                                    continue

                        # 既にルートに含まれている検出器をスキップ（ループを避ける）
                        if scan_record.detector_id in route_sequence:
                            scan_idx += 1
                            continue

                        # 到達可能性を判定
                        scan_time_diff = (
                            scan_record.timestamp - prev_record.timestamp
                        ).total_seconds()
                        det_scan = detectors[scan_record.detector_id]
                        min_t_scan = calculate_min_travel_time(
                            det_prev, det_scan, walker_speed
                        )

                        # シーケンス番号フィルタ（前方探索でも適用）
                        scan_seq_diff = abs(
                            scan_record.sequence_number - prev_record.sequence_number
                        )
                        if scan_seq_diff > 64 and scan_time_diff < min_t_scan * impossible_factor:
                            # 異常レコードとしてスキップ
                            scan_idx += 1
                            continue

                        if scan_time_diff >= min_t_scan * impossible_factor:
                            # 到達可能なレコード発見！
                            found_idx = scan_idx
                            print(
                                f"[{cluster_id}] 到達可能レコード発見: "
                                f"{prev_det_id}→{scan_record.detector_id} "
                                f"(idx {idx}→{found_idx}までスキップ)"
                            )
                            break

                        scan_idx += 1

                    if found_idx is not None:
                        # 到達可能なレコードが見つかった
                        # idx から found_idx-1 までのレコードは is_judged=False のまま
                        # found_idx のレコードを採用してクラスタ継続
                        found_record = records[found_idx]
                        found_record.is_judged = True
                        found_record.cluster_id = cluster_id
                        cluster_records.append(found_record)
                        if found_record.detector_id != route_sequence[-1]:
                            route_sequence.append(found_record.detector_id)
                        prev_record = found_record
                        idx = found_idx + 1
                        continue
                    else:
                        # 到達可能なレコードが見つからなかった
                        # クラスタをここで終了
                        print(f"[{cluster_id}] 到達可能レコードなし、クラスタ終了")
                        break

                # 正常な移動 → レコードを追加
                candidate_record.is_judged = True
                candidate_record.cluster_id = cluster_id
                cluster_records.append(candidate_record)
                route_sequence.append(cand_det_id)
                prev_record = candidate_record
                idx += 1

            # クラスタが有効なら（2つ以上の検出器を訪問）、軌跡として保存
            if len(route_sequence) >= 2:
                # EstimatedStayオブジェクトを作成（簡易版）
                stays = _create_estimated_stays(cluster_records, detectors)

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
                    f"レコード数={len(cluster_records)}"
                )

            # 1つのハッシュグループにつき1つのクラスタのみ作成
            # 次のパスで残りのレコードから新しいクラスタを作る
            break

    return estimated_trajectories, grouped_records, cluster_counter


def _create_estimated_stays(
    cluster_records: List[DetectionRecord], detectors: Dict[str, Detector]
) -> List[EstimatedStay]:
    """クラスタのレコードからEstimatedStayリストを作成（簡易版）

    Args:
        cluster_records: クラスタのレコードリスト
        detectors: 検出器の辞書

    Returns:
        EstimatedStayのリスト
    """
    stays: List[EstimatedStay] = []

    # 検出器ごとにグループ化
    records_by_detector = defaultdict(list)
    for rec in cluster_records:
        records_by_detector[rec.detector_id].append(rec)

    # 検出順にソート（最初の検出時刻順）
    detector_order = sorted(
        records_by_detector.keys(),
        key=lambda d: min(r.timestamp for r in records_by_detector[d]),
    )

    # 各検出器での滞在を推定
    for detector_id in detector_order:
        det_records = records_by_detector[detector_id]
        det_records.sort(key=lambda r: r.timestamp)

        first_detection = det_records[0].timestamp
        last_detection = det_records[-1].timestamp
        duration = (last_detection - first_detection).total_seconds()

        stay = EstimatedStay(
            detector_id=detector_id,
            first_detection=first_detection,
            last_detection=last_detection,
            estimated_duration_seconds=duration,
            num_detections=len(det_records),
        )
        stays.append(stay)

    return stays

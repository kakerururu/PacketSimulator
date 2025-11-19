from collections import defaultdict
from typing import Dict, List, Optional
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadRecordsCollection,
    ClusteredRoutes,
)


def classify_records_window_max(
    payload_records_collection: PayloadRecordsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
    impossible_factor: float = 0.8,
) -> tuple[ClusteredRoutes, PayloadRecordsCollection]:
    """
    不可能移動 (prev -> candidate の経過時間 actual_time が
    min_travel_time * impossible_factor 未満) を検知した際、
    「到達可能な次レコードが現れるまで」前方を無制限に探索する。

    分割境界戦略:
        採用候補（到達可能レコード）が一切見つからなかった場合のみ、
        分割境界を最初の不可能レコード位置 (scan_start_index) に置く。

    振る舞い:
    - 正常移動: 現在レコード detector_id をルートへ追加
    - 不可能移動:
        * 前方探索 (index = scan_start_index から末尾まで)
        * 条件を満たす最初の到達可能レコードを採用しジャンプ
        * 見つからなければクラスタ分割 (境界は scan_start_index)
          → 新クラスタはその不可能レコードを開始点にする
    - 同一検出器連続はスキップし追加しない

    戻り値:
        ClusteredRoutes(routes_by_cluster_id=<クラスタID→ルート文字列の辞書>)
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)

    for payload_id, records in payload_records_collection.records_by_payload.items():
        if not records:
            continue

        cluster_counter[payload_id] += 1
        # 各ペイロードの処理開始時に、すべてのレコードの is_judged を False に初期化
        for rec in records:
            rec.is_judged = False

        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        records[0].is_judged = True  # 最初のレコードは判定に使用される
        route_sequence: List[str] = [records[0].detector_id]

        prev_record = records[0]
        prev_record.is_judged = True  # 最初のprev_recordも判定に使用されるためTrueに
        idx = 1  # while で前方探索/ジャンプ対応

        while idx < len(records):
            current_record = records[idx]
            current_record.is_judged = True  # 判定に使用されるレコードをTrueに
            prev_det_id = prev_record.detector_id
            curr_det_id = current_record.detector_id

            # 同一検出器（移動なし）はスキップ
            if curr_det_id == route_sequence[-1]:
                prev_record = current_record
                idx += 1
                continue

            time_diff = (
                current_record.timestamp - prev_record.timestamp
            ).total_seconds()
            det_prev = detectors[prev_det_id]
            det_curr = detectors[curr_det_id]
            min_travel_time = calculate_min_travel_time(
                det_prev, det_curr, walker_speed
            )

            # 不可能移動判定
            if time_diff < min_travel_time * impossible_factor:
                scan_start_index = idx  # 最初の不可能レコード位置
                found_index: Optional[int] = None

                scan_idx = scan_start_index
                while scan_idx < len(records):
                    candidate = records[scan_idx]
                    # 同一検出器重複は採用しない
                    if candidate.detector_id == route_sequence[-1]:
                        scan_idx += 1
                        continue

                    candidate_time_diff = (
                        candidate.timestamp - prev_record.timestamp
                    ).total_seconds()
                    det_candidate = detectors[candidate.detector_id]
                    min_t_candidate = calculate_min_travel_time(
                        det_prev, det_candidate, walker_speed
                    )

                    if candidate_time_diff >= min_t_candidate * impossible_factor:
                        found_index = scan_idx
                        break

                    scan_idx += 1

                if found_index is not None:
                    # 採用候補発見: 不可能レコード列をノイズとして捨て、候補を追加
                    chosen = records[found_index]
                    chosen.is_judged = True  # 採用されたレコードは判定に使用される
                    if chosen.detector_id != route_sequence[-1]:
                        route_sequence.append(chosen.detector_id)
                    prev_record = chosen
                    idx = found_index + 1
                    continue
                else:
                    # 採用候補なし → 分割境界は最初の不可能レコード (scan_start_index)
                    if len(route_sequence) > 1:
                        estimated_clustered_routes[current_cluster_id] = "".join(
                            route_sequence
                        )

                    cluster_counter[payload_id] += 1
                    current_cluster_id = (
                        f"{payload_id}_cluster{cluster_counter[payload_id]}"
                    )
                    impossible_record = records[scan_start_index]
                    impossible_record.is_judged = (
                        True  # 新しいクラスタの開始点となるレコードは判定に使用される
                    )
                    route_sequence = [impossible_record.detector_id]
                    prev_record = impossible_record
                    idx = scan_start_index + 1
                    continue

            # 正常移動
            route_sequence.append(curr_det_id)
            prev_record = current_record
            idx += 1

        # 最終クラスタ確定
        if len(route_sequence) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(route_sequence)

    return (
        ClusteredRoutes(routes_by_cluster_id=estimated_clustered_routes),
        payload_records_collection,
    )


__all__ = ["classify_records_window_max"]

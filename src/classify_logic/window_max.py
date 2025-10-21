from collections import defaultdict
from typing import Dict, List, Optional
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadEventsCollection,
    ClusteredRoutes,
)


def classify_events_window_max(
    payload_events_collection: PayloadEventsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
    impossible_factor: float = 0.8,
) -> ClusteredRoutes:
    """
    不可能移動 (prev -> candidate の経過時間 actual_time が
    min_travel_time * impossible_factor 未満) を検知した際、
    「到達可能な次イベントが現れるまで」前方を無制限に探索する。

    分割境界戦略:
        採用候補（到達可能イベント）が一切見つからなかった場合のみ、
        分割境界を最初の不可能イベント位置 (scan_start_index) に置く。

    振る舞い:
    - 正常移動: 現在イベント detector_id をルートへ追加
    - 不可能移動:
        * 前方探索 (index = scan_start_index から末尾まで)
        * 条件を満たす最初の到達可能イベントを採用しジャンプ
        * 見つからなければクラスタ分割 (境界は scan_start_index)
          → 新クラスタはその不可能イベントを開始点にする
    - 同一検出器連続はスキップし追加しない

    戻り値:
        ClusteredRoutes(routes_by_cluster_id=<クラスタID→ルート文字列の辞書>)
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)

    for payload_id, events in payload_events_collection.events_by_payload.items():
        if not events:
            continue

        cluster_counter[payload_id] += 1
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        route_sequence: List[str] = [events[0].detector_id]

        prev_event = events[0]
        idx = 1  # while で前方探索/ジャンプ対応

        while idx < len(events):
            current_event = events[idx]
            prev_det_id = prev_event.detector_id
            curr_det_id = current_event.detector_id

            # 同一検出器（移動なし）はスキップ
            if curr_det_id == route_sequence[-1]:
                prev_event = current_event
                idx += 1
                continue

            time_diff = (current_event.timestamp - prev_event.timestamp).total_seconds()
            det_prev = detectors[prev_det_id]
            det_curr = detectors[curr_det_id]
            min_travel_time = calculate_min_travel_time(
                det_prev, det_curr, walker_speed
            )

            # 不可能移動判定
            if time_diff < min_travel_time * impossible_factor:
                scan_start_index = idx  # 最初の不可能イベント位置
                found_index: Optional[int] = None

                scan_idx = scan_start_index
                while scan_idx < len(events):
                    candidate = events[scan_idx]
                    # 同一検出器重複は採用しない
                    if candidate.detector_id == route_sequence[-1]:
                        scan_idx += 1
                        continue

                    candidate_time_diff = (
                        candidate.timestamp - prev_event.timestamp
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
                    # 採用候補発見: 不可能イベント列をノイズとして捨て、候補を追加
                    chosen = events[found_index]
                    if chosen.detector_id != route_sequence[-1]:
                        route_sequence.append(chosen.detector_id)
                    prev_event = chosen
                    idx = found_index + 1
                    continue
                else:
                    # 採用候補なし → 分割境界は最初の不可能イベント (scan_start_index)
                    if len(route_sequence) > 1:
                        estimated_clustered_routes[current_cluster_id] = "".join(
                            route_sequence
                        )

                    cluster_counter[payload_id] += 1
                    current_cluster_id = (
                        f"{payload_id}_cluster{cluster_counter[payload_id]}"
                    )
                    impossible_event = events[scan_start_index]
                    route_sequence = [impossible_event.detector_id]
                    prev_event = impossible_event
                    idx = scan_start_index + 1
                    continue

            # 正常移動
            route_sequence.append(curr_det_id)
            prev_event = current_event
            idx += 1

        # 最終クラスタ確定
        if len(route_sequence) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(route_sequence)

    return ClusteredRoutes(routes_by_cluster_id=estimated_clustered_routes)


__all__ = ["classify_events_window_max"]

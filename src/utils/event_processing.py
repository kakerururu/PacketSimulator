from collections import defaultdict
from typing import Dict, List, Any
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    CollectedEvent,
    PayloadEventsCollection,
    ClusteredRoutes,  # 新規インポート
)


def collect_and_sort_events(
    logs: List[Dict[str, Any]], detectors: Dict[str, Detector]
) -> PayloadEventsCollection:
    """ログデータからHashed_Payloadごとのイベントを収集し、時間順にソートする"""
    payload_events_raw = defaultdict(list)
    for log_entry in logs:
        current_detector_id = None
        for det_id, det_obj in detectors.items():
            if (
                det_obj.x == log_entry["Detector_X"]
                and det_obj.y == log_entry["Detector_Y"]
            ):
                current_detector_id = det_id
                break
        if current_detector_id:
            payload_events_raw[log_entry["Hashed_Payload"]].append(
                CollectedEvent(
                    timestamp=log_entry["Timestamp"],
                    detector_id=current_detector_id,
                    detector_x=log_entry["Detector_X"],
                    detector_y=log_entry["Detector_Y"],
                )
            )

    events_by_payload: Dict[str, List[CollectedEvent]] = {}
    for payload_id, events in payload_events_raw.items():
        events.sort(key=lambda x: x.timestamp)
        events_by_payload[payload_id] = events

    return PayloadEventsCollection(events_by_payload=events_by_payload)


def process_payload_events_for_clustering(
    payload_events_collection: PayloadEventsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
) -> ClusteredRoutes:  # 戻り値の型を変更
    """
    Hashed_Payloadごとのイベントを分析し、ありえない移動があった場合に新しいクラスタIDを割り当てる。
    戻り値: キーがクラスタID、値が推定ルート文字列の辞書
    例: {"payload1_cluster1": "ABCD", "payload1_cluster2": "ACD", "payload2_cluster1": "BCD"}
    """
    estimated_clustered_routes = {}
    cluster_counter = defaultdict(int)

    for (
        payload_id,
        events,
    ) in payload_events_collection.events_by_payload.items():
        if not events:
            continue

        current_route_sequence_list = []

        cluster_counter[payload_id] += 1
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        current_route_sequence_list.append(events[0].detector_id)

        prev_event = events[0]

        for i in range(1, len(events)):
            current_event = events[i]

            prev_det_id = prev_event.detector_id
            current_det_id = current_event.detector_id

            if current_det_id == current_route_sequence_list[-1]:
                prev_event = current_event
                continue

            time_diff = (current_event.timestamp - prev_event.timestamp).total_seconds()

            det1_obj = detectors[prev_det_id]
            det2_obj = detectors[current_det_id]

            min_travel_time = calculate_min_travel_time(
                det1_obj, det2_obj, walker_speed
            )

            if time_diff < min_travel_time * 0.8:
                if len(current_route_sequence_list) > 1:
                    estimated_clustered_routes[current_cluster_id] = "".join(
                        current_route_sequence_list
                    )

                cluster_counter[payload_id] += 1
                current_cluster_id = (
                    f"{payload_id}_cluster{cluster_counter[payload_id]}"
                )
                current_route_sequence_list = [current_det_id]
                prev_event = current_event
                continue

            current_route_sequence_list.append(current_det_id)
            prev_event = current_event

        if len(current_route_sequence_list) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(
                current_route_sequence_list
            )

    return ClusteredRoutes(
        routes_by_cluster_id=estimated_clustered_routes
    )  # ClusteredRoutes オブジェクトを返す

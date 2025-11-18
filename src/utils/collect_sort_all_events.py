from collections import defaultdict
from typing import Dict, List, Any
from domain.detector import Detector
from domain.analysis_results import (
    Event,
    PayloadEventsCollection,
)


def collect_and_sort_events(
    logs: List[Dict[str, Any]], detectors: Dict[str, Detector]
) -> PayloadEventsCollection:
    """ログデータからHashed_Payloadごとのイベントを収集し、時間順にソートする
    具体例：{"payload_1": [event1, event2], "payload_2": [event3], ...}

    """
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
                Event(
                    timestamp=log_entry["Timestamp"],
                    detector_id=current_detector_id,
                    detector_x=log_entry["Detector_X"],
                    detector_y=log_entry["Detector_Y"],
                    sequence_number=log_entry["Sequence_Number"],  # 追加
                )
            )

    events_by_payload: Dict[str, List[Event]] = {}
    for payload_id, events in payload_events_raw.items():
        events.sort(key=lambda x: x.timestamp)
        events_by_payload[payload_id] = events

    return PayloadEventsCollection(events_by_payload=events_by_payload)

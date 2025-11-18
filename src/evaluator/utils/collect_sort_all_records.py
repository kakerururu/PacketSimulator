from collections import defaultdict
from typing import Dict, List, Any
from domain.detector import Detector
from domain.analysis_results import (
    Record,
    PayloadRecordsCollection,
)


def collect_and_sort_records(
    logs: List[Dict[str, Any]], detectors: Dict[str, Detector]
) -> PayloadRecordsCollection:
    """ログデータからHashed_Payloadごとのレコードを収集し、時間順にソートする
    具体例：{"payload_1": [record1, record2], "payload_2": [record3], ...}

    """
    payload_records_raw = defaultdict(list)
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
            payload_records_raw[log_entry["Hashed_Payload"]].append(
                Record(
                    timestamp=log_entry["Timestamp"],
                    detector_id=current_detector_id,
                    detector_x=log_entry["Detector_X"],
                    detector_y=log_entry["Detector_Y"],
                    sequence_number=log_entry["Sequence_Number"],  # 追加
                )
            )

    records_by_payload: Dict[str, List[Record]] = {}
    for payload_id, records in payload_records_raw.items():
        records.sort(key=lambda x: x.timestamp)
        records_by_payload[payload_id] = records

    return PayloadRecordsCollection(records_by_payload=records_by_payload)

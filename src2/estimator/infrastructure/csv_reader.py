"""検出ログCSV読み込み"""

import csv
from pathlib import Path
from typing import List
from ..domain.detection_record import DetectionRecord
from ...shared.utils.datetime_utils import parse_timestamp


def read_detector_logs(detector_logs_dir: str = "src2_result/detector_logs") -> List[DetectionRecord]:
    """検出ログCSVファイルを読み込み、全レコードをリストとして返す

    Args:
        detector_logs_dir: 検出ログディレクトリのパス

    Returns:
        全検出レコードのリスト（タイムスタンプ順にソート済み）

    Examples:
        >>> records = read_detector_logs("src2_result/detector_logs")
        >>> len(records) > 0
        True
        >>> isinstance(records[0], DetectionRecord)
        True
    """
    all_records = []
    logs_dir = Path(detector_logs_dir)

    # 全CSVファイルを読み込む
    for csv_file in sorted(logs_dir.glob("*_log.csv")):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                record = DetectionRecord(
                    timestamp=parse_timestamp(row["Timestamp"]),
                    walker_id=row["Walker_ID"],
                    hashed_id=row["Hashed_ID"],
                    detector_id=row["Detector_ID"],
                    sequence_number=int(row["Sequence_Number"]),
                    is_judged=False,
                )
                all_records.append(record)

    # タイムスタンプ順にソート
    all_records.sort(key=lambda r: r.timestamp)

    return all_records


def read_detector_log_by_detector(
    detector_id: str, detector_logs_dir: str = "src2_result/detector_logs"
) -> List[DetectionRecord]:
    """特定の検出器の検出ログCSVファイルを読み込む

    Args:
        detector_id: 検出器ID（例: "A"）
        detector_logs_dir: 検出ログディレクトリのパス

    Returns:
        指定検出器の検出レコードリスト（タイムスタンプ順にソート済み）

    Examples:
        >>> records = read_detector_log_by_detector("A", "src2_result/detector_logs")
        >>> all(r.detector_id == "A" for r in records)
        True
    """
    records = []
    logs_dir = Path(detector_logs_dir)
    csv_file = logs_dir / f"{detector_id}_log.csv"

    if not csv_file.exists():
        return records

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = DetectionRecord(
                timestamp=parse_timestamp(row["Timestamp"]),
                walker_id=row["Walker_ID"],
                hashed_id=row["Hashed_ID"],
                detector_id=row["Detector_ID"],
                sequence_number=int(row["Sequence_Number"]),
                is_judged=False,
            )
            records.append(record)

    # タイムスタンプ順にソート
    records.sort(key=lambda r: r.timestamp)

    return records

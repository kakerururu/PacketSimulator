"""検出ログCSV出力モジュール"""

import csv
from pathlib import Path
from typing import List
from ..domain.detection_record import DetectionRecord
from .utils import format_timestamp


def write_detector_logs(
    detection_records: List[DetectionRecord],
    output_dir_path: str = "src2_result/detector_logs",
) -> None:
    """検出レコードを検出器ごとのCSVファイルに書き込む

    Args:
        records: 検出レコードのリスト
        output_dir: 出力ディレクトリパス

    Notes:
        - 各検出器ごとに1つのCSVファイルを生成
        - ファイル名: {detector_id}_log.csv
        - タイムスタンプでソートして出力

    Examples:
        >>> records = [
        ...     DetectionRecord(
        ...         timestamp=datetime(2024, 1, 14, 11, 0, 5),
        ...         walker_id="Walker_1",
        ...         hashed_id="C_01_base_payload",
        ...         detector_id="A",
        ...         sequence_number=100
        ...     )
        ... ]
        >>> write_detector_logs(records, "test_output")
    """
    # 出力ディレクトリを作成
    output_path = Path(output_dir_path)
    output_path.mkdir(parents=True, exist_ok=True)

    # 検出器IDごとにレコードをグループ化
    records_by_detector = {}
    for record in detection_records:
        if record.detector_id not in records_by_detector:
            records_by_detector[record.detector_id] = []
        records_by_detector[record.detector_id].append(record)

    # 検出器ごとにCSVファイルを作成
    for detector_id, detector_records in records_by_detector.items():
        file_path = output_path / f"{detector_id}_log.csv"

        # タイムスタンプでソート
        detector_records.sort(key=lambda r: r.timestamp)

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー（plan.mdの仕様：Detector座標は含めない）
            writer.writerow(
                [
                    "Timestamp",
                    "Walker_ID",
                    "Hashed_Payload",
                    "Detector_ID",
                    "Sequence_Number",
                ]
            )

            # データ
            for record in detector_records:
                writer.writerow(
                    [
                        format_timestamp(record.timestamp),
                        record.walker_id,
                        record.hashed_id,
                        record.detector_id,
                        record.sequence_number,
                    ]
                )

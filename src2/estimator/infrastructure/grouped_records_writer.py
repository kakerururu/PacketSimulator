"""グループ化されたレコードのCSV出力"""

import csv
from pathlib import Path
from typing import Dict, List, Optional
from ..domain.detection_record import DetectionRecord
from ...shared.utils.datetime_utils import format_timestamp


def export_grouped_records(
    grouped_records: Dict[str, List[DetectionRecord]],
    output_dir: str = "src2_result/grouped_records",
    include_index: bool = True,
    clean_before: bool = True,
) -> Dict[str, any]:
    """グループ化されたレコードをペイロードごとのCSVファイルに出力

    Args:
        grouped_records: ハッシュ値をキーとしたレコードリストの辞書
        output_dir: 出力ディレクトリパス
        include_index: index.csvを出力するか
        clean_before: 出力前に既存ファイルを削除するか

    Returns:
        出力情報の辞書 {
            "num_payloads": int,
            "written_files": List[str],
            "index_file": Optional[str]
        }

    Examples:
        >>> from datetime import datetime
        >>> from ..domain.detection_record import DetectionRecord
        >>> records = {
        ...     "C_01_integrated": [
        ...         DetectionRecord(
        ...             timestamp=datetime(2024, 1, 14, 11, 0, 5),
        ...             walker_id="Walker_1",
        ...             hashed_id="C_01_base_hash",
        ...             detector_id="A",
        ...             sequence_number=100,
        ...             is_judged=False
        ...         )
        ...     ]
        ... }
        >>> result = export_grouped_records(records, "test_output")
        >>> result["num_payloads"]
        1
    """
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 既存ファイルを削除
    if clean_before:
        for pattern in ["payload_*.csv", "index.csv"]:
            for file_path in output_path.glob(pattern):
                try:
                    file_path.unlink()
                except OSError:
                    pass

    written_files: List[str] = []
    index_rows: List[tuple] = []

    # ペイロードごとにCSVファイルを作成
    for integrated_hash, records in grouped_records.items():
        if not records:
            continue

        # ファイル名安全化（英数字以外は '_'）
        safe_hash = "".join(ch if ch.isalnum() else "_" for ch in integrated_hash)
        filename = f"payload_{safe_hash}.csv"
        file_path = output_path / filename

        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow(
                [
                    "Integrated_Hash",
                    "Original_Hash",
                    "Timestamp",
                    "Walker_ID",
                    "Detector_ID",
                    "Sequence_Number",
                    "Is_Judged",
                ]
            )

            # データ
            for record in records:
                writer.writerow(
                    [
                        integrated_hash,
                        record.hashed_id,  # 元のハッシュ値も記録
                        format_timestamp(record.timestamp),
                        record.walker_id,
                        record.detector_id,
                        record.sequence_number,
                        record.is_judged,
                    ]
                )

        written_files.append(str(file_path))

        # インデックス用の情報を記録
        first_ts = format_timestamp(records[0].timestamp)
        last_ts = format_timestamp(records[-1].timestamp)
        index_rows.append((integrated_hash, len(records), first_ts, last_ts))

    # インデックスファイルを出力
    index_file: Optional[str] = None
    if include_index:
        index_file = str(output_path / "index.csv")
        with open(index_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Integrated_Hash", "NumRecords", "FirstTimestamp", "LastTimestamp"]
            )
            writer.writerows(index_rows)

    return {
        "num_payloads": len(index_rows),
        "written_files": written_files,
        "index_file": index_file,
    }

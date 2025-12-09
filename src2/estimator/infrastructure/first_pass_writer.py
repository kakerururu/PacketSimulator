"""第1回目推定結果のCSV出力"""

import csv
from pathlib import Path
from typing import Dict, List
from ..domain.detection_record import DetectionRecord
from ...shared.utils.datetime_utils import format_timestamp


def export_first_pass_clusters(
    grouped_records: Dict[str, List[DetectionRecord]],
    output_dir: str = "src2_result/first_pass_clusters",
    clean_before: bool = True,
) -> Dict[str, any]:
    """第1回目推定後のレコードをCSV出力

    is_judged フラグの状態を含めて出力する。
    これにより、どのレコードが第1回目の推定で使用されたかが分かる。

    Args:
        grouped_records: ハッシュ値ごとのレコードリスト（is_judged更新済み）
        output_dir: 出力ディレクトリパス
        clean_before: 出力前に既存ファイルを削除するか

    Returns:
        出力情報の辞書 {
            "num_payloads": int,
            "written_files": List[str],
            "summary_file": str,
            "total_judged": int,
            "total_unjudged": int
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
        ...             is_judged=True
        ...         )
        ...     ]
        ... }
        >>> result = export_first_pass_clusters(records, "test_output")
    """
    # 出力ディレクトリを作成
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 既存ファイルを削除
    if clean_before:
        for pattern in ["cluster_*.csv", "summary.csv"]:
            for file_path in output_path.glob(pattern):
                try:
                    file_path.unlink()
                except OSError:
                    pass

    written_files: List[str] = []
    summary_rows: List[tuple] = []
    total_judged = 0
    total_unjudged = 0

    # ペイロードごとにCSVファイルを作成
    for integrated_hash, records in grouped_records.items():
        if not records:
            continue

        # ファイル名安全化
        safe_hash = "".join(ch if ch.isalnum() else "_" for ch in integrated_hash)
        filename = f"cluster_{safe_hash}.csv"
        file_path = output_path / filename

        # is_judged の統計
        judged_count = sum(1 for r in records if r.is_judged)
        unjudged_count = len(records) - judged_count
        total_judged += judged_count
        total_unjudged += unjudged_count

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
                    "Is_Judged",  # 第1回目で使用されたか
                ]
            )

            # データ
            for record in records:
                writer.writerow(
                    [
                        integrated_hash,
                        record.hashed_id,
                        format_timestamp(record.timestamp),
                        record.walker_id,
                        record.detector_id,
                        record.sequence_number,
                        record.is_judged,
                    ]
                )

        written_files.append(str(file_path))

        # サマリー情報を記録
        first_ts = format_timestamp(records[0].timestamp)
        last_ts = format_timestamp(records[-1].timestamp)
        summary_rows.append(
            (
                integrated_hash,
                len(records),
                judged_count,
                unjudged_count,
                first_ts,
                last_ts,
            )
        )

    # サマリーファイルを出力
    summary_file = str(output_path / "summary.csv")
    with open(summary_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Integrated_Hash",
                "TotalRecords",
                "JudgedRecords",
                "UnjudgedRecords",
                "FirstTimestamp",
                "LastTimestamp",
            ]
        )
        writer.writerows(summary_rows)

    return {
        "num_payloads": len(summary_rows),
        "written_files": written_files,
        "summary_file": summary_file,
        "total_judged": total_judged,
        "total_unjudged": total_unjudged,
    }

import os
import csv
import gzip
import glob
from typing import Optional
from datetime import datetime
from domain.analysis_results import PayloadEventsCollection


def _format_timestamp(ts: datetime) -> str:
    """
    既存ログ形式に合わせてミリ秒まで出力（最後の3桁切り捨て）:
    YYYY-MM-DD HH:MM:SS.mmm
    """
    return ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def export_payload_events(
    payload_events_collection: PayloadEventsCollection,
    output_dir: str = "result/payload_events",
    include_index: bool = True,
    gzip_compress: bool = False,
    clean_before: bool = True,
) -> dict:
    """
    ペイロードごとにソート済みイベントを個別CSVへ書き出す。

    出力:
      output_dir/payload_<payload_id_sanitized>.csv (または .csv.gz)
    オプション:
      - include_index: index.csv を併せて出力し要約統計を記載
      - gzip_compress: 個別ファイルを gzip 圧縮 (.csv.gz) 形式で保存

    戻り値:
      {
        "num_payloads": <int>,
        "written_files": [<str>, ...],
        "index_file": <str|None>
      }
    """
    os.makedirs(output_dir, exist_ok=True)
    if clean_before:
        for pattern in ("payload_*.csv", "payload_*.csv.gz", "index.csv"):
            for fp in glob.glob(os.path.join(output_dir, pattern)):
                try:
                    os.remove(fp)
                except OSError:
                    pass
    written_files: list[str] = []
    index_rows: list[tuple[str, int, str, str]] = []

    for payload_id, events in payload_events_collection.events_by_payload.items():
        if not events:
            continue

        # ペイロードIDのファイル名安全化（英数字以外は '_'）
        safe_id = "".join(ch if ch.isalnum() else "_" for ch in payload_id)
        filename = f"payload_{safe_id}.csv"
        if gzip_compress:
            filename += ".gz"
        file_path = os.path.join(output_dir, filename)

        if gzip_compress:
            f_open = gzip.open  # type: ignore
            mode = "wt"
        else:
            f_open = open
            mode = "w"

        with f_open(file_path, mode, newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Payload_ID",
                    "Timestamp",
                    "Detector_ID",
                    "Detector_X",
                    "Detector_Y",
                    "Sequence_Number",
                ]
            )
            for ev in events:  # ev: CollectedEvent
                writer.writerow(
                    [
                        payload_id,
                        _format_timestamp(ev.timestamp),
                        ev.detector_id,
                        f"{ev.detector_x:.6f}",
                        f"{ev.detector_y:.6f}",
                        ev.sequence_number,
                    ]
                )

        written_files.append(file_path)

        first_ts = _format_timestamp(events[0].timestamp)
        last_ts = _format_timestamp(events[-1].timestamp)
        index_rows.append((payload_id, len(events), first_ts, last_ts))

    index_file: Optional[str] = None
    if include_index:
        index_file = os.path.join(output_dir, "index.csv")
        with open(index_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Payload_ID", "NumEvents", "FirstTimestamp", "LastTimestamp"]
            )
            writer.writerows(index_rows)

    return {
        "num_payloads": len(index_rows),
        "written_files": written_files,
        "index_file": index_file,
    }


__all__ = ["export_payload_events"]

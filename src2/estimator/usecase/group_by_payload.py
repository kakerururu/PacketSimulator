"""ペイロードごとのレコードグルーピングと類似ハッシュ統合"""

from collections import defaultdict
from typing import Dict, List
from ..domain.detection_record import DetectionRecord


def integrate_similar_payloads(hashed_id: str) -> str:
    """類似ハッシュ値を統合して代表ハッシュ値を返す

    同一モデルの base_hash と sub_hash を integrated_hash に統合する。
    将来的には編集距離による類似度計算（95%以上で統合）を実装予定。

    Args:
        hashed_id: 元のハッシュ値

    Returns:
        統合後のハッシュ値

    Examples:
        >>> integrate_similar_payloads("C_01_base_hash")
        'C_01_integrated'
        >>> integrate_similar_payloads("C_01_sub_hash")
        'C_01_integrated'
        >>> integrate_similar_payloads("B_common_hash_X")
        'B_common_hash_X'
        >>> integrate_similar_payloads("unique_and_hashed_payload_Walker_1")
        'unique_and_hashed_payload_Walker_1'
    """
    # C系モデル（C_01 ~ C_10）の統合ルール
    # C_XX_base_hash と C_XX_sub_hash を C_XX_integrated に統合
    if hashed_id.startswith("C_") and ("_base_hash" in hashed_id or "_sub_hash" in hashed_id):
        # "C_01_base_hash" → "C_01"
        # "C_01_sub_hash" → "C_01"
        model_prefix = hashed_id.split("_base_")[0].split("_sub_")[0]
        return f"{model_prefix}_integrated"

    # D系モデル（D_01 ~ D_03）の統合ルール
    # D_XX_stateY_hash はそのまま（統合しない）
    # 将来的に必要なら追加

    # その他のハッシュ値はそのまま
    return hashed_id


def group_records_by_payload(
    detection_records: List[DetectionRecord],
) -> Dict[str, List[DetectionRecord]]:
    """検出レコードをペイロード（ハッシュ値）ごとにグループ化

    類似ハッシュ値の統合を行い、統合後のハッシュ値でグループ化する。

    Args:
        detection_records: 検出レコードのリスト

    Returns:
        統合後のハッシュ値をキーとした、レコードリストの辞書

    Examples:
        >>> from datetime import datetime
        >>> records = [
        ...     DetectionRecord(
        ...         timestamp=datetime(2024, 1, 14, 11, 0, 5),
        ...         walker_id="Walker_1",
        ...         hashed_id="C_01_base_hash",
        ...         detector_id="A",
        ...         sequence_number=100,
        ...         is_judged=False
        ...     ),
        ...     DetectionRecord(
        ...         timestamp=datetime(2024, 1, 14, 11, 0, 6),
        ...         walker_id="Walker_1",
        ...         hashed_id="C_01_sub_hash",
        ...         detector_id="A",
        ...         sequence_number=101,
        ...         is_judged=False
        ...     )
        ... ]
        >>> grouped = group_records_by_payload(records)
        >>> "C_01_integrated" in grouped
        True
        >>> len(grouped["C_01_integrated"])
        2
    """
    grouped_records = defaultdict(list)

    for record in detection_records:
        # 類似ハッシュ値を統合
        integrated_hash = integrate_similar_payloads(record.hashed_id)
        grouped_records[integrated_hash].append(record)

    # 各グループ内でタイムスタンプ順にソート
    for hashed_id in grouped_records:
        grouped_records[hashed_id].sort(key=lambda r: r.timestamp)

    return dict(grouped_records)

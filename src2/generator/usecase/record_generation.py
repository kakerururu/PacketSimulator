"""検出レコード生成ユースケース

責務: 滞在期間中の検出レコード生成とペイロード選択
"""

import random
from datetime import timedelta
from typing import List
from ..domain.walker import Walker
from ..domain.stay import Stay
from ..domain.detection_record import DetectionRecord
from ..domain.payload_config import PayloadDefinitionsDict
from ..infrastructure.config_loader import load_simulation_settings


def choose_payload(
    walker_id: str,
    model_name: str,
    payload_definitions: PayloadDefinitionsDict,
) -> str:
    """レコード生成時にペイロードを選択

    ユニーク型モデルの場合はwalker_idに基づいて固定ペイロードを生成。
    その他のモデルの場合は確率分布に基づいて選択。

    Args:
        walker_id: 通行人ID
        model_name: モデル名
        payload_definitions: ペイロード定義

    Returns:
        選択されたペイロード
    """
    # ユニーク型モデルの場合は walker_id に基づいて固定ハッシュ値を生成
    if payload_definitions[model_name]["is_unique"]:
        return f"unique_and_hashed_payload_{walker_id}"

    # 確率分布に基づいてペイロードを選択
    distribution = payload_definitions[model_name]["payload_distribution"]
    payload_types = list(distribution.keys())
    probabilities = list(distribution.values())

    return random.choices(payload_types, weights=probabilities, k=1)[0]


def generate_detection_records(
    walker: Walker,
    stays: List[Stay],
    payload_definitions: PayloadDefinitionsDict,
) -> List[DetectionRecord]:
    """滞在リストから検出レコードを生成し、オブジェクトとして返す

    各滞在期間中に、連続するシーケンス番号を持つペイロードの塊を生成します。
    各塊のサイズは1,2,3,4個のいずれかで、それぞれ25%の確率で決定されます。

    Args:
        walker: 通行人
        stays: 滞在リスト
        payload_definitions: ペイロード定義

    Returns:
        検出レコードのリスト

    Examples:
        payloads_per_detector=10の場合、例えば以下のような塊に分割される：
        - 塊1: 3個連続 (seq: 100, 101, 102)
        - 塊2: 2個連続 (seq: 500, 501)
        - 塊3: 4個連続 (seq: 1000, 1001, 1002, 1003)
        - 塊4: 1個 (seq: 2000)
        合計: 3+2+4+1 = 10個
    """
    # 設定ファイルから数値パラメータを読み込む
    settings = load_simulation_settings()
    payloads_per_detector = settings["payloads_per_detector_per_walker"]

    records = []

    for stay in stays:
        stay_records = []

        # 上限までのペイロード数
        remaining = payloads_per_detector
        chunks = []  # [(chunk_size, start_offset, start_seq), ...]

        while remaining > 0:
            # 1,2,3,4のいずれかを25%ずつの確率で選択
            # 塊のサイズを一つ決定
            chunk_size = random.choices([1, 2, 3, 4], weights=[0.25, 0.25, 0.25, 0.25])[
                0
            ]

            # 上限を超えそうなら残りの数に調整
            if chunk_size > remaining:
                chunk_size = remaining

            # この塊の開始オフセット（滞在時間内のランダムな位置）
            # 滞在時間を超えない中で、塊のスタート時間を決定
            max_offset = stay.duration_seconds - (chunk_size * 0.001)
            start_offset = random.uniform(
                0, max(0, max_offset)
            )  # 滞在開始からの経過秒数

            # この塊の開始シーケンス番号
            start_seq = random.randint(0, 4095)

            chunks.append((chunk_size, start_offset, start_seq))
            remaining -= chunk_size

        # 各塊についてレコードを生成
        for chunk_size, start_offset, start_seq in chunks:
            for i in range(chunk_size):
                # 時刻: 開始オフセット + i ミリ秒
                record_time = (
                    stay.arrival_time
                    + timedelta(seconds=start_offset)
                    + timedelta(milliseconds=i)
                )

                # ペイロード選択
                chosen_payload = choose_payload(
                    walker.id, walker.model, payload_definitions
                )

                # シーケンス番号: 連続
                seq_number = (start_seq + i) % 4096

                stay_records.append(
                    DetectionRecord(
                        timestamp=record_time,
                        walker_id=walker.id,
                        hashed_id=chosen_payload,
                        detector_id=stay.detector_id,
                        sequence_number=seq_number,
                    )
                )

        # タイムスタンプでソート
        stay_records.sort(key=lambda r: r.timestamp)
        records.extend(stay_records)

    return records

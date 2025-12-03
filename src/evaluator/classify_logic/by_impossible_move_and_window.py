from collections import defaultdict
from typing import Dict, List, Optional
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadRecordsCollection,
    ClusteredRoutes,
)


def classify_records_by_impossible_move_and_window(
    payload_records_collection: PayloadRecordsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
    max_lookahead: int = 5,
    impossible_factor: float = 0.8,
) -> tuple[ClusteredRoutes, PayloadRecordsCollection]:  # 戻り値の型を変更
    """
    ありえない移動 (prev -> current が最小移動時間 * impossible_factor 未満) を検知した際、
    直後最大 max_lookahead 個のレコードの中に「prev から物理的に到達可能」なレコードがあるかを探索し、
    あればそのレコードをルートに採用してクラスタ分割を回避する簡易ブリッジ手法を用いる。

    振る舞い概要:
    - 正常移動: 現在レコード検出器IDをシーケンスに追加
    - 不可能移動判定:
        * current はシーケンスに追加せず捨てる
        * lookahead window 内で最初に到達可能なレコード (prev から travel_time 条件を満たす) を探索
        * 見つかれば: そのレコードをシーケンスに追加し prev をそのレコードへ更新 (インデックスをジャンプ)
        * 見つからなければ: そこまでのルートを確定し新クラスタ開始

    戻り値: ClusteredRoutes
    routes_by_cluster_id: {クラスタID: ルート文字列}

    パラメータ:
    - max_lookahead: 不可能移動後に探索する最大レコード数
    - impossible_factor: 不可能移動判定係数 (time_diff < min_travel_time * impossible_factor)

    例:
    {"payload1_cluster1": "ABCD", "payload1_cluster2": "ACE", ...}
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)

    for payload_id, records in payload_records_collection.records_by_payload.items():
        if not records:
            continue

        # 新しいクラスタ開始
        cluster_counter[payload_id] += 1
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        records[0].is_judged = True  # 最初のレコードを判定済みとする
        route_sequence: List[str] = [records[0].detector_id]

        prev_record = records[0]
        prev_record.is_judged = True  # prev_recordも判定済みとする
        i = 1  # while でインデックス制御（lookaheadジャンプに対応）

        while i < len(records):
            current_record = records[i]
            current_record.is_judged = True  # current_recordも判定済みとする

            prev_det_id = prev_record.detector_id
            curr_det_id = current_record.detector_id

            # 直前と同じ検出器ならスキップ（移動なし）
            if curr_det_id == route_sequence[-1]:
                prev_record = current_record
                i += 1
                continue

            time_diff = (
                current_record.timestamp - prev_record.timestamp
            ).total_seconds()
            det_prev = detectors[prev_det_id]
            det_curr = detectors[curr_det_id]
            min_travel_time = calculate_min_travel_time(
                det_prev, det_curr, walker_speed
            )

            # 不可能移動判定
            if time_diff < min_travel_time * impossible_factor:
                current_record.is_judged = False  # 不可能移動レコードは判定に使用しない
                # lookahead 探索
                look_found_index: Optional[int] = None
                for j in range(i + 1, min(i + 1 + max_lookahead, len(records))):
                    candidate = records[j]
                    candidate_time_diff = (
                        candidate.timestamp - prev_record.timestamp
                    ).total_seconds()
                    det_candidate = detectors[candidate.detector_id]
                    min_t_candidate = calculate_min_travel_time(
                        det_prev, det_candidate, walker_speed
                    )
                    # 到達可能ならそのレコードを採用
                    if candidate_time_diff >= min_t_candidate * impossible_factor:
                        look_found_index = j
                        break

                if look_found_index is not None:
                    # ブリッジ成功: 不可能だった current を無視し、到達可能な candidate を採用
                    candidate_record = records[look_found_index]
                    candidate_record.is_judged = (
                        True  # 採用されたレコードも判定済みとする
                    )
                    # 重複検出器防止
                    # ここで、重複する検出器IDを持つレコードをスキップ
                    if candidate_record.detector_id != route_sequence[-1]:
                        route_sequence.append(candidate_record.detector_id)
                    prev_record = candidate_record
                    i = look_found_index + 1  # 採用レコードの次から継続
                    continue
                else:
                    # ブリッジ失敗: ここでクラスタ分割
                    if len(route_sequence) > 1:
                        estimated_clustered_routes[current_cluster_id] = "".join(
                            route_sequence
                        )

                    cluster_counter[payload_id] += 1
                    current_cluster_id = (
                        f"{payload_id}_cluster{cluster_counter[payload_id]}"
                    )
                    route_sequence = [curr_det_id]  # current を新クラスタの開始点に
                    prev_record = current_record
                    i += 1
                    continue

            # 正常移動: ルートへ追加
            route_sequence.append(curr_det_id)
            prev_record = current_record
            i += 1

        # 最終クラスタ確定
        if len(route_sequence) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(route_sequence)

    return (
        ClusteredRoutes(routes_by_cluster_id=estimated_clustered_routes),
        payload_records_collection,
    )  # ClusteredRoutes オブジェクトと更新された PayloadRecordsCollection を返す

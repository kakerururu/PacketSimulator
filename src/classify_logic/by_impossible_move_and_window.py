from collections import defaultdict
from typing import Dict, List, Optional
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadEventsCollection,
    ClusteredRoutes,
)


def classify_events_by_impossible_move_and_window(
    payload_events_collection: PayloadEventsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
    max_lookahead: int = 3,
    impossible_factor: float = 0.8,
) -> ClusteredRoutes:
    """
    ありえない移動 (prev -> current が最小移動時間 * impossible_factor 未満) を検知した際、
    直後最大 max_lookahead 個のイベントの中に「prev から物理的に到達可能」なイベントがあるかを探索し、
    あればそのイベントをルートに採用してクラスタ分割を回避する簡易ブリッジ手法を用いる。

    振る舞い概要:
    - 正常移動: 現在イベント検出器IDをシーケンスに追加
    - 不可能移動判定:
        * current はシーケンスに追加せず捨てる
        * lookahead window 内で最初に到達可能なイベント (prev から travel_time 条件を満たす) を探索
        * 見つかれば: そのイベントをシーケンスに追加し prev をそのイベントへ更新 (インデックスをジャンプ)
        * 見つからなければ: そこまでのルートを確定し新クラスタ開始

    戻り値: ClusteredRoutes
    routes_by_cluster_id: {クラスタID: ルート文字列}

    パラメータ:
    - max_lookahead: 不可能移動後に探索する最大イベント数
    - impossible_factor: 不可能移動判定係数 (time_diff < min_travel_time * impossible_factor)

    例:
    {"payload1_cluster1": "ABCD", "payload1_cluster2": "ACE", ...}
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)

    for payload_id, events in payload_events_collection.events_by_payload.items():
        if not events:
            continue

        # 新しいクラスタ開始
        cluster_counter[payload_id] += 1
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        route_sequence: List[str] = [events[0].detector_id]

        prev_event = events[0]
        i = 1  # while でインデックス制御（lookaheadジャンプに対応）

        while i < len(events):
            current_event = events[i]

            prev_det_id = prev_event.detector_id
            curr_det_id = current_event.detector_id

            # 直前と同じ検出器ならスキップ（移動なし）
            if curr_det_id == route_sequence[-1]:
                prev_event = current_event
                i += 1
                continue

            time_diff = (current_event.timestamp - prev_event.timestamp).total_seconds()
            det_prev = detectors[prev_det_id]
            det_curr = detectors[curr_det_id]
            min_travel_time = calculate_min_travel_time(
                det_prev, det_curr, walker_speed
            )

            # 不可能移動判定
            if time_diff < min_travel_time * impossible_factor:
                # lookahead 探索
                look_found_index: Optional[int] = None
                for j in range(i + 1, min(i + 1 + max_lookahead, len(events))):
                    candidate = events[j]
                    candidate_time_diff = (
                        candidate.timestamp - prev_event.timestamp
                    ).total_seconds()
                    det_candidate = detectors[candidate.detector_id]
                    min_t_candidate = calculate_min_travel_time(
                        det_prev, det_candidate, walker_speed
                    )
                    # 到達可能ならそのイベントを採用
                    if candidate_time_diff >= min_t_candidate * impossible_factor:
                        look_found_index = j
                        break

                if look_found_index is not None:
                    # ブリッジ成功: 不可能だった current を無視し、到達可能な candidate を採用
                    candidate_event = events[look_found_index]
                    # 重複検出器防止
                    # ここで、重複する検出器IDを持つイベントをスキップ
                    if candidate_event.detector_id != route_sequence[-1]:
                        route_sequence.append(candidate_event.detector_id)
                    prev_event = candidate_event
                    i = look_found_index + 1  # 採用イベントの次から継続
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
                    prev_event = current_event
                    i += 1
                    continue

            # 正常移動: ルートへ追加
            route_sequence.append(curr_det_id)
            prev_event = current_event
            i += 1

        # 最終クラスタ確定
        if len(route_sequence) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(route_sequence)

    return ClusteredRoutes(routes_by_cluster_id=estimated_clustered_routes)

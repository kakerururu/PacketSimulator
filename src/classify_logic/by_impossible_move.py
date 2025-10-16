from collections import defaultdict
from typing import Dict
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadEventsCollection,
    ClusteredRoutes,  # 新規インポート
)


def classify_events_by_impossible_move(
    payload_events_collection: PayloadEventsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
) -> ClusteredRoutes:
    """
    Hashed_Payloadごとのイベントを分析し、ありえない移動があった場合に新しいクラスタIDを割り当てる。
    戻り値: キーがクラスタID、値が推定ルート文字列の辞書
    例: {"payload1_cluster1": "ABCD", "payload1_cluster2": "ACD", "payload2_cluster1": "BCD"}
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)  # Payloadごとにクラスタ番号を管理

    for (
        payload_id,
        events,
    ) in payload_events_collection.events_by_payload.items():
        # イベントが無いときは以降の処理をスキップして次のPayloadへ
        if not events:
            continue

        current_route_sequence_list: list[str] = []

        cluster_counter[payload_id] += 1
        # クラスタIDの生成、例: "payload1_cluster1"
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        # 最初のイベントの検出器名をsequenceに追加
        current_route_sequence_list.append(events[0].detector_id)

        prev_event = events[0]

        # 一個前のイベントと現在のイベントの比較を最終レコードまでループ
        for i in range(1, len(events)):
            current_event = events[i]

            prev_event_detector_id = prev_event.detector_id
            current_event_detector_id = current_event.detector_id

            if current_event_detector_id == current_route_sequence_list[-1]:
                # シーケンスの最後のイベントと同じ検出器ならスキップ
                # これは移動していないことを意味する
                prev_event = current_event
                continue

            # ここで、前のイベントと現在のイベントの時間差を計算
            time_diff = (current_event.timestamp - prev_event.timestamp).total_seconds()

            det1_obj = detectors[prev_event_detector_id]
            det2_obj = detectors[current_event_detector_id]

            # 前のイベントと現在のイベントの検出器間の最小移動時間を計算
            min_travel_time = calculate_min_travel_time(
                det1_obj, det2_obj, walker_speed
            )

            # 最小移動時間の80%未満で到達している場合はありえない移動と判断し、新しいクラスタを開始
            if time_diff < min_travel_time * 0.8:
                # 現在のクラスタIDのルートをペイロード名+クラスタ番号をキーにして保存
                if len(current_route_sequence_list) > 1:
                    estimated_clustered_routes[current_cluster_id] = "".join(
                        current_route_sequence_list
                    )

                # 新しいクラスタを作成するため、クラスタ番号をインクリメント
                cluster_counter[payload_id] += 1
                # 新しいクラスタIDを生成
                current_cluster_id = (
                    f"{payload_id}_cluster{cluster_counter[payload_id]}"
                )
                # 新しいクラスタのルートシーケンスを初期化し、現在のイベントの検出器名を最初に追加
                current_route_sequence_list = [current_event_detector_id]
                prev_event = current_event
                continue

            # 正常な移動と判断された場合は、現在のイベントの検出器名（AやB）をシーケンスに追加
            current_route_sequence_list.append(current_event_detector_id)

            prev_event = current_event

        #
        if len(current_route_sequence_list) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(
                current_route_sequence_list
            )

    return ClusteredRoutes(
        routes_by_cluster_id=estimated_clustered_routes
    )  # ClusteredRoutes オブジェクトを返す

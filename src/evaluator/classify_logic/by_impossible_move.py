from collections import defaultdict
from typing import Dict
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector
from domain.analysis_results import (
    PayloadRecordsCollection,
    ClusteredRoutes,
)


def classify_records_by_impossible_move(
    payload_records_collection: PayloadRecordsCollection,
    detectors: Dict[str, Detector],
    walker_speed: float,
) -> tuple[ClusteredRoutes, PayloadRecordsCollection]:  # 戻り値の型を変更
    """
    Hashed_Payloadごとのレコードを分析し、ありえない移動があった場合に新しいクラスタIDを割り当てる。
    戻り値: キーがクラスタID、値が推定ルート文字列の辞書
    例: {"payload1_cluster1": "ABCD", "payload1_cluster2": "ACD", "payload2_cluster1": "BCD"}
    """
    estimated_clustered_routes: Dict[str, str] = {}
    cluster_counter = defaultdict(int)  # Payloadごとにクラスタ番号を管理

    for (
        payload_id,
        records,
    ) in payload_records_collection.records_by_payload.items():
        # レコードが無いときは以降の処理をスキップして次のPayloadへ
        if not records:
            continue

        current_route_sequence_list: list[str] = []

        cluster_counter[payload_id] += 1
        # クラスタIDの生成、例: "payload1_cluster1"
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        # 最初のレコードの検出器名をsequenceに追加
        records[0].is_judged = True  # is_judgedをTrueに設定
        current_route_sequence_list.append(records[0].detector_id)

        prev_record = records[0]
        prev_record.is_judged = True  # 最初のprev_recordも判定に使用されるためTrueに

        # 一個前のレコードと現在のレコードの比較を最終レコードまでループ
        for i in range(1, len(records)):
            current_record = records[i]
            current_record.is_judged = True  # 判定に使用されるレコードをTrueに

            prev_record_detector_id = prev_record.detector_id
            current_record_detector_id = current_record.detector_id

            if current_record_detector_id == current_route_sequence_list[-1]:
                # シーケンスの最後のレコードと同じ検出器ならスキップ
                # これは移動していないことを意味する
                prev_record = current_record
                continue

            # ここで、前のレコードと現在のレコードの時間差を計算
            time_diff = (
                current_record.timestamp - prev_record.timestamp
            ).total_seconds()

            det1_obj = detectors[prev_record_detector_id]
            det2_obj = detectors[current_record_detector_id]

            # 前のレコードと現在のレコードの検出器間の最小移動時間を計算
            min_travel_time = calculate_min_travel_time(
                det1_obj, det2_obj, walker_speed
            )

            # 最小移動時間の80%未満で到達している場合はありえない移動と判断し、新しいクラスタを開始
            if time_diff < min_travel_time * 0.8:
                current_record.is_judged = False  # 不可能移動レコードは判定に使用しない
                # 現在のクラスタIDのルートをペイロード名+クラスタ番号をキーにして保存
                if len(current_route_sequence_list) > 1:
                    estimated_clustered_routes[current_cluster_id] = "".join(
                        current_route_sequence_list
                    )

                # ログを出力（デバッグ用）
                print(
                    f"Impossible move detected for payload {payload_id} between detectors {prev_record_detector_id} and {current_record_detector_id}. Time diff: {time_diff:.2f}s, Min travel time: {min_travel_time:.2f}s"
                )
                # 推定されたルートを出力
                print(
                    f"クラスタID {current_cluster_id}:推定ルート {''.join(current_route_sequence_list)}"
                )

                # 新しいクラスタを作成するため、クラスタ番号をインクリメント
                cluster_counter[payload_id] += 1
                # 新しいクラスタIDを生成
                current_cluster_id = (
                    f"{payload_id}_cluster{cluster_counter[payload_id]}"
                )
                # 新しいクラスタのルートシーケンスを初期化し、現在のレコードの検出器名を最初に追加
                current_route_sequence_list = [current_record_detector_id]
                prev_record = current_record
                continue

            # 正常な移動と判断された場合は、現在のレコードの検出器名（AやB）をシーケンスに追加
            current_route_sequence_list.append(current_record_detector_id)

            prev_record = current_record

        #
        if len(current_route_sequence_list) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(
                current_route_sequence_list
            )

    return (
        ClusteredRoutes(routes_by_cluster_id=estimated_clustered_routes),
        payload_records_collection,
    )  # ClusteredRoutes オブジェクトと更新された PayloadRecordsCollection を返す

import numpy as np
from collections import defaultdict
from utils.calculate_function import calculate_min_travel_time
from domain.detector import Detector, load_detectors
from utils.load import load_ground_truth_routes, load_logs, load_simulation_settings

WALKER_SPEED = load_simulation_settings("config/simulation_settings.json")[
    "walker_speed"
]


def analyze_movements_with_clustering(
    logs: list[dict], detectors: dict[str, Detector]
) -> dict[str, str]:
    """
    ログデータからHashed_Payloadごとのイベントを分析し、
    ありえない移動があった場合に新しいクラスタIDを割り当てる。
    """
    # Hashed_Payload ごとのイベントを収集
    payload_events = defaultdict(list)
    for log_entry in logs:
        # Detector_X と Detector_Y から検出器IDを特定
        current_detector_id = None
        for det_id, det_obj in detectors.items():
            if (
                det_obj.x == log_entry["Detector_X"]
                and det_obj.y == log_entry["Detector_Y"]
            ):
                current_detector_id = det_id
                break
        if current_detector_id:
            payload_events[log_entry["Hashed_Payload"]].append(
                {
                    "Timestamp": log_entry["Timestamp"],
                    "Detector_ID": current_detector_id,
                    "Detector_X": log_entry["Detector_X"],
                    "Detector_Y": log_entry["Detector_Y"],
                }
            )

    # 各 Hashed_Payload のイベントを時間でソート
    for payload_id in payload_events:
        payload_events[payload_id].sort(key=lambda x: x["Timestamp"])

    estimated_clustered_routes = {}  # キーは仮想的なクラスタID (例: "payloadX_cluster1")
    cluster_counter = defaultdict(int)  # 各Hashed_Payloadに対するクラスタ番号を管理

    # 各 Hashed_Payload のイベントシーケンスを分析
    for payload_id, events in payload_events.items():
        if not events:
            continue

        current_route_sequence_list = []

        # 最初のイベントで最初のクラスタとルートを開始
        cluster_counter[payload_id] += 1
        current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"
        current_route_sequence_list.append(events[0]["Detector_ID"])

        prev_event = events[0]

        for i in range(1, len(events)):
            current_event = events[i]

            prev_det_id = prev_event["Detector_ID"]
            current_det_id = current_event["Detector_ID"]

            # 同じ検出器での連続した検出は、ルートシーケンスに重複して追加しない
            if current_det_id == current_route_sequence_list[-1]:
                prev_event = current_event
                continue

            # 移動時間のチェック
            time_diff = (
                current_event["Timestamp"] - prev_event["Timestamp"]
            ).total_seconds()

            det1_obj = detectors[prev_det_id]
            det2_obj = detectors[current_det_id]

            min_travel_time = calculate_min_travel_time(
                det1_obj, det2_obj, WALKER_SPEED
            )

            # ありえない移動の場合：現在のルートシーケンスを確定し、新しいクラスタを開始
            # 閾値は min_travel_time * 0.8
            if time_diff < min_travel_time * 0.8:
                # これまでのルートシーケンスを確定して保存
                # ルートが有効（少なくとも2つの異なる検出器を含む）な場合のみ保存
                if len(current_route_sequence_list) > 1:
                    estimated_clustered_routes[current_cluster_id] = "".join(
                        current_route_sequence_list
                    )

                # 新しいクラスタの開始
                cluster_counter[payload_id] += 1
                current_cluster_id = (
                    f"{payload_id}_cluster{cluster_counter[payload_id]}"
                )
                current_route_sequence_list = [
                    current_det_id
                ]  # 新しいルートは現在の検出器から開始
                prev_event = current_event  # 新しいクラスタの最初のイベントとして設定
                continue  # 次のイベントへ

            # 有効な移動として、ルートシーケンスに追加
            current_route_sequence_list.append(current_det_id)
            prev_event = current_event  # 次の比較のためにprev_eventを更新

        # ループ終了後、最後に構築中のルートシーケンスを確定して保存
        if len(current_route_sequence_list) > 1:
            estimated_clustered_routes[current_cluster_id] = "".join(
                current_route_sequence_list
            )

    return estimated_clustered_routes


def evaluate_algorithm(
    estimated_clustered_routes: dict, ground_truth_routes: dict, num_detectors: int
) -> dict:
    """
    アルゴリズムの推定結果をグランドトゥルースと比較して評価する。
    推定されたルートがnum_detectorsの数と一致しない場合は評価対象から除外する。
    """
    true_route_counts = defaultdict(int)
    estimated_route_counts = defaultdict(int)

    # グランドトゥルースから真のルートシーケンスの出現回数をカウント
    # グランドトゥルースは常にnum_detectorsの数の検出器を含むルートを想定
    for walker_id, route_str in ground_truth_routes.items():
        if len(route_str) == num_detectors:  # 真のルートは必ずN個の検出器を経由する前提
            true_route_counts[route_str] += 1

    # 推定されたルートシーケンスの出現回数をカウント
    # ここで、推定されたルートがnum_detectorsの数と一致しない場合は除外
    for cluster_id, route_str in estimated_clustered_routes.items():
        if (
            len(route_str) == num_detectors
        ):  # N個の検出器を経由するルートのみを評価対象とする
            estimated_route_counts[route_str] += 1

    # --- 評価指標の計算 ---
    total_absolute_error = 0
    squared_errors = []
    total_true_route_instances = sum(
        true_route_counts.values()
    )  # 評価対象となる真のルートインスタンスの合計
    num_unique_routes_evaluated = 0

    # 全てのユニークなルートシーケンスを網羅（評価対象のもののみ）
    all_unique_routes = set(true_route_counts.keys()) | set(
        estimated_route_counts.keys()
    )

    results_details = []

    for route_str in sorted(list(all_unique_routes)):
        true_count = true_route_counts.get(route_str, 0)
        estimated_count = estimated_route_counts.get(route_str, 0)

        # Absolute Error
        error = estimated_count - true_count
        abs_error = abs(error)
        total_absolute_error += abs_error
        squared_errors.append(error**2)
        num_unique_routes_evaluated += 1

        results_details.append(
            {
                "Route": route_str,
                "TrueCount": true_count,
                "EstimatedCount": estimated_count,
                "AbsoluteError": abs_error,
            }
        )

    # MAEはユニークなルート数で割る
    mae_per_route = (
        total_absolute_error / num_unique_routes_evaluated
        if num_unique_routes_evaluated > 0
        else 0
    )

    # RMSEの計算
    mse = np.mean(squared_errors) if squared_errors else 0
    rmse = np.sqrt(mse)

    # 追跡率 (Tracking Rate) の計算
    # 全ての真の通行人のうち、ルートが正しく推定された通行人の割合
    # 計算式: Σ min(各ルートの真の人数, 各ルートの推定人数) / (全ウォーカーの総数)
    # 例: 真が5人/推定4人なら4人、真が2人/推定3人なら2人が追跡成功とカウントされる
    correctly_tracked_walkers = sum(
        min(true_route_counts.get(route, 0), estimated_route_counts.get(route, 0))
        for route in all_unique_routes
    )
    tracking_rate = (
        correctly_tracked_walkers / total_true_route_instances
        if total_true_route_instances > 0
        else 0
    )

    return {
        "summary": {
            "TotalUniqueRoutesEvaluated": num_unique_routes_evaluated,
            "TotalTrueRouteInstances": total_true_route_instances,
            "TotalEstimatedRouteInstances": sum(estimated_route_counts.values()),
            "MAE_PerUniqueRoute": mae_per_route,
            "RMSE": f"{rmse:.4f}",
            "TrackingRate": f"{tracking_rate:.4f}",  # 追跡率を追加
        },
        "details": results_details,
    }


def main():
    # データの読み込み
    detectors = load_detectors("config/detectors.json")
    logs = load_logs("result")
    ground_truth_routes = load_ground_truth_routes("result/walker_routes.csv")

    # 移動経路の推定とありえない移動の排除、およびクラスタリング
    estimated_clustered_routes = analyze_movements_with_clustering(logs, detectors)

    print("\n--- 推定結果 (クラスタリング後の推定ルート) ---")
    # クラスタIDごとのルートを出力
    for cluster_id, route_str in sorted(estimated_clustered_routes.items()):
        print(f"クラスタID: {cluster_id}, 推定ルート: {route_str}")
    print(
        f"推定されたユニークな人物（クラスタ）の総数: {len(estimated_clustered_routes)}"
    )
    print("-" * 30)

    # アルゴリズムの評価
    evaluation_results = evaluate_algorithm(
        estimated_clustered_routes, ground_truth_routes, len(detectors)
    )

    print("\n--- 評価結果サマリー (ルートシーケンスごとのカウント) ---")
    for key, value in evaluation_results["summary"].items():
        print(f"{key}: {value}")
    print("\n--- 評価結果詳細 (ユニークなルートシーケンス) ---")
    print(
        "{:<15} {:>10} {:>15} {:>15}".format("ルート", "真の数", "推定数", "絶対誤差")
    )
    print("-" * 60)
    for detail in evaluation_results["details"]:
        print(
            "{:<15} {:>10} {:>15} {:>15}".format(
                detail["Route"],
                detail["TrueCount"],
                detail["EstimatedCount"],
                detail["AbsoluteError"],
            )
        )
    print("-" * 60)


if __name__ == "__main__":
    main()

import json
import csv
import math
from datetime import datetime, timedelta
from collections import defaultdict
import os

# 定数（main.ipynbから引用）
WALKER_SPEED = 1.4  # 通行人の移動速度（m/s）

# --- クラスタリングロジック用の定数 ---
# ペイロードが「ありえない移動」をしたと判断する閾値 (最小移動時間の何%未満か)
TRAVEL_TIME_THRESHOLD_FACTOR = 0.8
# CLUSTER_WINDOW_SECONDS は、このバージョンでは使用しないが、変数として残す
# 今後の拡張のために、設定ファイルなどで管理することも検討可能
CLUSTER_WINDOW_SECONDS = 300  # 5分


class Detector:
    def __init__(self, id: str, float_x: float, float_y: float):
        self.id = id
        self.x = float_x
        self.y = float_y


def load_detectors(file_path: str) -> dict[str, Detector]:
    """JSONファイルから検知器情報をロードし、IDをキーとする辞書で返す"""
    with open(file_path, "r") as file:
        data = json.load(file)
        return {d["id"]: Detector(d["id"], d["x"], d["y"]) for d in data["detectors"]}


def load_logs(log_dir: str) -> list[dict]:
    """
    指定されたディレクトリからすべてのログファイルを読み込み、結合する。
    """
    all_logs = []
    for filename in os.listdir(log_dir):
        if filename.endswith("_log.csv"):
            filepath = os.path.join(log_dir, filename)
            with open(filepath, "r") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    timestamp_key = "Timestamp"
                    if "zTimestamp" in row:
                        timestamp_key = "zTimestamp"

                    try:
                        row["Timestamp"] = datetime.strptime(
                            row[timestamp_key], "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        row["Timestamp"] = datetime.strptime(
                            row[timestamp_key], "%Y-%m-%d %H:%M:%S.%f"
                        )

                    row["Detector_X"] = float(row["Detector_X"])
                    row["Detector_Y"] = float(row["Detector_Y"])
                    all_logs.append(row)
    all_logs.sort(key=lambda x: x["Timestamp"])
    return all_logs


def calculate_min_travel_time(det1: Detector, det2: Detector, speed: float) -> float:
    """検知器AからBへの最小移動時間を計算（ばらつきなし）"""
    distance = math.sqrt((det2.x - det1.x) ** 2 + (det2.y - det1.y) ** 2)
    return distance / speed if speed > 0 else 0


def load_ground_truth_routes(file_path: str) -> dict[str, str]:
    """
    グランドトゥルースのウォーカールートを読み込む。
    User_ID (Walker_ID) と真のRouteの対応。
    """
    ground_truth = {}
    with open(file_path, "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            ground_truth[row["Walker_ID"]] = row["Route"]
    return ground_truth


def analyze_movements_with_clustering(
    logs: list[dict], detectors: dict[str, Detector]
) -> dict[str, str]:
    """
    ログデータからHashed_Payloadごとのイベントを分析し、
    物理的にありえない移動があった場合に新しいクラスタIDを割り当てる（即座に分割）。
    """
    payload_events = defaultdict(list)
    for log_entry in logs:
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

        prev_event = events[0]  # 直前の有効なイベント

        for i in range(1, len(events)):
            current_event = events[i]

            prev_det_id = prev_event["Detector_ID"]
            current_det_id_for_check = current_event["Detector_ID"]

            # 同じ検出器での連続した検出は、ルートシーケンスに重複して追加しない
            if current_det_id_for_check == current_route_sequence_list[-1]:
                prev_event = current_event
                continue

            # 移動時間のチェック
            time_diff = (
                current_event["Timestamp"] - prev_event["Timestamp"]
            ).total_seconds()

            det1_obj = detectors[prev_det_id]
            det2_obj = detectors[current_det_id_for_check]

            min_travel_time = calculate_min_travel_time(
                det1_obj, det2_obj, WALKER_SPEED
            )

            # ありえない移動の場合：現在のルートシーケンスを確定し、新しいクラスタを開始
            # 閾値は min_travel_time * TRAVEL_TIME_THRESHOLD_FACTOR
            if time_diff < min_travel_time * TRAVEL_TIME_THRESHOLD_FACTOR:
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
                    current_det_id_for_check
                ]  # 新しいルートは現在の検出器から開始
                prev_event = current_event  # 新しいクラスタの最初のイベントとして設定
                continue  # 次のイベントへ

            # 有効な移動として、ルートシーケンスに追加
            current_route_sequence_list.append(current_det_id_for_check)
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
    total_squared_error = 0  # RMSE計算用
    total_true_route_instances = sum(
        true_route_counts.values()
    )  # 評価対象となる真のルートインスタンスの合計
    num_unique_routes_evaluated = 0

    # 全てのユニークなルートシーケンスを網羅（評価対象のもののみ）
    all_unique_routes = set(true_route_counts.keys()) | set(
        estimated_route_counts.keys()
    )

    # Precision, Recall, F1-score, Accuracy 計算用の変数 (参考として残す)
    TP = 0
    FP = 0
    FN = 0

    results_details = []

    for route_str in sorted(list(all_unique_routes)):
        true_count = true_route_counts[route_str]
        estimated_count = estimated_route_counts[route_str]

        # Absolute Error
        abs_error = abs(estimated_count - true_count)
        total_absolute_error += abs_error

        # Squared Error (RMSE用)
        total_squared_error += (estimated_count - true_count) ** 2

        num_unique_routes_evaluated += 1

        # TP, FP, FN の計算 (参考として)
        TP_current = min(true_count, estimated_count)
        TP += TP_current

        FP_current = max(0, estimated_count - true_count)
        FP += FP_current

        FN_current = max(0, true_count - estimated_count)
        FN += FN_current

        results_details.append(
            {
                "Route": route_str,
                "TrueCount": true_count,
                "EstimatedCount": estimated_count,
                "AbsoluteError": abs_error,
                "TP_current": TP_current,
                "FP_current": FP_current,
                "FN_current": FN_current,
            }
        )

    # MAE (Mean Absolute Error)
    mae_per_route = (
        total_absolute_error / num_unique_routes_evaluated
        if num_unique_routes_evaluated > 0
        else 0
    )

    # RMSE (Root Mean Squared Error)
    rmse_per_route = (
        math.sqrt(total_squared_error / num_unique_routes_evaluated)
        if num_unique_routes_evaluated > 0
        else 0
    )

    # Percentage Error (以前の Total Percentage Error)
    total_percentage_error = (
        (total_absolute_error / total_true_route_instances) * 100
        if total_true_route_instances > 0
        else 0
    )

    # Precision, Recall, F1-score, Accuracy の計算 (参考として)
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    f1_score = (
        2 * (precision * recall) / (precision + recall)
        if (precision + recall) > 0
        else 0
    )
    accuracy = TP / total_true_route_instances if total_true_route_instances > 0 else 0

    return {
        "summary": {
            "TotalUniqueRoutesEvaluated": num_unique_routes_evaluated,
            "TotalTrueRouteInstances": total_true_route_instances,
            "TotalEstimatedRouteInstances": sum(estimated_route_counts.values()),
            "TotalAbsoluteError": total_absolute_error,
            "MAE_PerUniqueRoute": mae_per_route,
            "RMSE_PerUniqueRoute": rmse_per_route,  # RMSEを追加
            "TotalPercentageError": f"{total_percentage_error:.2f}%",
            "Precision": f"{precision:.4f}",  # 参考として残す
            "Recall": f"{recall:.4f}",  # 参考として残す
            "F1_Score": f"{f1_score:.4f}",  # 参考として残す
            "Accuracy": f"{accuracy:.4f}",  # 参考として残す
            "Total_TP": TP,
            "Total_FP": FP,
            "Total_FN": FN,
        },
        "details": results_details,
    }


def main():
    detector_config_path = "src/config/detectors.json"
    log_dir = "src/result"
    ground_truth_path = "src/result/walker_routes.csv"

    # データの読み込み
    detectors = load_detectors(detector_config_path)
    logs = load_logs(log_dir)
    ground_truth_routes = load_ground_truth_routes(ground_truth_path)

    # 検出器の総数を取得 (N)
    num_detectors = len(detectors)

    print("--- データ読み込み完了 ---")
    print(f"検出器数 (N): {num_detectors}")
    print(f"ログエントリ数: {len(logs)}")
    print(f"グランドトゥルースのウォーカー数: {len(ground_truth_routes)}")
    print("-" * 30)

    # 移動経路の推定とありえない移動の排除、およびクラスタリング
    # ウィンドウロジックは削除し、以前の「ありえない移動で即時分割」ロジックに戻す
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
        estimated_clustered_routes, ground_truth_routes, num_detectors
    )

    print("\n--- 評価結果サマリー ---")
    # 人数推定の誤差指標を前面に
    print(
        f"平均絶対誤差（ルートあたり人数） (MAE): {evaluation_results['summary']['MAE_PerUniqueRoute']:.4f}"
    )
    print(
        f"二乗平均平方根誤差（ルートあたり人数） (RMSE): {evaluation_results['summary']['RMSE_PerUniqueRoute']:.4f}"
    )
    print(
        f"総絶対誤差の割合 (Total Percentage Error): {evaluation_results['summary']['TotalPercentageError']}"
    )
    # print("\n--- 分類性能指標 (参考) ---")
    # print(f"正解率 (Accuracy): {evaluation_results['summary']['Accuracy']}")
    # print(f"適合率 (Precision): {evaluation_results['summary']['Precision']}")
    # print(f"再現率 (Recall): {evaluation_results['summary']['Recall']}")
    # print(f"F1スコア (F1_Score): {evaluation_results['summary']['F1_Score']}")
    # print("\n--- 評価カウントサマリー ---")
    # print(
    #     f"合計正しく推定されたインスタンス (TP): {evaluation_results['summary']['Total_TP']}"
    # )
    # print(
    #     f"合計誤って推定されたインスタンス (FP): {evaluation_results['summary']['Total_FP']}"
    # )
    # print(
    #     f"合計見落とされたインスタンス (FN): {evaluation_results['summary']['Total_FN']}"
    # )

    print("\n--- 評価結果詳細 (ユニークなルートシーケンス) ---")
    print(
        "{:<15} {:>10} {:>15} {:>15} {:>7} {:>7} {:>7}".format(
            "ルート", "真の数", "推定数", "絶対誤差", "TP", "FP", "FN"
        )
    )
    print("-" * 75)
    for detail in evaluation_results["details"]:
        print(
            "{:<15} {:>10} {:>15} {:>15} {:>7} {:>7} {:>7}".format(
                detail["Route"],
                detail["TrueCount"],
                detail["EstimatedCount"],
                detail["AbsoluteError"],
                detail["TP_current"],
                detail["FP_current"],
                detail["FN_current"],
            )
        )
    print("-" * 75)


if __name__ == "__main__":
    main()

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
# CLUSTER_WINDOW_SECONDS は、このロジックでは使用しないが、変数として残す
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
    物理的にありえない移動があった場合、一つ先のイベントを見て結合を試みる（簡易ウィンドウロジック）。
    見つからない場合はクラスタを分割。
    """
    estimated_clustered_routes = {}
    cluster_counter = defaultdict(int)

    # Hashed_Payload ごとにイベントを収集し、ソート
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

    print(f"\n--- クラスタリング開始: 各ペイロードIDのイベントを処理 ---")

    for payload_id, events in payload_events.items():
        if not events:
            print(f"  ペイロードID: {payload_id} - イベントなし。スキップ。")
            continue

        print(f"\n  ペイロードID: {payload_id} のイベント処理開始 ({len(events)}個)")

        # このペイロードのイベントリストで、既に処理済みのイベントのインデックスを追跡するセット
        processed_event_indices = set()

        # 現在処理中のイベントリストのインデックス (新しいクラスタの開始点候補)
        current_event_idx = 0

        while current_event_idx < len(events):
            # もし現在のイベントが既に何らかのクラスタに割り当て済みであれば、スキップして次へ
            if current_event_idx in processed_event_indices:
                current_event_idx += 1
                print(
                    f"    インデックス {current_event_idx - 1} (イベント {events[current_event_idx - 1]['Detector_ID']}) は既に処理済み。次へスキップ。"
                )
                continue

            # 新しいクラスタの開始
            cluster_counter[payload_id] += 1
            current_cluster_id = f"{payload_id}_cluster{cluster_counter[payload_id]}"

            # このクラスタの最初のイベント
            start_event_for_cluster = events[current_event_idx]
            current_route_sequence_list = [start_event_for_cluster["Detector_ID"]]
            processed_event_indices.add(
                current_event_idx
            )  # クラスタの開始イベントを処理済みとしてマーク

            last_valid_event_in_cluster = (
                start_event_for_cluster  # このクラスタで最後に確定された有効なイベント
            )

            print(
                f"    新しいクラスタ {current_cluster_id} 開始。開始イベント: {start_event_for_cluster['Detector_ID']} @ {start_event_for_cluster['Timestamp']}"
            )
            print(f"      初期ルート: {''.join(current_route_sequence_list)}")

            # 内側のループで現在のクラスタのルートを構築
            # search_from_idx は current_event_idx の次のイベントから開始
            search_from_idx = current_event_idx + 1

            while search_from_idx < len(events):
                candidate_event = events[search_from_idx]

                # この候補イベントが既に処理済みであればスキップ（他のクラスタに割り当て済み）
                if search_from_idx in processed_event_indices:
                    search_from_idx += 1  # 次のイベントへ
                    continue

                # 同じ検出器での連続検出は、ルートシーケンスに重複して追加しないが、last_valid_eventは更新する
                if candidate_event["Detector_ID"] == current_route_sequence_list[-1]:
                    print(
                        f"        候補 {search_from_idx} ({candidate_event['Detector_ID']}) @ {candidate_event['Timestamp']} は同じ検出器。last_valid_eventを更新。"
                    )
                    last_valid_event_in_cluster = candidate_event
                    processed_event_indices.add(
                        search_from_idx
                    )  # 同じ検出器でも処理済みとしてマーク
                    search_from_idx += 1
                    continue

                # last_valid_event_in_cluster から candidate_event への移動を評価
                time_diff = (
                    candidate_event["Timestamp"]
                    - last_valid_event_in_cluster["Timestamp"]
                ).total_seconds()

                det1_obj = detectors[last_valid_event_in_cluster["Detector_ID"]]
                det2_obj = detectors[candidate_event["Detector_ID"]]

                min_travel_time = calculate_min_travel_time(
                    det1_obj, det2_obj, WALKER_SPEED
                )

                is_impossible_move = (
                    time_diff < min_travel_time * TRAVEL_TIME_THRESHOLD_FACTOR
                )

                if is_impossible_move:
                    # 「ありえない移動」の場合：一つ先のイベントを見て結合を試みる
                    print(
                        f"        ありえない移動 ({last_valid_event_in_cluster['Detector_ID']}->{candidate_event['Detector_ID']}) @ {candidate_event['Timestamp']} を検出。一つ先を確認。"
                    )
                    found_valid_skip_connection = False

                    if search_from_idx + 1 < len(
                        events
                    ):  # E_next (一つ先のイベント) が存在するか
                        next_event_after_candidate = events[search_from_idx + 1]

                        # next_event_after_candidate が既に処理済みであればスキップ判定は適用しない
                        if (search_from_idx + 1) in processed_event_indices:
                            print(
                                f"          次候補 {search_from_idx + 1} ({next_event_after_candidate['Detector_ID']}) は既に処理済み。スキップ判定できず。"
                            )
                            found_valid_skip_connection = False
                        else:
                            # last_valid_event_in_cluster から next_event_after_candidate への移動が物理的に可能かチェック
                            time_diff_to_next_event = (
                                next_event_after_candidate["Timestamp"]
                                - last_valid_event_in_cluster["Timestamp"]
                            ).total_seconds()
                            det_next_obj = detectors[
                                next_event_after_candidate["Detector_ID"]
                            ]
                            min_travel_time_to_next_event = calculate_min_travel_time(
                                det1_obj, det_next_obj, WALKER_SPEED
                            )

                            if (
                                time_diff_to_next_event
                                >= min_travel_time_to_next_event
                                * TRAVEL_TIME_THRESHOLD_FACTOR
                            ):
                                # E_prev_valid から E_next が繋がる！E_current はノイズと判断しスキップ
                                found_valid_skip_connection = True
                                print(
                                    f"          ありえない移動 ({candidate_event['Detector_ID']}) をスキップし、{next_event_after_candidate['Detector_ID']} へ接続。"
                                )
                            else:
                                print(
                                    f"          E_prev_valid から E_next ({next_event_after_candidate['Detector_ID']}) もありえない移動。スキップできず。"
                                )
                                found_valid_skip_connection = False
                    else:
                        print(f"        E_next が存在しないため、スキップできず。")
                        found_valid_skip_connection = (
                            False  # E_next がなければスキップはできない
                        )

                    if found_valid_skip_connection:
                        # E_current をスキップし、E_next をルートに追加
                        current_route_sequence_list.append(
                            next_event_after_candidate["Detector_ID"]
                        )
                        # スキップされたイベント (candidate_event) と接続に使用したイベント (next_event_after_candidate) を処理済みとしてマーク
                        processed_event_indices.add(
                            search_from_idx
                        )  # candidate_event (スキップされたノイズ)
                        processed_event_indices.add(
                            search_from_idx + 1
                        )  # next_event_after_candidate (接続点)

                        last_valid_event_in_cluster = next_event_after_candidate
                        search_from_idx += 2  # candidate_event と next_event_after_candidate の両方を飛ばして次へ
                        print(
                            f"      ルート延長 (スキップ経由): {''.join(current_route_sequence_list)}"
                        )
                        print(f"      search_from_idx 更新: {search_from_idx}")
                        continue  # このループの残りはスキップし、次の candidate_event を評価

                    else:
                        # 「ありえない移動」だが、スキップして繋げることもできなかった場合
                        # このクラスタはここで終了し、candidate_event は新しいクラスタの開始点となる
                        print(
                            f"      ありえない移動 ({candidate_event['Detector_ID']}) でクラスタ分割。現在のクラスタを終了。"
                        )
                        break  # 内側の while ループを抜けて、現在のクラスタを確定

                else:  # is_impossible_move is False, meaning current move IS physically possible
                    # そのままルートに追加
                    current_route_sequence_list.append(candidate_event["Detector_ID"])
                    processed_event_indices.add(search_from_idx)  # 処理済みとしてマーク

                    last_valid_event_in_cluster = candidate_event
                    search_from_idx += 1
                    print(
                        f"      ルート延長 (通常): {''.join(current_route_sequence_list)}"
                    )
                    print(f"      search_from_idx 更新: {search_from_idx}")

            # 現在構築中のルートシーケンスを確定して保存
            if len(current_route_sequence_list) > 1:
                estimated_clustered_routes[current_cluster_id] = "".join(
                    current_route_sequence_list
                )
                print(
                    f"    クラスタ {current_cluster_id} ルート確定: {''.join(current_route_sequence_list)}"
                )
            else:
                print(f"    クラスタ {current_cluster_id} ルートは短いため保存せず。")

            # 外側ループの current_event_idx を更新
            # 次の処理は、processed_event_indices に含まれない、最もインデックスの小さいイベントから開始
            next_unprocessed_idx = -1
            # range(current_event_idx + 1, len(events)) からではなく、0から全てを走査し直すことで、
            # 完全に網羅的に「次の未処理イベント」を見つける
            for idx_check in range(len(events)):  # 全てのイベントを走査
                if idx_check not in processed_event_indices:
                    next_unprocessed_idx = idx_check
                    break

            if next_unprocessed_idx != -1:
                current_event_idx = next_unprocessed_idx
                print(f"    次のクラスタ開始点候補インデックス: {current_event_idx}")
            else:
                # すべてのイベントが処理済みであれば、このペイロードの処理を終了
                print(f"    ペイロードID: {payload_id} のイベント処理完了。")
                break

    print(f"\n--- クラスタリング完了 ---")
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
    # ウィンドウロジック導入（一つ先を見る簡易版）
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
    # シンプルな正答率とエラー率のみを表示
    print(f"正解率 (Accuracy): {evaluation_results['summary']['Accuracy']}")
    print(
        f"間違っている率 (Total Percentage Error): {evaluation_results['summary']['TotalPercentageError']}"
    )
    # 詳細な情報も簡潔に表示
    print(
        f"合計正しく推定されたインスタンス (TP): {evaluation_results['summary']['Total_TP']}"
    )
    print(
        f"合計誤って推定されたインスタンス (FP): {evaluation_results['summary']['Total_FP']}"
    )
    print(
        f"合計見落とされたインスタンス (FN): {evaluation_results['summary']['Total_FN']}"
    )

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

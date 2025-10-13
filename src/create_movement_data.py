import json
import csv
import math
import random
from datetime import datetime, timedelta
import os
from collections import defaultdict

from domain.detector import Detector, load_detectors
from utils.calculate_function import calculate_travel_time


# --- 設定ファイルの読み込み関数を追加 ---
def load_simulation_settings(file_path: str) -> dict:
    """JSONファイルからシミュレーション設定をロードする"""
    with open(file_path, "r") as file:
        data = json.load(file)
        return data["simulation_settings"]


def load_payloads(file_path: str) -> tuple[dict, list, list]:
    """
    ペイロード設定をロードし、モデルごとの全体確率も読み込む。
    動的生成ペイロードを持つモデルも認識する。
    戻り値: (ペイロード分布辞書, モデル名リスト, モデル確率リスト)
    """
    with open(file_path, "r") as f:
        data = json.load(f)

    payload_distributions = {}  # 静的に定義されたペイロード分布を保持
    model_names = []
    overall_probabilities = []

    # モデルの定義を解析し、動的/静的ペイロードの情報を保持
    for model_name, model_data in data["models"].items():
        model_names.append(model_name)
        overall_probabilities.append(model_data["overall_probability"])

        # dynamic_unique_payload フラグを持つモデルは、payload_distributionを持たない
        if (
            "dynamic_unique_payload" in model_data
            and model_data["dynamic_unique_payload"]
        ):
            payload_distributions[model_name] = {"dynamic_unique_payload": True}
        else:
            payload_distributions[model_name] = model_data["payload_distribution"]

    # 確率の合計が1.0であることを確認（または正規化）
    total_prob = sum(overall_probabilities)
    if not math.isclose(total_prob, 1.0, rel_tol=1e-9):  # 浮動小数点誤差を考慮
        print(
            f"Warning: Overall probabilities in {file_path} do not sum to 1.0 ({total_prob}). Normalizing."
        )
        overall_probabilities = [p / total_prob for p in overall_probabilities]

    return payload_distributions, model_names, overall_probabilities


# --- シミュレーション用データの生成 ---
def generate_routes(detectors: dict[str, Detector], num_walkers: int) -> dict[str, str]:
    """
    指定された検出器のリストと通行人の数に基づいて、各通行人のランダムな移動ルートを生成します。
    すべてのウォーカーがすべての検出器を1回ずつ通る、ランダムな順序のルートを生成。
    """
    detector_ids = list(detectors.keys())
    walker_routes = {}
    for i in range(num_walkers):
        route = list(detector_ids)  # 検出器IDのリストをコピー
        random.shuffle(route)  # 順序をランダムにシャッフル
        walker_routes[f"Walker_{i + 1}"] = "".join(
            route
        )  # ルートを文字列として保存 (例: "BACD")
    return walker_routes


def assign_models_to_walkers(
    num_walkers: int,
    model_names: list[str],
    model_probabilities: list[float],
    payload_definitions: dict,
) -> dict[str, dict]:
    """
    各ウォーカーに、指定された確率分布に基づいてスマートフォンモデルを割り当て、
    必要であればユニークなペイロードIDを生成します。
    戻り値: { "Walker_ID": {"model": "Model_Name", "assigned_payload_id": "UniquePayloadString_if_dynamic"} }
    """
    walker_details = {}

    for i in range(num_walkers):
        walker_id = f"Walker_{i + 1}"
        # 重み付きランダム選択でモデルを割り当て
        assigned_model_name = random.choices(
            model_names, weights=model_probabilities, k=1
        )[0]

        assigned_payload_id = None
        # もし割り当てられたモデルが動的にユニークなペイロードを生成するタイプなら
        if (
            "dynamic_unique_payload" in payload_definitions[assigned_model_name]
            and payload_definitions[assigned_model_name]["dynamic_unique_payload"]
        ):
            assigned_payload_id = f"DynamicUniquePayload_Walker_{walker_id}"

        walker_details[walker_id] = {
            "model": assigned_model_name,
            "assigned_payload_id": assigned_payload_id,  # 動的ペイロードのID、静的モデルの場合はNone
        }
    return walker_details


def choose_payload_for_model(
    model_name: str, assigned_payload_id: str | None, payload_distributions: dict
) -> str:
    """
    指定されたモデルの確率分布に基づいて、ペイロードをランダムに選択します。
    動的ペイロードの場合は、割り当てられたIDをそのまま返します。
    """
    if assigned_payload_id:  # このウォーカーに動的ペイロードが割り当てられている場合
        return assigned_payload_id

    # 静的に定義されたペイロード分布から選択
    distribution = payload_distributions.get(model_name)
    if not distribution:
        raise ValueError(f"Payload distribution for model '{model_name}' not found.")

    payload_types = list(distribution.keys())
    probabilities = list(distribution.values())

    chosen_payload = random.choices(payload_types, weights=probabilities, k=1)[0]
    return chosen_payload


# --- シミュレーションの実行 ---
def simulate(
    detectors: dict[str, Detector],
    walker_routes: dict[str, str],
    walker_details: dict[str, dict],
    payload_distributions: dict,
    payloads_per_detector: int,
    walker_speed: float,
    variation_factor: float,
):
    """
    スマートフォンの検出シミュレーションを実行し、ログファイルを生成します。
    """
    results_dir = "result"
    os.makedirs(results_dir, exist_ok=True)

    # 既存のログファイルを削除
    for filename in os.listdir(results_dir):
        if filename.endswith("_log.csv") or filename == "walker_routes.csv":
            os.remove(os.path.join(results_dir, filename))

    # ウォーカールートをCSVファイルに保存
    with open(os.path.join(results_dir, "walker_routes.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["Walker_ID", "Route", "Model", "Assigned_Hashed_Payload_If_Dynamic"]
        )  # 新しい列を追加
        for walker_id, details in walker_details.items():
            route_str = walker_routes[walker_id]
            # 動的ペイロードの場合、そのIDを記録
            assigned_payload_info = (
                details["assigned_payload_id"]
                if details["assigned_payload_id"]
                else "N/A"
            )
            writer.writerow(
                [walker_id, route_str, details["model"], assigned_payload_info]
            )

    # 検出器ごとのログデータを一時的に保持
    detector_logs = defaultdict(list)

    # シミュレーション開始時刻
    start_time = datetime(2024, 1, 14, 11, 0, 0)

    for walker_id, details in walker_details.items():
        current_time = start_time
        assigned_model_name = details["model"]
        assigned_payload_id_for_walker = details[
            "assigned_payload_id"
        ]  # 動的に割り当てられたペイロードID (グループA用)

        route_str = walker_routes[walker_id]
        route_detectors = [detectors[d_id] for d_id in route_str]

        for i in range(len(route_detectors)):
            current_detector = route_detectors[i]

            # 検出器に到達した際のイベントを生成（ペイロード放出数を変数で制御）
            for _ in range(payloads_per_detector):
                # ランダムなオフセット（最大5分 = 300秒）
                offset_seconds = random.randint(0, 300)
                event_time = current_time + timedelta(seconds=offset_seconds)

                # ペイロードをランダムに選択（動的ペイロードの場合はそれを優先）
                chosen_payload = choose_payload_for_model(
                    assigned_model_name,
                    assigned_payload_id_for_walker,
                    payload_distributions,
                )

                # ログエントリを記録
                detector_logs[current_detector.id].append(
                    {
                        "Timestamp": event_time,
                        "Walker_ID": walker_id,
                        "Hashed_Payload": chosen_payload,
                        "Detector_ID": current_detector.id,
                        "Detector_X": current_detector.x,
                        "Detector_Y": current_detector.y,
                    }
                )

            # 次の検出器への移動
            if i < len(route_detectors) - 1:
                next_detector = route_detectors[i + 1]
                travel_duration = calculate_travel_time(
                    current_detector.x,
                    current_detector.y,
                    next_detector.x,
                    next_detector.y,
                    walker_speed,
                    variation_factor,  # パラメータとして受け取った値を使用
                )
                current_time += timedelta(
                    seconds=travel_duration
                )  # 次の検出器への移動時間を加算
            else:
                # 最終検出器で少し滞在する時間を追加 (次のウォーカーの開始に影響しないよう)
                current_time += timedelta(minutes=random.randint(1, 5))

    # 各検出器のログをファイルに書き出し、タイムスタンプでソート
    for det_id, logs in detector_logs.items():
        logs.sort(key=lambda x: x["Timestamp"])  # 各検出器内のログをソート
        file_path = os.path.join(results_dir, f"{det_id}_log.csv")
        with open(file_path, "w", newline="") as f:
            fieldnames = [
                "Timestamp",
                "Walker_ID",
                "Hashed_Payload",
                "Detector_ID",
                "Detector_X",
                "Detector_Y",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in logs:
                # タイムスタンプは文字列形式で書き出す
                entry["Timestamp"] = entry["Timestamp"].strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )[:-3]  # ミリ秒を3桁に
                writer.writerow(entry)

    print(f"シミュレーションログを '{results_dir}' フォルダに生成しました。")


# --- メイン実行部分 ---
def main():
    detector_config_path = "src/config/detectors.json"
    payloads_config_path = "src/config/payloads.json"
    simulation_settings_path = (
        "src/config/simulation_settings.json"  # 新しい設定ファイル
    )

    # 設定データの読み込み
    detectors = load_detectors(detector_config_path)
    payload_distributions, model_names, model_probabilities = load_payloads(
        payloads_config_path
    )
    simulation_settings = load_simulation_settings(
        simulation_settings_path
    )  # 設定を読み込む

    # 設定値を変数に格納
    num_walkers_to_simulate = simulation_settings["num_walkers_to_simulate"]
    payloads_per_detector_per_walker = simulation_settings[
        "payloads_per_detector_per_walker"
    ]
    walker_speed = simulation_settings["walker_speed"]
    variation_factor = simulation_settings["variation_factor"]

    print(f"検出器数: {len(detectors)}")
    print(
        f"利用可能なモデル: {model_names} (確率: {[f'{p:.2f}' for p in model_probabilities]})"
    )
    print(f"シミュレートするウォーカー数: {num_walkers_to_simulate}人")
    print(
        f"各検出器でウォーカーあたりに放出されるペイロード数: {payloads_per_detector_per_walker}個"
    )
    print(f"ウォーカーの移動速度: {walker_speed} m/s")
    print(f"移動時間のばらつき要因: {variation_factor}")

    # ウォーカーごとのルートとモデルを生成
    walker_routes = generate_routes(detectors, num_walkers_to_simulate)
    walker_details = assign_models_to_walkers(
        num_walkers_to_simulate, model_names, model_probabilities, payload_distributions
    )

    # シミュレーション実行
    simulate(
        detectors,
        walker_routes,
        walker_details,
        payload_distributions,
        payloads_per_detector_per_walker,
        walker_speed,
        variation_factor,
    )


if __name__ == "__main__":
    main()

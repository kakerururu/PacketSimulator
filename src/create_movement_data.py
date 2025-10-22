import csv
import random
from datetime import datetime, timedelta
import os
from collections import defaultdict
from domain.detector import Detector, load_detectors
from domain.simulation_entities import Walker, DetectionEvent
from utils.calculate_function import calculate_travel_time
from utils.load import load_payloads, load_simulation_settings


# --- シミュレーション用データの生成 ---
def generate_random_route_string(detectors: dict[str, Detector]) -> str:
    """
    指定された検出器のリストに基づいて、ランダムな順序のルート文字列を生成します。

    例：ABCDという計4つの検知器を持つ場合、"ACBD"や"DBCA"などのランダムな順序の文字列を返します。
    """
    detector_ids = list(detectors.keys())
    random.shuffle(detector_ids)
    return "".join(detector_ids)


def create_walkers(
    num_walkers: int,
    detectors: dict[str, Detector],
    model_names: list[str],
    model_probabilities: list[float],
    payload_definitions: dict,
) -> dict[str, Walker]:
    """
    指定された数と設定に基づいて、Walkerオブジェクトの辞書を生成します。
    各ウォーカーにランダムなルートとスマートフォンモデルを割り当てます。
    返される辞書のキーはウォーカーID、値は対応するWalkerオブジェクトです。

    例：{"Walker_1": Walker(...), "Walker_2": Walker(...)}
    """
    walkers = {}
    for i in range(num_walkers):
        walker_id = f"Walker_{i + 1}"  # ウォーカーIDを生成 1から始まる連番

        # 重み付きランダム選択でモデルを割り当て
        # モデル名のリストとその選択確率のリストを受け取り、1つ選択
        assigned_model_name = random.choices(
            model_names, weights=model_probabilities, k=1
        )[0]

        assigned_payload_id = (
            None  # 静的モデルの場合は確率分布に基づいて選択するため、ここはNoneに設定
        )

        # もし割り当てられたモデルが動的にユニークなペイロードを生成するタイプなら、ここでペイロードの中身を設定
        if (
            "dynamic_unique_payload" in payload_definitions[assigned_model_name]
            and payload_definitions[assigned_model_name]["dynamic_unique_payload"]
        ):
            assigned_payload_id = f"DynamicUniquePayload_Walker_{walker_id}"

        walkers[walker_id] = Walker(
            id=walker_id,
            model=assigned_model_name,
            assigned_payload_id=assigned_payload_id,
            route=generate_random_route_string(detectors),
        )
    return walkers


def choose_payload_for_model(
    model_name: str, assigned_payload_id: str | None, payload_distributions: dict
) -> str:
    """
    指定されたモデルの確率分布に基づいて、ペイロードをランダムに選択します。
    動的ペイロードの場合は、割り当てられたIDをそのまま返します。
    """
    if (
        assigned_payload_id
    ):  # このウォーカーに動的ペイロードが割り当てられている場合はそのまま
        return assigned_payload_id

    # 静的に定義されたペイロード分布を取得
    distribution = payload_distributions.get(model_name)
    if not distribution:
        raise ValueError(f"Payload distribution for model '{model_name}' not found.")

    payload_types = list(distribution.keys())
    probabilities = list(distribution.values())

    # モデルごとに定義された確率分布に基づいてペイロードを1つ選択
    chosen_payload: str = random.choices(payload_types, weights=probabilities, k=1)[0]
    return chosen_payload


# --- シミュレーションの実行 ---
def simulate(
    detectors: dict[str, Detector],
    walkers: dict[str, Walker],  # Walkerオブジェクトの辞書を受け取る
    payload_distributions: dict,
    payloads_per_detector: int,
    walker_speed: float,
    variation_factor: float,
    num_consecutive_payloads: int,
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
        )
        for walker_id, walker in walkers.items():
            assigned_payload_info = (
                walker.assigned_payload_id if walker.assigned_payload_id else "N/A"
            )
            writer.writerow(
                [walker.id, walker.route, walker.model, assigned_payload_info]
            )

    # 検出器ごとのログデータを一時的に保持
    detector_logs = defaultdict(list)

    # シミュレーション開始時刻
    start_time = datetime(2024, 1, 14, 11, 0, 0)

    for walker_id, walker in walkers.items():
        current_time = start_time
        assigned_model_name = walker.model
        assigned_payload_id_for_walker = walker.assigned_payload_id

        route_str = walker.route
        route_detectors = [detectors[d_id] for d_id in route_str]

        for i in range(len(route_detectors)):
            current_detector = route_detectors[i]

            # 生成するペイロードイベントを一時的に保持するリスト
            events_to_add = []

            # 連続ペイロードの生成
            if num_consecutive_payloads > 0:
                # 連続ペイロードの開始オフセットをランダムに決定
                # random.randintの引数は整数である必要があるため、int()で変換
                consecutive_start_offset = random.randint(
                    0, int(300 - (num_consecutive_payloads * 0.001))
                )
                current_sequence_number = random.randint(
                    0, 4095
                )  # 最初の連続ペイロードのシーケンス番号

                for k in range(num_consecutive_payloads):
                    event_time = (
                        current_time
                        + timedelta(seconds=consecutive_start_offset)
                        + timedelta(milliseconds=k)
                    )
                    chosen_payload = choose_payload_for_model(
                        assigned_model_name,
                        assigned_payload_id_for_walker,
                        payload_distributions,
                    )
                    events_to_add.append(
                        DetectionEvent(
                            timestamp=event_time,
                            walker_id=walker.id,
                            hashed_payload=chosen_payload,
                            detector_id=current_detector.id,
                            detector_x=current_detector.x,
                            detector_y=current_detector.y,
                            sequence_number=current_sequence_number,
                        )
                    )
                    current_sequence_number = (
                        current_sequence_number + 1
                    ) % 4096  # 次のシーケンス番号

            # 残りのペイロード（連続ペイロード以外の部分）の生成
            num_random_payloads = payloads_per_detector - num_consecutive_payloads
            for _ in range(num_random_payloads):
                offset_seconds = random.randint(0, 300)
                event_time = current_time + timedelta(seconds=offset_seconds)
                chosen_payload = choose_payload_for_model(
                    assigned_model_name,
                    assigned_payload_id_for_walker,
                    payload_distributions,
                )
                random_sequence_number = random.randint(0, 4095)
                events_to_add.append(
                    DetectionEvent(
                        timestamp=event_time,
                        walker_id=walker.id,
                        hashed_payload=chosen_payload,
                        detector_id=current_detector.id,
                        detector_x=current_detector.x,
                        detector_y=current_detector.y,
                        sequence_number=random_sequence_number,
                    )
                )

            # 生成されたすべてのイベントをタイムスタンプでソートして追加
            events_to_add.sort(key=lambda x: x.timestamp)
            detector_logs[current_detector.id].extend(events_to_add)

            # 次の検出器への移動
            if i < len(route_detectors) - 1:
                next_detector = route_detectors[i + 1]
                travel_duration = calculate_travel_time(
                    current_detector.x,
                    current_detector.y,
                    next_detector.x,
                    next_detector.y,
                    walker_speed,
                    variation_factor,
                )
                current_time += timedelta(seconds=travel_duration)
            else:
                current_time += timedelta(minutes=random.randint(1, 5))

    # 各検出器のログをファイルに書き出し、タイムスタンプでソート
    for det_id, logs in detector_logs.items():
        logs.sort(
            key=lambda x: x.timestamp
        )  # DetectionEventオブジェクトのtimestampでソート
        file_path = os.path.join(results_dir, f"{det_id}_log.csv")
        with open(file_path, "w", newline="") as f:
            fieldnames = [
                "Timestamp",
                "Walker_ID",
                "Hashed_Payload",
                "Detector_ID",
                "Detector_X",
                "Detector_Y",
                "Sequence_Number",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in logs:
                # DetectionEventオブジェクトの属性からデータを書き出す
                writer.writerow(
                    {
                        "Timestamp": entry.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[
                            :-3
                        ],
                        "Walker_ID": entry.walker_id,
                        "Hashed_Payload": entry.hashed_payload,
                        "Detector_ID": entry.detector_id,
                        "Detector_X": entry.detector_x,
                        "Detector_Y": entry.detector_y,
                        "Sequence_Number": entry.sequence_number,
                    }
                )

    print(f"シミュレーションログを '{results_dir}' フォルダに生成しました。")


# --- メイン実行部分 ---
def main():
    # 設定データの読み込み
    detectors = load_detectors("config/detectors.json")
    payload_distributions, model_names, model_probabilities = load_payloads(
        "config/payloads.json"
    )
    simulation_settings = load_simulation_settings("config/simulation_settings.json")

    # 設定値を変数に格納
    num_walkers_to_simulate = simulation_settings["num_walkers_to_simulate"]
    payloads_per_detector_per_walker = simulation_settings[
        "payloads_per_detector_per_walker"
    ]
    num_consecutive_payloads = simulation_settings["num_consecutive_payloads"]
    walker_speed = simulation_settings["walker_speed"]
    variation_factor = simulation_settings["variation_factor"]

    print(f"検出器数: {len(detectors)}")
    print(f"シミュレートするウォーカー数: {num_walkers_to_simulate}人")
    print(
        f"各検出器でウォーカーあたりに放出されるペイロード数: {payloads_per_detector_per_walker}個"
    )
    print(f"ウォーカーの移動速度: {walker_speed} m/s")

    # ウォーカーオブジェクトを生成
    walkers = create_walkers(
        num_walkers_to_simulate,
        detectors,
        model_names,
        model_probabilities,
        payload_distributions,
    )

    # シミュレーション実行
    simulate(
        detectors,
        walkers,  # Walkerオブジェクトの辞書を渡す
        payload_distributions,
        payloads_per_detector_per_walker,
        walker_speed,
        variation_factor,
        num_consecutive_payloads,
    )


if __name__ == "__main__":
    main()

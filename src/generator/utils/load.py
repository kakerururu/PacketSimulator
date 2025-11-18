import json
import os
import csv
import math
from datetime import datetime
import re


def load_jsonc(file_path: str) -> dict:
    """
    JSONCファイルを読み込み、コメントを削除してJSONとしてパースする。
    """
    with open(file_path, "r") as f:
        content = f.read()
    # コメントを削除 (行コメント // とブロックコメント /* */)
    # 行コメント
    content = re.sub(r"//.*", "", content)
    # ブロックコメント (複数行対応)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    return json.loads(content)


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
                    # 'zTimestamp' のような不規則なヘッダーに対応
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

                    # ログの Detector_X, Y を float に変換
                    row["Detector_X"] = float(row["Detector_X"])
                    row["Detector_Y"] = float(row["Detector_Y"])
                    # Sequence_Number を int に変換して追加
                    row["Sequence_Number"] = int(row["Sequence_Number"])
                    all_logs.append(row)
    # タイムスタンプで全体をソート
    all_logs.sort(key=lambda x: x["Timestamp"])
    return all_logs


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


# --- 設定ファイルの読み込み関数を追加 ---
def load_simulation_settings(file_path: str) -> dict:
    """jsoncファイルからシミュレーション設定をロードする"""
    data = load_jsonc(file_path)
    return data["simulation_settings"]


def load_payloads(file_path: str) -> tuple[dict, list, list]:
    """
    ペイロード設定をロードし、モデルごとの全体確率も読み込む。
    動的生成ペイロードを持つモデルも認識する。
    戻り値: (ペイロード分布辞書, モデル名リスト, モデル確率リスト)
    """
    data = load_jsonc(file_path)

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

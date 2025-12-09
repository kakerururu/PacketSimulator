"""設定ファイル読み込みモジュール"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
from ...shared.domain.detector import Detector
from ..domain.payload_config import PayloadDefinitionsDict


def load_jsonc(file_path: str) -> Dict[str, Any]:
    """JSONCファイルを読み込む

    Args:
        file_path: JSONCファイルのパス

    Returns:
        パースされた辞書
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    def remove_jsonc_comments(text: str) -> str:
        # 行コメント (//) を削除
        text = re.sub(r"//.*", "", text)
        # ブロックコメント (/* */) を削除
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        return text

    # コメントを除去
    content_no_comments = remove_jsonc_comments(content)

    # JSONとしてパース
    return json.loads(content_no_comments)


def load_detectors() -> List[Detector]:
    """検出器設定を読み込む

    Args:
        config_dir_path: 設定ファイルディレクトリ
    Returns:
        検出器のリスト

    Examples:
        >>> detectors = load_detectors()
        >>> len(detectors)
        4
        >>> detectors[0].id
        'A'
    """
    detectors_path = Path("config") / "detectors.jsonc"
    json_data = load_jsonc(str(detectors_path))

    return [Detector(id=d["id"], x=d["x"], y=d["y"]) for d in json_data["detectors"]]


def load_payloads() -> Tuple[PayloadDefinitionsDict, List[str], List[float]]:
    """ペイロード設定を読み込む

    Returns:
        (payload_definitions, model_names, model_probabilities) のタプル
        - payload_definitions: モデルごとのペイロード定義
        - model_names: モデル名のリスト
        - model_probabilities: モデルの選択確率のリスト

    Examples:
        >>> payloads, models, probs = load_payloads()
        >>> "Model_C_08" in models
        True
        >>> sum(probs)  # 確率の合計は1.0
        1.0
    """
    # ペイロード設定を読み込み
    payloads_path = Path("config") / "payloads.jsonc"
    data = load_jsonc(str(payloads_path))
    payload_definitions = data["models"]

    # モデル名と確率を抽出
    model_names = list(payload_definitions.keys())
    model_probabilities = [
        payload_definitions[model]["overall_probability"] for model in model_names
    ]

    return payload_definitions, model_names, model_probabilities


def load_simulation_settings(config_dir: str = "config") -> Dict[str, Any]:
    """シミュレーション設定を読み込む

    Args:
        config_dir: 設定ファイルディレクトリ

    Returns:
        シミュレーション設定の辞書

    Examples:
        >>> settings = load_simulation_settings()
        >>> settings["num_walkers_to_simulate"]
        50
        >>> settings["walker_speed"]
        1.4
    """
    settings_path = Path(config_dir) / "simulation_settings.jsonc"
    data = load_jsonc(str(settings_path))

    settings = data["simulation_settings"]

    # デフォルト値を設定（plan.mdの仕様）
    settings.setdefault("stay_duration_min_seconds", 180)
    settings.setdefault("stay_duration_max_seconds", 420)

    return settings

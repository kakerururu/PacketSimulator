"""Estimator用の設定ファイル読み込みモジュール"""

import json
import re
from pathlib import Path
from typing import Dict, Any, List
from ...shared.domain.detector import Detector
from ..domain.clustering_config import ClusteringConfig


def load_jsonc(file_path: str) -> Dict[str, Any]:
    """JSONCファイルを読み込む（コメント付きJSON）

    Args:
        file_path: JSONCファイルのパス

    Returns:
        パースされた辞書
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 行コメント (//) を削除
    content = re.sub(r"//.*", "", content)
    # ブロックコメント (/* */) を削除
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    return json.loads(content)


def load_detectors(config_dir: str = "config") -> Dict[str, Detector]:
    """検出器設定を読み込み、辞書形式で返す

    Args:
        config_dir: 設定ファイルディレクトリ

    Returns:
        検出器の辞書 {detector_id: Detector}
    """
    detectors_path = Path(config_dir) / "detectors.jsonc"
    json_data = load_jsonc(str(detectors_path))

    return {
        d["id"]: Detector(id=d["id"], x=d["x"], y=d["y"])
        for d in json_data["detectors"]
    }


def load_simulation_settings(config_dir: str = "config") -> Dict[str, Any]:
    """シミュレーション設定を読み込む（walker_speed, impossible_factor等）

    Args:
        config_dir: 設定ファイルディレクトリ

    Returns:
        シミュレーション設定の辞書
    """
    settings_path = Path(config_dir) / "simulation_settings.jsonc"
    data = load_jsonc(str(settings_path))
    return data["simulation_settings"]


def load_estimator_settings(config_dir: str = "config") -> Dict[str, Any]:
    """Estimator固有の設定を読み込む（allow_long_stays, max_passes等）

    Args:
        config_dir: 設定ファイルディレクトリ

    Returns:
        Estimator設定の辞書
    """
    settings_path = Path(config_dir) / "estimator_settings.jsonc"
    data = load_jsonc(str(settings_path))

    settings = data["estimator_settings"]
    # デフォルト値を設定
    settings.setdefault("allow_long_stays", False)
    settings.setdefault("max_passes", 10)

    return settings


def load_clustering_config(config_dir: str = "config") -> ClusteringConfig:
    """設定ファイルからClusteringConfigを生成

    simulation_settings.jsoncとestimator_settings.jsoncから
    必要な設定を読み込み、ClusteringConfigを生成する。

    Args:
        config_dir: 設定ファイルディレクトリ

    Returns:
        ClusteringConfig インスタンス
    """
    detectors = load_detectors(config_dir)
    sim_settings = load_simulation_settings(config_dir)
    est_settings = load_estimator_settings(config_dir)

    return ClusteringConfig(
        detectors=detectors,
        walker_speed=sim_settings.get("walker_speed", 1.4),
        impossible_factor=sim_settings.get("impossible_factor", 0.8),
        allow_long_stays=est_settings.get("allow_long_stays", False),
    )

"""実験結果出力モジュール"""

import json
from pathlib import Path
from datetime import datetime

from ..domain.experiment_config import ExperimentConfig
from ..domain.aggregated_result import ConditionResult, AggregatedResult


def write_experiment_config(config: ExperimentConfig, experiment_dir: str) -> None:
    """実験設定を保存

    Args:
        config: 実験設定
        experiment_dir: 実験ディレクトリ
    """
    output_path = Path(experiment_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config_path = output_path / "config.json"
    config_data = {
        "experiment_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        **config.to_dict(),
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=2, ensure_ascii=False)


def write_condition_summary(result: ConditionResult, output_path: str) -> None:
    """条件のサマリーを保存

    Args:
        result: 条件の結果
        output_path: 出力パス
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)


def write_final_summary(result: AggregatedResult, output_path: str) -> None:
    """最終サマリーを保存

    Args:
        result: 全体の集約結果
        output_path: 出力パス
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)


def write_seed_file(run_dir: str, seed: int) -> None:
    """シードファイルを保存

    Args:
        run_dir: 実行ディレクトリ
        seed: 使用したシード値
    """
    output_path = Path(run_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    seed_path = output_path / "seed.txt"
    with open(seed_path, "w", encoding="utf-8") as f:
        f.write(str(seed))

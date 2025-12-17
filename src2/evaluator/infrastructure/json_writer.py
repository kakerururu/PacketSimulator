"""JSON書き込み機能

責務: 評価結果をJSONファイルに出力する。

【出力フォーマット】

{
    "metadata": {
        "evaluation_timestamp": "2025-01-01 12:00:00",
        "ground_truth_file": "...",
        "estimated_file": "...",
        "tolerance_seconds": 1200.0,
        "evaluation_method": "trajectory_based",
        "num_partial_routes": 0,
        "num_complete_routes": 2,
        "partial_routes": []
    },
    "overall_metrics": {
        "total_stays": 2,
        "mae": 0.0,
        "rmse": 0.0,
        "tracking_rate": 1.0,
        "total_gt_count": 2,
        "total_est_count": 2,
        "total_absolute_error": 0
    },
    "stay_evaluations": [
        {
            "detector_id": "ABCD_...",
            "gt_count": 1,
            "est_count": 1,
            "error": 0,
            ...
        }
    ]
}
"""

import json
from dataclasses import asdict
from pathlib import Path

from ..domain.evaluation import EvaluationResult


def save_evaluation_result(result: EvaluationResult, file_path: str) -> None:
    """評価結果をJSONで保存

    EvaluationResultオブジェクトをJSON形式でファイルに出力する。
    出力ディレクトリが存在しない場合は自動作成する。

    【処理フロー】
    1. 出力ディレクトリを作成（必要な場合）
    2. EvaluationResult を辞書に変換
    3. JSON形式でファイルに書き込み

    【出力オプション】
    - indent=2: 読みやすいインデント
    - ensure_ascii=False: 日本語などの非ASCII文字をそのまま出力
    - default: None値の処理

    Args:
        result: 評価結果オブジェクト
        file_path: 出力JSONファイルパス
                  例: "src2_result/evaluation/results.json"

    Raises:
        IOError: ファイル書き込みに失敗した場合
        PermissionError: 書き込み権限がない場合
    """
    # ========================================================================
    # 出力ディレクトリの作成
    # ========================================================================
    # ディレクトリが存在しない場合は自動作成
    output_dir = Path(file_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # ========================================================================
    # EvaluationResult を辞書に変換
    # ========================================================================
    # dataclass の asdict を使用して、ネストしたオブジェクトも再帰的に辞書化
    data = {
        "metadata": result.metadata,
        "overall_metrics": asdict(result.overall_metrics),
        "stay_evaluations": [asdict(se) for se in result.stay_evaluations]
    }

    # ========================================================================
    # JSONファイルに書き込み
    # ========================================================================
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,           # 読みやすいインデント
            ensure_ascii=False  # 日本語などをそのまま出力
        )

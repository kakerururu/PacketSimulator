"""JSON書き込み機能"""

import json
from dataclasses import asdict
from pathlib import Path
from ..domain.time_window import EvaluationResult


def save_evaluation_result(result: EvaluationResult, file_path: str) -> None:
    """評価結果をJSONで保存

    Args:
        result: 評価結果オブジェクト
        file_path: 出力JSONファイルパス

    Raises:
        IOError: ファイル書き込みに失敗した場合
    """
    # 出力ディレクトリが存在しない場合は作成
    output_dir = Path(file_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Noneをnullに変換するため、カスタムエンコーダーを使用
    def convert_none_to_null(obj):
        if obj is None:
            return None
        return obj

    data = {
        "metadata": result.metadata,
        "overall_metrics": asdict(result.overall_metrics),
        "stay_evaluations": [asdict(se) for se in result.stay_evaluations]
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=convert_none_to_null)

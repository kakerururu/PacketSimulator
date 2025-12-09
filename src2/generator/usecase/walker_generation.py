"""通行人生成ユースケース

責務: 通行人の生成とモデル・ルートの割り当て
"""

import random
from typing import List
from ..domain.walker import Walker
from ..domain.payload_config import PayloadDefinitionsDict
from ...shared.domain.detector import Detector


def generate_random_route(detectors: List[Detector]) -> str:
    """ランダムなルート文字列を生成

    Args:
        detectors: 検出器のリスト

    Returns:
        ルート文字列 (例: "ACBD")
    """
    detector_ids = [d.id for d in detectors]
    random.shuffle(detector_ids)
    return "".join(detector_ids)


def generate_walkers(
    num_walkers: int,
    detectors: List[Detector],
    payload_definitions: PayloadDefinitionsDict,
    model_names: List[str],
    model_probabilities: List[float],
) -> List[Walker]:
    """指定された数の通行人を生成

    Args:
        num_walkers: 生成する通行人の数
        detectors: 検出器のリスト
        payload_definitions: ペイロード定義
        model_names: モデル名のリスト
        model_probabilities: モデルの選択確率

    Returns:
        通行人のリスト
    """
    walkers = []
    for i in range(num_walkers):
        walker_id = f"Walker_{i + 1}"

        # モデルを確率的に選択
        assigned_model = random.choices(model_names, weights=model_probabilities, k=1)[
            0
        ]

        walkers.append(
            Walker(
                id=walker_id,
                model=assigned_model,
                route=generate_random_route(detectors),
            )
        )

    return walkers

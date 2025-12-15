"""クラスタリング設定を管理するデータクラス"""

from dataclasses import dataclass
from typing import Dict
from ...shared.domain.detector import Detector


@dataclass
class ClusteringConfig:
    """クラスタリングの設定パラメータ

    クラスタリング処理全体で共有される設定値をまとめる。
    関数間でのパラメータ受け渡しを簡潔にする。

    Attributes:
        detectors: 検出器の辞書 {detector_id: Detector}
        walker_speed: 歩行速度 (m/s)、デフォルト 1.4
        impossible_factor: ありえない移動判定の係数、デフォルト 0.8
            → 最小移動時間の80%未満で到着 = ありえない
        allow_long_stays: 長時間滞在を許可するか、デフォルト False
    """

    detectors: Dict[str, Detector]
    walker_speed: float = 1.4
    impossible_factor: float = 0.8
    allow_long_stays: bool = False

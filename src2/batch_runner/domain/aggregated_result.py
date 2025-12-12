"""集約結果のドメインモデル"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class MetricStatistics:
    """メトリクスの統計情報

    Attributes:
        mean: 平均値
        std: 標準偏差
        ci_95_lower: 95%信頼区間の下限
        ci_95_upper: 95%信頼区間の上限
        min: 最小値
        max: 最大値
    """

    mean: float
    std: float
    ci_95_lower: float
    ci_95_upper: float
    min: float
    max: float

    def to_dict(self) -> Dict[str, float]:
        """辞書形式に変換"""
        return {
            "mean": self.mean,
            "std": self.std,
            "ci_95_lower": self.ci_95_lower,
            "ci_95_upper": self.ci_95_upper,
            "min": self.min,
            "max": self.max,
        }


@dataclass
class ConditionResult:
    """1つの条件（num_walkers）の結果

    Attributes:
        num_walkers: 通行人数
        num_runs: 実行回数
        metrics: メトリクス名 -> 統計情報のマップ
        run_results: 各実行の生の結果（オプション）
    """

    num_walkers: int
    num_runs: int
    metrics: Dict[str, MetricStatistics]
    run_results: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "num_walkers": self.num_walkers,
            "num_runs": self.num_runs,
            "metrics": {name: stat.to_dict() for name, stat in self.metrics.items()},
        }


@dataclass
class AggregatedResult:
    """全体の集約結果

    Attributes:
        experiment_id: 実験ID
        config: 実験設定
        conditions: 条件ごとの結果リスト
    """

    experiment_id: str
    config: Dict[str, Any]
    conditions: List[ConditionResult]

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "experiment_id": self.experiment_id,
            "config": self.config,
            "conditions": [cond.to_dict() for cond in self.conditions],
        }

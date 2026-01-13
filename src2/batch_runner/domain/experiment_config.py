"""実験設定のドメインモデル"""

from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class ExperimentConfig:
    """実験設定

    バッチ実験の設定を保持する。

    Attributes:
        num_walkers_list: 評価するnum_walkersのリスト
        num_runs: 各条件での実行回数
        output_dir: 出力ディレクトリ
        base_seed: 乱数シードのベース値（各実行でインクリメント）
        time_bin_minutes: 評価時の時間ビン幅（分）
        compare_time_bins: 比較モード用の時間ビンリスト（指定時は比較モード）

    Examples:
        >>> config = ExperimentConfig(
        ...     num_walkers_list=[50, 100, 200],
        ...     num_runs=30,
        ...     output_dir="experiments/",
        ...     time_bin_minutes=30
        ... )
        >>> # 比較モード: 15, 30, 60分で比較
        >>> config = ExperimentConfig(
        ...     num_walkers_list=[50],
        ...     num_runs=10,
        ...     output_dir="experiments/",
        ...     compare_time_bins=[15, 30, 60]
        ... )
    """

    num_walkers_list: List[int]
    num_runs: int
    output_dir: str
    base_seed: int = 42
    time_bin_minutes: int = 30
    compare_time_bins: List[int] = field(default_factory=list)

    @property
    def is_compare_mode(self) -> bool:
        """比較モードかどうか"""
        return len(self.compare_time_bins) > 0

    def get_time_bins_to_evaluate(self) -> List[int]:
        """評価する時間ビンのリストを取得

        比較モードの場合はcompare_time_binsを返す。
        通常モードの場合はtime_bin_minutesのみを含むリストを返す。

        Returns:
            時間ビンのリスト（ソート済み）
        """
        if self.is_compare_mode:
            return sorted(self.compare_time_bins)
        else:
            return [self.time_bin_minutes]

    def get_seed(self, num_walkers: int, run_index: int) -> int:
        """特定の実行に対するシードを計算

        Args:
            num_walkers: 通行人数
            run_index: 実行インデックス（0始まり）

        Returns:
            シード値
        """
        # num_walkersとrun_indexから一意のシードを生成
        walkers_index = self.num_walkers_list.index(num_walkers)
        return self.base_seed + walkers_index * 10000 + run_index

    def get_experiment_id(self) -> str:
        """実験IDを生成

        Returns:
            実験ID（例: "exp_20250610_143000"）
        """
        return datetime.now().strftime("exp_%Y%m%d_%H%M%S")

    def to_dict(self) -> dict:
        """辞書形式に変換

        Returns:
            設定を表す辞書
        """
        result = {
            "num_walkers_list": self.num_walkers_list,
            "num_runs": self.num_runs,
            "output_dir": self.output_dir,
            "base_seed": self.base_seed,
            "time_bin_minutes": self.time_bin_minutes,
        }
        if self.is_compare_mode:
            result["compare_time_bins"] = self.compare_time_bins
        return result

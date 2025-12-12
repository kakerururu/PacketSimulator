"""軌跡ドメインモデル (評価用)

Ground TruthとEstimated軌跡の統一インターフェース
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class GroundTruthStay:
    """Ground Truth滞在情報

    シミュレーションで生成された、歩行者の実際の滞在データ。
    """
    detector_id: str                # 検出器ID（例: "A", "B", "C", "D"）
    arrival_time: datetime          # この検出器への到着時刻
    departure_time: datetime        # この検出器からの出発時刻
    duration_seconds: float         # 滞在時間（秒）


@dataclass
class EstimatedStay:
    """Estimated滞在情報

    パケット検知データから推定された滞在情報。
    """
    detector_id: str                # 検出器ID（例: "A", "B", "C", "D"）
    num_detections: int             # この検出器で検知されたパケット数
    first_detection: datetime       # 最初の検知時刻
    last_detection: datetime        # 最後の検知時刻
    duration_seconds: float         # 推定滞在時間（秒）= last - first


@dataclass
class GroundTruthTrajectory:
    """Ground Truth軌跡

    1人の歩行者の完全な移動経路（正解データ）。
    """
    trajectory_id: str              # 軌跡ID（例: "gt_traj_1"）
    walker_id: str                  # 歩行者ID（例: "Walker_1"）
    route: str                      # ルートパターン（例: "ABCD"）
    stays: List[GroundTruthStay]    # 各検出器での滞在情報リスト
    model: Optional[str] = None     # 歩行者モデル（オプション）
    integrated_payload_id: Optional[str] = None  # 統合ペイロードID（オプション）


@dataclass
class EstimatedTrajectory:
    """Estimated軌跡

    クラスタリングにより推定された1人分の移動経路。
    """
    trajectory_id: str              # 推定軌跡ID（例: "est_traj_1"）
    route: str                      # 推定されたルートパターン（例: "ABCD"）
    stays: List[EstimatedStay]      # 各検出器での推定滞在情報リスト
    cluster_ids: Optional[List[str]] = None  # この軌跡を構成するクラスタIDリスト

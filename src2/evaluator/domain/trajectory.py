"""軌跡ドメインモデル (評価用)

責務: Ground Truth と Estimated 軌跡の統一インターフェースを提供。
     評価処理で使用するデータ構造を定義。

【データの流れ】

Generator → Estimator → Evaluator
    │           │           │
    ↓           ↓           ↓
   GT軌跡     Est軌跡     比較・評価
 (正解データ)  (推定結果)

【GT軌跡 vs Est軌跡】

GT (Ground Truth):
- シミュレーションで生成された「正解」データ
- arrival_time / departure_time: 実際の到着・出発時刻
- duration_seconds: 実際の滞在時間

Est (Estimated):
- パケット検知から推定されたデータ
- first_detection / last_detection: 最初・最後の検知時刻
- num_detections: 検知されたパケット数

【使用例】
    from src2.evaluator.domain.trajectory import (
        GroundTruthTrajectory,
        EstimatedTrajectory,
    )

    # GT軌跡の作成
    gt_stay = GroundTruthStay(
        detector_id="A",
        arrival_time=datetime(2025, 1, 1, 9, 0),
        departure_time=datetime(2025, 1, 1, 9, 10),
        duration_seconds=600.0
    )
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


# ============================================================================
# Ground Truth（正解データ）
# ============================================================================


@dataclass
class GroundTruthStay:
    """Ground Truth滞在情報

    シミュレーションで生成された、歩行者の実際の滞在データ。
    「この人は実際にこの検出器エリアに何時から何時までいた」という正解情報。

    【フィールド詳細】

    detector_id:
        検出器ID（例: "A", "B", "C", "D"）
        どの検出器のエリアに滞在していたか

    arrival_time:
        この検出器エリアへの到着時刻
        例: 2025-01-01 09:00:00

    departure_time:
        この検出器エリアからの出発時刻
        例: 2025-01-01 09:10:00

    duration_seconds:
        滞在時間（秒）= departure_time - arrival_time
        例: 600.0 (10分)

    Attributes:
        detector_id: 検出器ID（例: "A", "B", "C", "D"）
        arrival_time: この検出器への到着時刻
        departure_time: この検出器からの出発時刻
        duration_seconds: 滞在時間（秒）
    """
    detector_id: str          # 検出器ID（例: "A"）
    arrival_time: datetime    # 到着時刻
    departure_time: datetime  # 出発時刻
    duration_seconds: float   # 滞在時間（秒）


@dataclass
class GroundTruthTrajectory:
    """Ground Truth軌跡

    1人の歩行者の完全な移動経路（正解データ）。
    複数の GroundTruthStay を時系列順に持つ。

    【データ構造イメージ】

    trajectory_id: "gt_traj_1"
    walker_id: "Walker_1"
    route: "ABCD"
    stays: [
        Stay(A, 09:00-09:10),
        Stay(B, 10:00-10:10),
        Stay(C, 11:00-11:10),
        Stay(D, 12:00-12:10),
    ]

    【route フィールドについて】
    - 訪問した検出器を順に連結した文字列
    - 例: "ABCD" = A → B → C → D の順で訪問
    - 例: "DCBA" = D → C → B → A の順で訪問

    Attributes:
        trajectory_id: 軌跡ID（例: "gt_traj_1"）
        walker_id: 歩行者ID（例: "Walker_1"）
        route: ルートパターン（例: "ABCD"）
        stays: 各検出器での滞在情報リスト（時系列順）
        model: 歩行者モデル（オプション）
        integrated_payload_id: 統合ペイロードID（オプション）
    """
    trajectory_id: str                       # 軌跡ID
    walker_id: str                           # 歩行者ID
    route: str                               # ルートパターン（例: "ABCD"）
    stays: List[GroundTruthStay]             # 滞在情報リスト（時系列順）
    model: Optional[str] = None              # 歩行者モデル（オプション）
    integrated_payload_id: Optional[str] = None  # 統合ペイロードID


# ============================================================================
# Estimated（推定データ）
# ============================================================================


@dataclass
class EstimatedStay:
    """Estimated滞在情報

    パケット検知データから推定された滞在情報。
    「この検出器でこれだけのパケットが検知された」という推定情報。

    【GT vs Est の違い】

    GT:  arrival_time / departure_time → 実際の滞在時刻
    Est: first_detection / last_detection → パケット検知時刻

    通常、Est の時刻は GT と若干ズレる:
    - first_detection >= arrival_time (到着後に検知開始)
    - last_detection <= departure_time (出発前に検知終了)

    【フィールド詳細】

    num_detections:
        検知されたパケット数
        多いほど滞在が確実に推定されたことを示す

    Attributes:
        detector_id: 検出器ID（例: "A", "B", "C", "D"）
        num_detections: この検出器で検知されたパケット数
        first_detection: 最初の検知時刻
        last_detection: 最後の検知時刻
        duration_seconds: 推定滞在時間（秒）= last - first
    """
    detector_id: str          # 検出器ID
    num_detections: int       # 検知されたパケット数
    first_detection: datetime # 最初の検知時刻
    last_detection: datetime  # 最後の検知時刻
    duration_seconds: float   # 推定滞在時間（秒）


@dataclass
class EstimatedTrajectory:
    """Estimated軌跡

    クラスタリングにより推定された1人分の移動経路。
    複数の EstimatedStay を時系列順に持つ。

    【推定の仕組み】
    1. 同じペイロード（BLEハッシュ）を持つパケットをグループ化
    2. 物理的に可能な移動をクラスタリング
    3. 1つのクラスタ = 1人分の軌跡として推定

    【route フィールドについて】
    - クラスタリングで推定された訪問順序
    - 例: "ABCD" = A → B → C → D と推定
    - GT の route と比較して評価される

    【cluster_ids について】
    - この軌跡を構成するクラスタのIDリスト
    - 推定過程のトレーサビリティに使用

    Attributes:
        trajectory_id: 推定軌跡ID（例: "est_traj_1"）
        route: 推定されたルートパターン（例: "ABCD"）
        stays: 各検出器での推定滞在情報リスト（時系列順）
        cluster_ids: この軌跡を構成するクラスタIDリスト（オプション）
    """
    trajectory_id: str                    # 推定軌跡ID
    route: str                            # 推定ルートパターン
    stays: List[EstimatedStay]            # 推定滞在情報リスト（時系列順）
    cluster_ids: Optional[List[str]] = None  # クラスタIDリスト

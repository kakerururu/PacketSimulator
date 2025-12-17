"""軌跡ベース評価のドメインモデル

このモジュールは評価に使用するデータ構造を定義する。

クラス一覧:
    - EvaluationConfig: 評価設定（許容誤差など）
    - RouteEvaluation: ルートごとの評価結果（内部処理用）
    - StayEvaluation: 滞在/ルート評価結果（出力用、互換性維持）
    - OverallMetrics: 全体の評価指標
    - EvaluationResult: 評価結果全体を格納
"""

from dataclasses import dataclass, field
from typing import List


# ============================================================================
# 評価設定
# ============================================================================


@dataclass
class EvaluationConfig:
    """評価設定

    評価時に使用するパラメータを格納する。

    Attributes:
        tolerance_seconds: 許容誤差（秒）
            - GTの滞在時刻に対して、±この時間内のEst検出を許容する
            - デフォルト: 1200秒 = 20分
            - 例: GTが10:00-10:30の滞在の場合、
                  9:40-10:50の範囲内のEst検出を許容

    使用例:
        config = EvaluationConfig(tolerance_seconds=600.0)  # 10分の許容誤差
    """
    tolerance_seconds: float = 1200.0  # デフォルト: 20分


# ============================================================================
# ルート評価結果（内部処理用）
# ============================================================================


@dataclass
class RouteEvaluation:
    """ルートごとの評価結果

    内部処理で使用するデータ構造。
    時系列情報を含むルート名（例: "ABCD_0900-0910_..."）ごとに
    GT/Est人数と誤差を集計する。

    Attributes:
        route: 時系列情報を含むルート名
               例: "ABCD_0900-0910_1000-1010_1100-1110_1200-1210"
        gt_count: このルートのGT人数（正解の人数）
        est_count: このルートのEst人数（推定された人数）
        error: 誤差（|gt_count - est_count|）
        gt_trajectory_ids: このルートに該当するGT軌跡のIDリスト
        est_trajectory_ids: このルートに該当するEst軌跡のIDリスト

    Note:
        - 評価完了後、StayEvaluation形式に変換して出力される
        - errorは後から計算して設定されるため、初期値は0
    """
    route: str
    gt_count: int = 0
    est_count: int = 0
    error: int = 0
    gt_trajectory_ids: List[str] = field(default_factory=list)
    est_trajectory_ids: List[str] = field(default_factory=list)


# ============================================================================
# 滞在/ルート評価結果（出力用）
# ============================================================================


@dataclass
class StayEvaluation:
    """ルート評価結果（JSON出力用）

    【歴史的経緯】
    元々は滞在（Stay）単位の評価用だったが、現在はルート単位の評価に使用。
    後方互換性のためクラス名は変更していない。

    【フィールドの使い方】
    - detector_id: 実際にはルート名が入る
      例: "ABCD_0900-0910_1000-1010_1100-1110_1200-1210"
    - gt_start/gt_end/tolerance_start/tolerance_end: ルート評価では空文字

    Attributes:
        detector_id: ルート名（時系列情報を含む）
        gt_start: GT滞在開始時刻（ルート評価では空文字）
        gt_end: GT滞在終了時刻（ルート評価では空文字）
        tolerance_start: 許容範囲開始（ルート評価では空文字）
        tolerance_end: 許容範囲終了（ルート評価では空文字）
        gt_count: このルートのGT人数
        est_count: このルートのEst人数
        error: 誤差（|gt_count - est_count|）
        gt_trajectory_ids: このルートに該当するGT軌跡IDリスト
        est_trajectory_ids: このルートに該当するEst軌跡IDリスト
    """
    detector_id: str               # ルート名（例: "ABCD_0900-0910_..."）
    gt_start: str                  # GT滞在開始時刻（ルート評価では空文字）
    gt_end: str                    # GT滞在終了時刻（ルート評価では空文字）
    tolerance_start: str           # 許容範囲開始（ルート評価では空文字）
    tolerance_end: str             # 許容範囲終了（ルート評価では空文字）
    gt_count: int                  # このルートのGT人数
    est_count: int                 # このルートのEst人数
    error: int                     # 誤差: |gt_count - est_count|
    gt_trajectory_ids: List[str]   # 該当するGT軌跡IDリスト
    est_trajectory_ids: List[str]  # 該当するEst軌跡IDリスト


# ============================================================================
# 全体評価指標
# ============================================================================


@dataclass
class OverallMetrics:
    """全体の評価指標

    評価全体を通じての統計情報を格納する。

    【指標の意味】
    - MAE: 平均絶対誤差。ルートあたり平均何人ずれているか。0が最良。
    - RMSE: 二乗平均平方根誤差。大きな誤差にペナルティ。0が最良。
    - Tracking Rate: 完全一致したルートの割合。1.0（100%）が最良。

    【MAE vs RMSE】
    - MAE = 1.0, RMSE = 1.0 → 誤差が均一
    - MAE = 1.0, RMSE = 2.0 → 外れ値（大きな誤差）がある

    Attributes:
        total_stays: 評価対象のルート数（時系列情報を含む）
        mae: Mean Absolute Error（平均絶対誤差）
        rmse: Root Mean Squared Error（二乗平均平方根誤差）
        tracking_rate: 追跡率（完全一致の割合）。0.0～1.0
        total_gt_count: GT軌跡の総数
        total_est_count: Est軌跡の総数（完全ルートのみ）
        total_absolute_error: 絶対誤差の合計（Σ|GT - Est|）
    """
    total_stays: int           # 評価対象のルート数
    mae: float                 # Mean Absolute Error（0が最良）
    rmse: float                # Root Mean Squared Error（0が最良）
    tracking_rate: float       # 追跡率（1.0が最良）
    total_gt_count: int        # GT軌跡の総数
    total_est_count: int       # Est軌跡の総数（完全ルートのみ）
    total_absolute_error: int  # 絶対誤差の合計


# ============================================================================
# 評価結果（最終出力）
# ============================================================================


@dataclass
class EvaluationResult:
    """評価結果全体

    評価処理の最終出力として、メタデータ・全体指標・詳細結果を格納する。
    JSON形式で出力される。

    Attributes:
        metadata: 評価に関するメタ情報
            - evaluation_timestamp: 評価実行日時
            - ground_truth_file: GTファイルパス
            - estimated_file: Estファイルパス
            - tolerance_seconds: 使用した許容誤差
            - evaluation_method: 評価方法（"trajectory_based"）
            - num_partial_routes: 除外された部分ルート数
            - num_complete_routes: 評価対象の完全ルート数
            - partial_routes: 除外された部分ルートの詳細

        overall_metrics: 全体の評価指標（MAE, RMSE, 追跡率など）

        stay_evaluations: ルートごとの詳細評価結果リスト
    """
    metadata: dict                           # 評価メタ情報
    overall_metrics: OverallMetrics          # 全体評価指標
    stay_evaluations: List[StayEvaluation]   # ルートごとの詳細

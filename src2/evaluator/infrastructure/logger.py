"""評価ログの出力（軌跡ベース）

責務: 評価結果を人間が読みやすい形式（Markdown, CSV）で出力する。

【出力ファイル】
1. サマリーログ (Markdown)
   - evaluation_summary_{timestamp}.md
   - 全体指標、ルート別統計、誤差分布

2. ルート評価詳細 (CSV)
   - route_evaluations_{timestamp}.csv
   - 各ルートのGT/Est人数、誤差、軌跡ID

【使用場面】
- 評価結果の確認・分析
- レポート作成の素材
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Dict

from ..domain.evaluation import EvaluationResult


def save_evaluation_logs(
    result: EvaluationResult,
    log_dir: str = "src2_result/evaluate_log"
) -> Dict[str, str]:
    """評価ログを保存

    評価結果をMarkdownとCSV形式で出力する。
    ファイル名にはタイムスタンプが付与される。

    【出力ファイル】
    - evaluation_summary_{timestamp}.md: サマリー（Markdown）
    - route_evaluations_{timestamp}.csv: 詳細（CSV）

    Args:
        result: 評価結果オブジェクト
        log_dir: ログ出力ディレクトリ
                デフォルト: "src2_result/evaluate_log"

    Returns:
        保存したファイルパスの辞書
        {"summary": "...", "route_evaluations": "..."}

    Raises:
        IOError: ファイル書き込みに失敗した場合
    """
    # ========================================================================
    # 出力ディレクトリの準備
    # ========================================================================
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # タイムスタンプ（ファイル名に使用）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ========================================================================
    # 各形式でログを出力
    # ========================================================================
    saved_files = {}

    # 1. サマリーログ (Markdown)
    summary_file = log_path / f"evaluation_summary_{timestamp}.md"
    _save_summary_markdown(result, summary_file)
    saved_files["summary"] = str(summary_file)

    # 2. ルート評価詳細 (CSV)
    routes_file = log_path / f"route_evaluations_{timestamp}.csv"
    _save_route_evaluations_csv(result, routes_file)
    saved_files["route_evaluations"] = str(routes_file)

    return saved_files


# ============================================================================
# サマリーログ (Markdown)
# ============================================================================


def _save_summary_markdown(result: EvaluationResult, filepath: Path) -> None:
    """サマリーログをMarkdown形式で保存

    【出力内容】
    1. 評価情報（ファイルパス、許容誤差など）
    2. 評価方法の説明
    3. 全体評価指標（MAE, RMSE, 追跡率）
    4. 指標の解釈ガイド
    5. ルート別統計テーブル
    6. 誤差分布

    Args:
        result: 評価結果オブジェクト
        filepath: 出力ファイルパス
    """
    with open(filepath, "w", encoding="utf-8") as f:
        # ====================================================================
        # ヘッダー
        # ====================================================================
        f.write("# 軌跡推定の評価ログ（軌跡ベース）\n\n")

        # ====================================================================
        # 1. 評価情報
        # ====================================================================
        f.write("## 評価情報\n\n")
        f.write(f"- **評価日時**: {result.metadata['evaluation_timestamp']}\n")
        f.write(f"- **Ground Truthファイル**: `{result.metadata['ground_truth_file']}`\n")
        f.write(f"- **推定結果ファイル**: `{result.metadata['estimated_file']}`\n")
        f.write(f"- **許容誤差**: {result.metadata['tolerance_seconds']}秒 ({result.metadata['tolerance_seconds']/60:.1f}分)\n")
        f.write(f"- **評価方法**: {result.metadata['evaluation_method']}\n\n")

        # ====================================================================
        # 2. 評価方法の説明
        # ====================================================================
        f.write("## 評価方法\n\n")
        f.write("GT軌跡に時系列情報を付与し、Est軌跡を許容誤差でマッチングして評価する。\n\n")

        f.write("**ルート名の生成**:\n")
        f.write("- GT軌跡: 時系列情報付きルート名を生成\n")
        f.write("  - 例: `ABDC_1100-1106_1452-1459_2008-2015_0008-0015`\n")
        f.write("  - 各地点での滞在時刻（到着-出発）を含む\n\n")

        f.write("**Est軌跡のマッチング**:\n")
        tolerance_min = result.metadata['tolerance_seconds'] / 60
        f.write(f"- Est軌跡をGTと許容誤差（±{tolerance_min:.0f}分）でマッチング\n")
        f.write("- マッチした場合: GTと同じルート名でカウント\n")
        f.write("- マッチしない場合: 独自のルート名で別ルートとしてカウント\n\n")

        f.write("**評価対象**:\n")
        f.write("- すべての検出器(A,B,C,D)を経由した完全ルートのみ評価対象\n")
        f.write("- 部分ルート（一部検出器のみ経由）は評価対象外\n\n")

        # ====================================================================
        # 3. 全体評価指標
        # ====================================================================
        m = result.overall_metrics
        f.write("## 全体評価指標\n\n")
        f.write("| 指標 | 値 | 説明 |\n")
        f.write("|------|-----|------|\n")
        f.write(f"| 評価したルート数（時系列含む） | {m.total_stays} | 時系列情報を含むルートの種類数 |\n")
        f.write(f"| GT軌跡総数 | {m.total_gt_count}人 | 全ルート合計のGT人数 |\n")
        f.write(f"| Est軌跡総数（完全ルート） | {m.total_est_count}人 | 評価対象のEst軌跡数 |\n")
        f.write(f"| 総絶対誤差 | {m.total_absolute_error} | 全ルートの誤差の合計 |\n")
        f.write(f"| **MAE** (平均絶対誤差) | **{m.mae:.3f}** | ルートあたりの平均誤差 |\n")
        f.write(f"| **RMSE** (二乗平均平方根誤差) | **{m.rmse:.3f}** | 大きな誤差にペナルティ |\n")
        f.write(f"| **追跡率** | **{m.tracking_rate:.1%}** | GT人数==Est人数のルート割合 |\n\n")

        # ====================================================================
        # 4. 指標の解釈ガイド
        # ====================================================================
        f.write("### 指標の解釈\n\n")
        f.write("- **MAE (Mean Absolute Error)**: ルートあたり平均で何人ずれているか\n")
        f.write("  - 0に近いほど良い\n")
        f.write("  - 例: MAE=0.5 → 平均0.5人のずれ\n\n")
        f.write("- **RMSE (Root Mean Squared Error)**: MAEより大きな誤差に厳しい\n")
        f.write("  - RMSE > MAE の場合、バラつきが大きい\n")
        f.write("  - 0に近いほど良い\n\n")
        f.write("- **追跡率 (Tracking Rate)**: 人数がピッタリ合ったルートの割合\n")
        f.write("  - 1.0 (100%) が理想\n\n")

        # ====================================================================
        # 5. ルート別統計テーブル
        # ====================================================================
        f.write("## ルートごとの評価サマリー\n\n")
        f.write("### ルート別の統計\n\n")
        f.write("| ルート | GT人数 | Est人数 | 誤差 | 正確一致 |\n")
        f.write("|--------|--------|---------|------|----------|\n")

        # ルート名でソート
        sorted_evaluations = sorted(result.stay_evaluations, key=lambda x: x.detector_id)
        for se in sorted_evaluations:
            match_status = "OK" if se.error == 0 else "NG"
            f.write(f"| {se.detector_id} | {se.gt_count} | {se.est_count} | {se.error} | {match_status} |\n")
        f.write("\n")

        # ====================================================================
        # 6. 誤差分布
        # ====================================================================
        # 誤差ごとのルート数を集計
        error_dist: Dict[int, int] = {}
        for se in result.stay_evaluations:
            err = se.error
            error_dist[err] = error_dist.get(err, 0) + 1

        f.write("### 誤差分布\n\n")
        f.write("| 誤差（人） | ルート数 | 割合 |\n")
        f.write("|-----------|----------|------|\n")
        for err in sorted(error_dist.keys()):
            count = error_dist[err]
            ratio = count / m.total_stays if m.total_stays > 0 else 0
            f.write(f"| {err} | {count} | {ratio:.1%} |\n")
        f.write("\n")


# ============================================================================
# ルート評価詳細 (CSV)
# ============================================================================


def _save_route_evaluations_csv(result: EvaluationResult, filepath: Path) -> None:
    """ルート評価の詳細をCSV形式で保存

    【出力カラム】
    - route: ルート名（時系列情報を含む）
    - gt_count: GT人数
    - est_count: Est人数
    - error: 誤差
    - exact_match: 完全一致か（TRUE/FALSE）
    - gt_trajectory_ids: 該当するGT軌跡ID（セミコロン区切り）
    - est_trajectory_ids: 該当するEst軌跡ID（セミコロン区切り）

    Args:
        result: 評価結果オブジェクト
        filepath: 出力ファイルパス
    """
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        # ====================================================================
        # ヘッダー行
        # ====================================================================
        writer.writerow([
            "route",
            "gt_count",
            "est_count",
            "error",
            "exact_match",
            "gt_trajectory_ids",
            "est_trajectory_ids"
        ])

        # ====================================================================
        # データ行（ルート名でソート）
        # ====================================================================
        sorted_evaluations = sorted(result.stay_evaluations, key=lambda x: x.detector_id)
        for se in sorted_evaluations:
            writer.writerow([
                se.detector_id,                           # ルート名
                se.gt_count,                              # GT人数
                se.est_count,                             # Est人数
                se.error,                                 # 誤差
                "TRUE" if se.error == 0 else "FALSE",     # 完全一致フラグ
                ";".join(se.gt_trajectory_ids),           # GT軌跡ID（セミコロン区切り）
                ";".join(se.est_trajectory_ids)           # Est軌跡ID（セミコロン区切り）
            ])

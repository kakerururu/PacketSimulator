"""評価ログの出力（軌跡ベース）

評価結果をMarkdownとCSVで記録する。
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import List

from ..domain.time_window import EvaluationResult


def save_evaluation_logs(
    result: EvaluationResult,
    log_dir: str = "src2_result/evaluate_log"
) -> dict:
    """評価ログを保存

    Args:
        result: 評価結果
        log_dir: ログ出力ディレクトリ

    Returns:
        保存したファイルパスの辞書
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # タイムスタンプ（ファイル名用）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

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


def _save_summary_markdown(result: EvaluationResult, filepath: Path):
    """サマリーログをMarkdown形式で保存"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("# 軌跡推定の評価ログ（軌跡ベース）\n\n")

        # メタデータ
        f.write("## 評価情報\n\n")
        f.write(f"- **評価日時**: {result.metadata['evaluation_timestamp']}\n")
        f.write(f"- **Ground Truthファイル**: `{result.metadata['ground_truth_file']}`\n")
        f.write(f"- **推定結果ファイル**: `{result.metadata['estimated_file']}`\n")
        f.write(f"- **許容誤差**: {result.metadata['tolerance_seconds']}秒 ({result.metadata['tolerance_seconds']/60:.1f}分)\n")
        f.write(f"- **評価方法**: {result.metadata['evaluation_method']}\n\n")

        # 評価方法の説明
        f.write("## 評価方法\n\n")
        f.write("GT軌跡の**すべての滞在地点**で許容時間内に検出できた場合のみ、その軌跡を正しく推定できたと判定。\n\n")
        f.write("**評価条件**:\n")
        f.write("1. ルートパターンが一致（例: ABCD）\n")
        f.write("2. 滞在数が一致\n")
        f.write("3. すべての滞在地点で検出器IDが一致\n")
        f.write(f"4. すべての滞在で検出時刻が許容範囲内（±{result.metadata['tolerance_seconds']}秒）\n\n")
        f.write("**集計方法**:\n")
        f.write("- ルートパターンごとに集計（例: A→B→C→Dというルート）\n")
        f.write("- GT人数: そのルートを通った実際の人数\n")
        f.write("- Est人数: 上記4条件をすべて満たした推定軌跡の数\n")
        f.write("- 部分的なルートは評価対象外\n\n")

        # 全体指標
        m = result.overall_metrics
        f.write("## 全体評価指標\n\n")
        f.write(f"| 指標 | 値 | 説明 |\n")
        f.write(f"|------|-----|------|\n")
        f.write(f"| 評価したルート数 | {m.total_stays} | ルートパターンの種類数 |\n")
        f.write(f"| GT軌跡総数 | {m.total_gt_count}人 | 全ルート合計のGT人数 |\n")
        f.write(f"| Est軌跡総数（条件満たす） | {m.total_est_count}人 | 4条件を満たしたEst軌跡数 |\n")
        f.write(f"| 総絶対誤差 | {m.total_absolute_error} | 全ルートの誤差の合計 |\n")
        f.write(f"| **MAE** (平均絶対誤差) | **{m.mae:.3f}** | ルートあたりの平均誤差 |\n")
        f.write(f"| **RMSE** (二乗平均平方根誤差) | **{m.rmse:.3f}** | 大きな誤差にペナルティ |\n")
        f.write(f"| **正確一致率** | **{m.exact_match_rate:.1%}** | GT人数==Est人数のルート割合 |\n\n")

        # 指標の説明
        f.write("### 指標の解釈\n\n")
        f.write("- **MAE (Mean Absolute Error)**: ルートあたり平均で何人ずれているか\n")
        f.write("  - 0に近いほど良い\n")
        f.write("  - 例: MAE=0.5 → 平均0.5人のずれ\n\n")
        f.write("- **RMSE (Root Mean Squared Error)**: MAEより大きな誤差に厳しい\n")
        f.write("  - RMSE > MAE の場合、バラつきが大きい\n")
        f.write("  - 0に近いほど良い\n\n")
        f.write("- **正確一致率**: 人数がピッタリ合ったルートの割合\n")
        f.write("  - 1.0 (100%) が理想\n\n")

        # ルートごとの詳細サマリー
        f.write("## ルートごとの評価サマリー\n\n")

        # ルートごとに集計（detector_idにはルート名が入っている）
        route_stats = {}
        for se in result.stay_evaluations:
            route = se.detector_id  # ルート名
            if route not in route_stats:
                route_stats[route] = {"count": 0, "errors": [], "exact_matches": 0}
            route_stats[route]["count"] += 1
            route_stats[route]["errors"].append(se.error)
            if se.error == 0:
                route_stats[route]["exact_matches"] += 1

        f.write("### ルート別の統計\n\n")
        f.write("| ルート | GT人数 | Est人数 | 誤差 | 正確一致 |\n")
        f.write("|--------|--------|---------|------|----------|\n")
        for se in result.stay_evaluations:
            match_status = "✓" if se.error == 0 else "✗"
            f.write(f"| {se.detector_id} | {se.gt_count} | {se.est_count} | {se.error} | {match_status} |\n")
        f.write("\n")

        # 誤差分布
        error_dist = {}
        for se in result.stay_evaluations:
            err = se.error
            error_dist[err] = error_dist.get(err, 0) + 1

        f.write("### 誤差分布\n\n")
        f.write("| 誤差（人） | ルート数 | 割合 |\n")
        f.write("|-----------|----------|------|\n")
        for err in sorted(error_dist.keys()):
            count = error_dist[err]
            ratio = count / m.total_stays
            f.write(f"| {err} | {count} | {ratio:.1%} |\n")
        f.write("\n")


def _save_route_evaluations_csv(result: EvaluationResult, filepath: Path):
    """ルート評価の詳細をCSV形式で保存"""
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)

        # ヘッダー
        writer.writerow([
            "route",
            "gt_count",
            "est_count",
            "error",
            "exact_match",
            "gt_trajectory_ids",
            "est_trajectory_ids"
        ])

        # データ
        for se in result.stay_evaluations:
            writer.writerow([
                se.detector_id,  # ルート名
                se.gt_count,
                se.est_count,
                se.error,
                "TRUE" if se.error == 0 else "FALSE",
                ";".join(se.gt_trajectory_ids),
                ";".join(se.est_trajectory_ids)
            ])

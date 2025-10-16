import numpy as np
from collections import defaultdict
from domain.detector import Detector, load_detectors
from utils.load import load_ground_truth_routes, load_logs, load_simulation_settings
from domain.analysis_results import (
    RouteAnalysisResult,
)
from utils.collect_sort_all_events import (
    collect_and_sort_events,
)
from classify_logic.by_impossible_move import classify_events_by_impossible_move


def analyze_movements_with_clustering(
    logs: list[dict], detectors: dict[str, Detector]
) -> RouteAnalysisResult:  # 戻り値の型を変更
    """
    ログデータからHashed_Payloadごとのイベントを分析し、
    ありえない移動があった場合に新しいクラスタIDを割り当てる。
    """
    # シミュレーション設定を一度だけロード
    simulation_settings = load_simulation_settings("config/simulation_settings.json")
    walker_speed = simulation_settings["walker_speed"]

    # 1. イベントの収集とソート (PayloadEventsCollection オブジェクトを返す)
    events_per_record_per_payload = collect_and_sort_events(logs, detectors)

    # 2. 移動経路のクラスタリング (PayloadEventsCollection オブジェクトを渡す)
    estimated_routes_per_payload = classify_events_by_impossible_move(
        events_per_record_per_payload, detectors, walker_speed
    )

    # 結果を RouteAnalysisResult オブジェクトに格納して返す
    # ClusteredRoutes オブジェクトから辞書を取り出して渡す
    return RouteAnalysisResult(
        estimated_clustered_routes=estimated_routes_per_payload.routes_by_cluster_id
    )


def evaluate_algorithm(
    estimated_clustered_routes: dict, ground_truth_routes: dict, num_detectors: int
) -> dict:
    """
    アルゴリズムの推定結果をグランドトゥルースと比較して評価する。
    推定されたルートがnum_detectorsの数と一致しない場合は評価対象から除外する。
    """
    true_route_counts = defaultdict(int)
    estimated_route_counts = defaultdict(int)

    # グランドトゥルースから真のルートシーケンスの出現回数をカウント
    # グランドトゥルースは常にnum_detectorsの数の検出器を含むルートを想定
    for walker_id, route_str in ground_truth_routes.items():
        if len(route_str) == num_detectors:  # 真のルートは必ずN個の検出器を経由する前提
            true_route_counts[route_str] += 1
    # print(true_route_counts.items())
    # dict_items([('BCDA', 1), ('CDBA', 1), ('BDAC', 1)])

    # 推定されたルートシーケンスの出現回数をカウント
    # ここで、推定されたルートがnum_detectorsの数と一致しない場合は除外
    for cluster_id, route_str in estimated_clustered_routes.items():
        if (
            len(route_str) == num_detectors
        ):  # N個の検出器を経由するルートのみを評価対象とする
            estimated_route_counts[route_str] += 1

    # --- 評価指標の計算 ---
    total_absolute_error = 0
    squared_errors = []
    total_true_route_instances = sum(
        true_route_counts.values()
    )  # 評価対象となる真のルートインスタンスの合計
    num_unique_routes_evaluated = 0

    # 全てのユニークなルートシーケンスを網羅（評価対象のもののみ）
    all_unique_routes = set(true_route_counts.keys()) | set(
        estimated_route_counts.keys()
    )

    results_details = []

    for route_str in sorted(list(all_unique_routes)):
        true_count = true_route_counts.get(route_str, 0)
        estimated_count = estimated_route_counts.get(route_str, 0)

        # Absolute Error
        error = estimated_count - true_count
        abs_error = abs(error)
        total_absolute_error += abs_error
        squared_errors.append(error**2)
        num_unique_routes_evaluated += 1

        results_details.append(
            {
                "Route": route_str,
                "TrueCount": true_count,
                "EstimatedCount": estimated_count,
                "AbsoluteError": abs_error,
            }
        )

    # MAEはユニークなルート数で割る
    mae_per_route = (
        total_absolute_error / num_unique_routes_evaluated
        if num_unique_routes_evaluated > 0
        else 0
    )

    # RMSEの計算
    mse = np.mean(squared_errors) if squared_errors else 0
    rmse = np.sqrt(mse)

    # 追跡率 (Tracking Rate) の計算
    # 全ての真の通行人のうち、ルートが正しく推定された通行人の割合
    # 計算式: Σ min(各ルートの真の人数, 各ルートの推定人数) / (全ウォーカーの総数)
    # 例: 真が5人/推定4人なら4人、真が2人/推定3人なら2人が追跡成功とカウントされる
    correctly_tracked_walkers = sum(
        min(true_route_counts.get(route, 0), estimated_route_counts.get(route, 0))
        for route in all_unique_routes
    )
    tracking_rate = (
        correctly_tracked_walkers / total_true_route_instances
        if total_true_route_instances > 0
        else 0
    )

    return {
        "summary": {
            "TotalUniqueRoutesEvaluated": num_unique_routes_evaluated,
            "TotalTrueRouteInstances": total_true_route_instances,
            "TotalEstimatedRouteInstances": sum(estimated_route_counts.values()),
            "MAE_PerUniqueRoute": mae_per_route,
            "RMSE": f"{rmse:.4f}",
            "TrackingRate": f"{tracking_rate:.4f}",  # 追跡率を追加
        },
        "details": results_details,
    }


def main():
    # データの読み込み
    detectors = load_detectors("config/detectors.json")
    logs = load_logs("result")
    ground_truth_routes = load_ground_truth_routes("result/walker_routes.csv")

    # 移動経路の推定とありえない移動の排除、およびクラスタリング
    analysis_result = analyze_movements_with_clustering(
        logs, detectors
    )  # 戻り値の型を変更
    estimated_clustered_routes = (
        analysis_result.estimated_clustered_routes
    )  # オブジェクトからルートを取得

    print("\n--- 推定結果 (クラスタリング後の推定ルート) ---")
    # クラスタIDごとのルートを出力
    for cluster_id, route_str in sorted(estimated_clustered_routes.items()):
        print(f"クラスタID: {cluster_id}, 推定ルート: {route_str}")
    print(
        f"推定されたユニークな人物（クラスタ）の総数: {len(estimated_clustered_routes)}"
    )
    print("-" * 30)

    # アルゴリズムの評価
    evaluation_results = evaluate_algorithm(
        estimated_clustered_routes, ground_truth_routes, len(detectors)
    )

    print("\n--- 評価結果サマリー (ルートシーケンスごとのカウント) ---")
    for key, value in evaluation_results["summary"].items():
        print(f"{key}: {value}")
    print("\n--- 評価結果詳細 (ユニークなルートシーケンス) ---")
    print(
        "{:<15} {:>10} {:>15} {:>15}".format("ルート", "真の数", "推定数", "絶対誤差")
    )
    print("-" * 60)
    for detail in evaluation_results["details"]:
        print(
            "{:<15} {:>10} {:>15} {:>15}".format(
                detail["Route"],
                detail["TrueCount"],
                detail["EstimatedCount"],
                detail["AbsoluteError"],
            )
        )
    print("-" * 60)


if __name__ == "__main__":
    main()

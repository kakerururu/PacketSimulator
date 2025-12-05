import numpy as np
import os  # osモジュールを追加
from collections import defaultdict
from domain.detector import Detector, load_detectors
from utils.load import (
    load_ground_truth_routes,
    load_logs,
    load_simulation_settings,
)
from utils.choose_classify_logic import choose_classify_logic
from domain.analysis_results import RouteAnalysisResult
from utils.collect_sort_all_records import collect_and_sort_records
from utils.export_payload_records import export_payload_records

# logic_name = "by_impossible_move"
logic_name = "by_impossible_move_and_window"
# logic_name = "window_max"

# データの読み込み
current_dir = os.path.dirname(__file__)
config_dir = os.path.join(current_dir, "../../config")
# result_dir = os.path.join(current_dir, "../../result")
result_dir = os.path.join(current_dir, "../../test_data")  # テストデータで試す場合


def analyze_movements_with_clustering(
    logs: list[dict], detectors: dict[str, Detector]
) -> RouteAnalysisResult:  # 戻り値の型を変更
    """
    ログデータからHashed_Payloadごとのレコードを分析し、
    ありえない移動があった場合に新しいクラスタIDを割り当てる。
    """
    # シミュレーション設定を一度だけロード
    current_dir = os.path.dirname(__file__)
    config_dir = os.path.join(current_dir, "../../config")
    simulation_settings = load_simulation_settings(
        os.path.join(config_dir, "simulation_settings.jsonc")
    )
    walker_speed = simulation_settings["walker_speed"]

    # 1. レコードの収集とソート (PayloadRecordsCollection オブジェクトを返す)
    records_per_record_per_payload = collect_and_sort_records(logs, detectors)
    # 収集・ソート済みレコードをペイロードごとにCSV書き出し
    export_payload_records(
        records_per_record_per_payload,
        # output_dir=os.path.join(current_dir, "../../result/payload_records"),
        output_dir=os.path.join(current_dir, "../../test_data/payload_records"),
        include_index=False,
        gzip_compress=False,
    )

    # 2. 移動経路のクラスタリング (PayloadRecordsCollection オブジェクトを渡す)
    classification_function = choose_classify_logic(logic_name)
    (
        estimated_routes_per_record,
        updated_payload_records_collection,
    ) = classification_function(records_per_record_per_payload, detectors, walker_speed)

    # is_judged が変更されたものをディレクトリに書き出す
    export_payload_records(
        updated_payload_records_collection,
        # output_dir=os.path.join(current_dir, "../../result/judged_payload_records"),
        output_dir=os.path.join(current_dir, "../../test_data/judged_payload_records"),
        include_index=False,
        gzip_compress=False,
    )

    # 結果を RouteAnalysisResult オブジェクトに格納して返す
    # ClusteredRoutes オブジェクトから辞書を取り出して渡す
    return RouteAnalysisResult(
        estimated_clustered_routes=estimated_routes_per_record.routes_by_cluster_id
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
    detectors = load_detectors(os.path.join(config_dir, "detectors.jsonc"))
    logs = load_logs(result_dir)
    # logs = load_logs("test_data")  # テストデータで試す場合
    ground_truth_routes = load_ground_truth_routes(
        os.path.join(result_dir, "walker_routes.csv")
    )
    # ground_truth_routes = load_ground_truth_routes("test_data/walker_routes.csv")

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

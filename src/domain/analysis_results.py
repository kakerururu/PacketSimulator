from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List


@dataclass
class RouteAnalysisResult:
    """
    移動経路分析の結果を保持するデータクラス。
    具体例：{"estimated_clustered_routes": {"cluster_1": "A-B-C", "cluster_2": "A-C-B"}, ...}
    """

    estimated_clustered_routes: Dict[str, str]  # キー: クラスタID, 値: 推定ルート文字列
    # 将来的に、分析中に生成された他の情報（例: 各クラスタのイベント数など）もここに追加できます。


@dataclass
class CollectedEvent:
    """
    _collect_and_sort_events 関数によって収集される個々の検出イベントデータ。
    """

    timestamp: datetime
    detector_id: str
    detector_x: float
    detector_y: float


@dataclass
class PayloadEventsCollection:
    """
    Hashed_Payload ごとに収集され、時間順にソートされたイベントのコレクション。
    具体例：{"payload_1": [event1, event2], "payload_2": [event3], ...}
    """

    events_by_payload: Dict[str, List[CollectedEvent]]


@dataclass
class ClusteredRoutes:
    """
    process_payload_events_for_clustering 関数によって生成される
    Hashed_Payload ごとのクラスタリングされたルートのコレクション。
    """

    routes_by_cluster_id: Dict[str, str]  # キー: クラスタID, 値: 推定ルート文字列

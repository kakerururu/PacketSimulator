"""クラスタリング中の状態を管理するデータクラス"""

from dataclasses import dataclass
from typing import List
from .detection_record import DetectionRecord


@dataclass
class ClusterState:
    """クラスタリング中の状態を保持

    1つのクラスタ（= 1人分の推定経路）を構築する際に必要な情報をまとめる。

    Attributes:
        cluster_id: クラスタの識別子（例: "C_01_integrated_cluster1"）
        cluster_records: このクラスタに属するレコードのリスト
        route_sequence: 推定経路（訪問した検出器IDの順序、例: ["A", "B", "C"]）
        prev_record: 直前に追加したレコード（移動可能性の判定に使用）
    """

    cluster_id: str
    cluster_records: List[DetectionRecord]
    route_sequence: List[str]
    prev_record: DetectionRecord

    def add_record(self, record: DetectionRecord, add_to_route: bool = False) -> None:
        """レコードをcluster_recordsに追加

        Args:
            record: 追加するレコード
            add_to_route: True の場合、推定経路(route_sequence)にも検出器IDを追加
                          （新しい検出器に移動した場合に True にする）。falseだと、
                          検出器IDは追加されない。

        処理内容:
            1. レコードの is_judged を True にマーク（使用済み）
            2. レコードの cluster_id をこのクラスタのIDに設定
            3. cluster_records にレコードを追加
            4. add_to_route=True かつ新しい検出器なら推定経路に検出器IDを追加
            5. prev_record を更新
        """
        # レコードを「使用済み」にマーク
        record.is_judged = True
        record.cluster_id = self.cluster_id

        # cluster_recordsにレコードを追加
        self.cluster_records.append(record)

        # 推定経路への検出器ID追加
        if add_to_route:
            # route_sequence が空、または異なる検出器なら追加
            # （同じ検出器での連続検知は推定経路には追加しない）
            if not self.route_sequence or record.detector_id != self.route_sequence[-1]:
                self.route_sequence.append(record.detector_id)

        # 「直前のレコード」を更新
        self.prev_record = record

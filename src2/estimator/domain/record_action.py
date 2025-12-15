"""クラスタリング時のレコード評価アクション"""

from enum import Enum, auto


class RecordAction(Enum):
    """メインループでの候補レコード評価後に取るべきアクション"""

    # 滞在継続: cluster_recordsにレコードを追加（推定経路には追加しない）
    # 同じ検出器で連続検知された場合
    ADD_AS_STAY = auto()

    # 移動: cluster_recordsにレコードを追加し、推定経路にも検出器IDを追加
    # 新しい検出器への到達可能な移動
    ADD_AS_MOVE = auto()

    # 「ありえない移動」または「滞在時間超過」を検出
    # → 前方探索を開始して、到達可能なレコードを探す
    FORWARD_SEARCH = auto()


class ForwardSearchAction(Enum):
    """前方探索中のレコード評価後に取るべきアクション"""

    # 同じ検出器での滞在継続: cluster_recordsにレコードを追加し、探索を継続
    # （まだ「次の検出器」は見つかっていない）
    ADD_AND_CONTINUE = auto()

    # このレコードをスキップして、探索を継続
    # - 使用済みレコード
    # - ループになる検出器（既に推定経路に含まれる）
    # - シーケンス番号異常
    # - 到達不可能
    SKIP = auto()

    # 到達可能なレコードを発見！探索終了
    FOUND = auto()

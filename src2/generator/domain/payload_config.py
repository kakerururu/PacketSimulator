"""ペイロード設定の型定義"""

from typing import TypedDict, Dict


class PayloadModel(TypedDict):
    """ペイロードモデルの定義

    すべてのモデルは以下のフィールドを持つ：
    - overall_probability: モデル自体の選択確率
    - dynamic_unique_payload: 動的にユニークなペイロードを生成するかのフラグ
    - payload_distribution: 各ペイロードの確率分布
      - ユニーク型の場合は空の辞書 {}
      - その他のモデルの場合はペイロード名と確率の組み合わせを返す

    Examples:
        # ユニーク型モデル
        >>> unique_model: PayloadModel = {
        ...     "overall_probability": 0.20,
        ...     "dynamic_unique_payload": True,
        ...     "payload_distribution": {}
        ... }

        # 限定変動型モデル
        >>> variant_model: PayloadModel = {
        ...     "overall_probability": 0.035,
        ...     "dynamic_unique_payload": False,
        ...     "payload_distribution": {
        ...         "C_01_base_payload": 0.9,
        ...         "C_01_sub_payload": 0.1
        ...     }
        ... }
    """

    overall_probability: float
    dynamic_unique_payload: bool
    payload_distribution: Dict[str, float]


class PayloadDefinitions(TypedDict):
    """全モデルのペイロード定義

    Examples:
        >>> payload_defs: PayloadDefinitions = {
        ...     "Model_Group_A_DynamicUnique": {
        ...         "overall_probability": 0.20,
        ...         "dynamic_unique_payload": True,
        ...         "payload_distribution": {}
        ...     },
        ...     "Model_C_08": {
        ...         "overall_probability": 0.035,
        ...         "dynamic_unique_payload": False,
        ...         "payload_distribution": {
        ...             "C_08_base_payload": 0.9,
        ...             "C_08_sub_payload": 0.1
        ...         }
        ...     }
        ... }
    """

    pass  # モデル名をキーとする辞書（動的なキー）


# 実際の型としてはDict[str, PayloadModel]を使用
PayloadDefinitionsDict = Dict[str, PayloadModel]

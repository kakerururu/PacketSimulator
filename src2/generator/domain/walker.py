from dataclasses import dataclass
from typing import Optional


@dataclass
class Walker:
    """通行人

    シミュレーション上の歩行者。
    各通行人はスマートフォンを持ち、特定のルートを移動する。

    Notes:
        - dynamic_unique_payloadモデルの場合: assigned_hash_IDが設定される（固定）
        - その他のモデル: assigned_hash_IDはNone（レコード生成時に確率分布で選択）

    Examples:
        # ユニーク型モデルの場合
        >>> walker_unique = Walker(
        ...     id="Walker_1",
        ...     model="Model_Group_A_DynamicUnique",
        ...     assigned_hash_ID="DynamicUniquePayload_Walker_Walker_1",
        ...     route="ABCD"
        ... )

        # 一般型・限定変動型・変動型の場合
        >>> walker_general = Walker(
        ...     id="Walker_2",
        ...     model="Model_C_08",
        ...     assigned_hash_ID=None,  # レコード生成時に確率分布で選択
        ...     route="BCDA"
        ... )
    """

    id: str  # 通行人ID（例: "Walker_1", "Walker_2"）
    model: str  # スマートフォンモデル（例: "Model_C_08", "Model_B_01"）
    assigned_hash_ID: Optional[str] = None  # 割り当てられたハッシュID（ユニーク型のみ設定、それ以外はNone）
    route: str = ""  # 移動ルート（例: "ABCD", "BCDA"）

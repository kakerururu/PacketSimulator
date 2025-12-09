from dataclasses import dataclass


@dataclass
class Walker:
    """通行人

    シミュレーション上の歩行者。
    各通行人はスマートフォンを持ち、特定のルートを移動する。

    ペイロードの決定はレコード生成時に行われる：
    - ユニーク型モデル: walker_idに基づいて固定ペイロードを生成
    - その他のモデル: 確率分布に基づいて毎回選択

    Examples:
        >>> walker = Walker(
        ...     id="Walker_1",
        ...     model="Model_C_08",
        ...     route="ABCD"
        ... )
    """

    id: str  # 通行人ID（例: "Walker_1", "Walker_2"）
    model: str  # スマートフォンモデル（例: "Model_C_08", "Model_B_01"）
    route: str = ""  # 移動ルート（例: "ABCD", "BCDA"）

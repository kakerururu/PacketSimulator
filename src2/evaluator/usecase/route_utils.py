"""ルート名生成ユーティリティ

責務: ルート文字列に時系列情報を付与する処理を担当。
     評価時にGT/Est軌跡を時間帯で区別するために使用される。

使用例:
    # GT軌跡の場合
    route_name = create_route_with_timing("ABCD", gt_traj.stays)
    # → "ABCD_0900-0910_1000-1010_1100-1110_1200-1210"

    # Est軌跡の場合も同様に動作
    route_name = create_route_with_timing("ABCD", est_traj.stays)
"""

from typing import List, Any


def create_route_with_timing(route: str, stays: List[Any]) -> str:
    """ルート名に時系列情報を付与する

    【目的】
    同じ空間ルート（例: ABCD）でも、異なる時間帯に通過した場合を
    区別できるようにする。これにより、評価時に「いつ」その経路を
    通ったかを考慮したマッチングが可能になる。

    【処理フロー】
    1. stays リストを順に走査
    2. 各 stay の時刻情報を "HHMM-HHMM" 形式で抽出
       - GT: arrival_time / departure_time
       - Est: first_detection / last_detection
    3. アンダースコアで連結してルート名に付与

    【入力例】
    route = "ABCD"
    stays = [
        Stay(detector="A", arrival=09:00, departure=09:10),
        Stay(detector="B", arrival=10:00, departure=10:10),
        Stay(detector="C", arrival=11:00, departure=11:10),
        Stay(detector="D", arrival=12:00, departure=12:10),
    ]

    【出力例】
    "ABCD_0900-0910_1000-1010_1100-1110_1200-1210"

    Args:
        route: 空間的なルートパターン（例: "ABCD", "DCBA"）
        stays: 滞在情報のリスト。以下のいずれかの属性を持つ:
               - arrival_time / departure_time (GT軌跡)
               - first_detection / last_detection (Est軌跡)

    Returns:
        時系列情報を含むルート名
        フォーマット: "{route}_{時刻1}_{時刻2}_..."

    Note:
        - stays が空の場合は "{route}_" を返す
        - 時刻は24時間表記（例: 0900, 1430, 2359）
    """
    # ============================================================
    # 各滞在の時刻情報を抽出
    # ============================================================
    time_parts = []  # ["0900-0910", "1000-1010", ...] 形式で格納

    for stay in stays:
        # ----------------------------------------------------------
        # GT軌跡の場合: arrival_time / departure_time 属性を使用
        # ----------------------------------------------------------
        if hasattr(stay, 'arrival_time') and hasattr(stay, 'departure_time'):
            # datetime → "HHMM" 形式の文字列に変換
            start = stay.arrival_time.strftime("%H%M")   # 例: "0900"
            end = stay.departure_time.strftime("%H%M")   # 例: "0910"
            time_parts.append(f"{start}-{end}")          # 例: "0900-0910"

        # ----------------------------------------------------------
        # Est軌跡の場合: first_detection / last_detection 属性を使用
        # ----------------------------------------------------------
        elif hasattr(stay, 'first_detection') and hasattr(stay, 'last_detection'):
            # datetime → "HHMM" 形式の文字列に変換
            start = stay.first_detection.strftime("%H%M")  # 例: "0902"
            end = stay.last_detection.strftime("%H%M")     # 例: "0908"
            time_parts.append(f"{start}-{end}")            # 例: "0902-0908"

    # ============================================================
    # ルート名と時刻情報を連結して返す
    # ============================================================
    # 例: ["0900-0910", "1000-1010"] → "0900-0910_1000-1010"
    time_str = "_".join(time_parts)

    # 例: "ABCD" + "_" + "0900-0910_1000-1010" → "ABCD_0900-0910_1000-1010"
    return f"{route}_{time_str}"

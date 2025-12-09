"""日時処理ユーティリティ"""

from datetime import datetime


def format_timestamp(dt: datetime) -> str:
    """タイムスタンプをミリ秒まで出力 (YYYY-MM-DD HH:MM:SS.mmm)

    Args:
        dt: datetime オブジェクト

    Returns:
        フォーマットされたタイムスタンプ文字列

    Examples:
        >>> from datetime import datetime
        >>> dt = datetime(2024, 1, 14, 11, 0, 5, 123000)
        >>> format_timestamp(dt)
        '2024-01-14 11:00:05.123'
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def parse_timestamp(ts_str: str) -> datetime:
    """タイムスタンプ文字列をパース

    Args:
        ts_str: タイムスタンプ文字列 (ミリ秒あり/なし両対応)

    Returns:
        datetime オブジェクト

    Examples:
        >>> parse_timestamp("2024-01-14 11:00:05.123")
        datetime.datetime(2024, 1, 14, 11, 0, 5, 123000)
        >>> parse_timestamp("2024-01-14 11:00:05")
        datetime.datetime(2024, 1, 14, 11, 0, 5)
    """
    try:
        # ミリ秒ありのフォーマット
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        # ミリ秒なしのフォーマット
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")

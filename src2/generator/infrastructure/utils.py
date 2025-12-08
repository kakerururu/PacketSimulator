"""Infrastructure層の共通ユーティリティ"""
from datetime import datetime


def format_timestamp(dt: datetime) -> str:
    """タイムスタンプをミリ秒まで出力

    Args:
        dt: datetime オブジェクト

    Returns:
        フォーマットされた文字列 (YYYY-MM-DD HH:MM:SS.mmm)

    Examples:
        >>> from datetime import datetime
        >>> format_timestamp(datetime(2024, 1, 14, 11, 0, 5, 123000))
        '2024-01-14 11:00:05.123'
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

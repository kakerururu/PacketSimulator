def choose_classify_logic(logic_name):
    """
    指定されたロジック名に基づいて分類関数を返す。
    """
    if logic_name == "by_impossible_move":
        from classify_logic.by_impossible_move import (
            classify_records_by_impossible_move,
        )

        return classify_records_by_impossible_move

    elif logic_name == "by_impossible_move_and_window":
        from classify_logic.by_impossible_move_and_window import (
            classify_records_by_impossible_move_and_window,
        )

        return classify_records_by_impossible_move_and_window

    elif logic_name == "window_max":
        from classify_logic.window_max import classify_records_window_max

        return classify_records_window_max

    else:
        raise ValueError(f"未知の分類ロジック名: {logic_name}")

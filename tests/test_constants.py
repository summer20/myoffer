from app.constants import merge_options, DEFAULT_INDUSTRIES


def test_merge_options_keeps_defaults_first_and_appends_new_sorted():
    result = merge_options(["互联网", "游戏"], ["互联网", "金融", "教育"])
    assert result == ["互联网", "游戏", "教育", "金融"]


def test_merge_options_strips_and_ignores_blank_values():
    result = merge_options(["互联网"], ["  ", "", "互联网", " 金融 "])
    assert result == ["互联网", "金融"]


def test_default_industries_is_nonempty():
    assert len(DEFAULT_INDUSTRIES) > 0

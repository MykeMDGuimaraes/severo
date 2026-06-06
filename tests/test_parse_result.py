def test_parse_result_defaults():
    from channels.base import ParseResult
    r = ParseResult(action="process", user_id="5511999", text="oi", message_id="ABC")
    assert r.action == "process"
    assert r.user_id == "5511999"
    assert r.text == "oi"
    assert r.message_id == "ABC"
    assert r.reason == ""


def test_parse_result_ignore():
    from channels.base import ParseResult
    r = ParseResult(action="ignore", reason="group")
    assert r.action == "ignore"
    assert r.reason == "group"
    assert r.user_id == ""

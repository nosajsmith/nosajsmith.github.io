from server.protocol import mk_ok, mk_err, normalize_request


def test_mk_ok_shape():
    resp = mk_ok("123", {"a": 1})
    assert resp["ok"] is True
    assert resp["req_id"] == "123"
    assert resp["payload"]["a"] == 1
    assert "v" in resp


def test_mk_err_shape():
    resp = mk_err("123", "x", "boom")
    assert resp["ok"] is False
    assert resp["req_id"] == "123"
    assert resp["error"]["code"] == "x"
    assert resp["error"]["message"] == "boom"
    assert "v" in resp


def test_normalize_request_happy():
    msg = {"cmd": "ping", "req_id": "abc", "payload": {}, "v": "1.0"}
    norm = normalize_request(msg)
    assert norm["cmd"] == "ping"
    assert norm["req_id"] == "abc"
    assert isinstance(norm["payload"], dict)


def test_normalize_request_rejects_bad_cmd():
    try:
        normalize_request({"cmd": "", "req_id": "x", "payload": {}})
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_normalize_request_rejects_non_dict_payload():
    try:
        normalize_request({"cmd": "ping", "req_id": "x", "payload": []})
        assert False, "expected ValueError"
    except ValueError:
        pass

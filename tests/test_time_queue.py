from server.sim_time import SimTime
from server.event_queue import EventQueue
from server.orders_v1 import make_order_event


def test_sim_time_advances():
    t = SimTime()
    assert t.now() == 0
    t.advance(6)
    assert t.now() == 6


def test_event_queue_resolves():
    q = EventQueue()
    q.schedule({"resolve_at": 10, "type": "x"})
    q.schedule({"resolve_at": 5, "type": "y"})
    ready = q.resolve_up_to(6)
    assert len(ready) == 1
    assert ready[0]["type"] == "y"
    assert len(q.pending()) == 1


def test_make_order_event():
    ev = make_order_event(kind="attack", unit_id="U1", issued_at=12, eta_hours=6, intent="go")
    assert ev["resolve_at"] == 18
    assert ev["type"] == "order"

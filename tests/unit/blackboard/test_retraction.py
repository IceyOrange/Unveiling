from __future__ import annotations

from blackboard.retraction import resolve_cascade
from blackboard.store import BlackboardStore
from models.blackboard import BlackboardRecord
from models.state import State


def test_resolve_cascade_linear_chain():
    a = BlackboardRecord(author="test")
    b = BlackboardRecord(author="test", references=[a.id])
    c = BlackboardRecord(author="test", references=[b.id])
    state = State()
    state.schedule_log.extend([a, b, c])
    store = BlackboardStore(state)
    affected = resolve_cascade(store, a.id)
    assert b.id in affected
    assert c.id in affected
    assert a.id not in affected


def test_resolve_cascade_diamond():
    a = BlackboardRecord(author="test")
    b = BlackboardRecord(author="test", references=[a.id])
    c = BlackboardRecord(author="test", references=[a.id])
    d = BlackboardRecord(author="test", references=[b.id, c.id])
    state = State()
    state.schedule_log.extend([a, b, c, d])
    store = BlackboardStore(state)
    affected = resolve_cascade(store, a.id)
    assert set(affected) == {b.id, c.id, d.id}


def test_resolve_cascade_no_dependents():
    a = BlackboardRecord(author="test")
    state = State()
    state.schedule_log.append(a)
    store = BlackboardStore(state)
    assert resolve_cascade(store, a.id) == []


def test_resolve_cascade_circular_refs():
    a = BlackboardRecord(author="test")
    b = BlackboardRecord(author="test", references=[a.id])
    # circular: a references b (unusual but tests safety)
    a_copy = BlackboardRecord(author="test", id=a.id, references=[b.id])
    state = State()
    state.schedule_log.extend([a, b, a_copy])
    store = BlackboardStore(state)
    affected = resolve_cascade(store, a.id)
    # Should terminate without infinite loop
    assert b.id in affected

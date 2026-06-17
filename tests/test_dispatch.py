from staunchpad import dispatch
from staunchpad.dispatch import JobQueue


def test_submit_and_read(tmp_path):
    q = JobQueue(tmp_path)
    jid = q.submit("hello", button=(0, 1), label="greet")
    job = q.read(jid)
    assert job.prompt == "hello"
    assert job.button == (0, 1)        # round-trips back to a tuple
    assert job.label == "greet"
    assert job.status == dispatch.PENDING
    assert not job.is_terminal


def test_lifecycle(tmp_path):
    q = JobQueue(tmp_path)
    jid = q.submit("do a thing")
    assert [j.id for j in q.pending()] == [jid]

    assert q.claim(q.read(jid)) is True          # pending -> running
    assert q.status(jid) == dispatch.RUNNING
    assert q.pending() == []                      # no longer pending
    assert q.claim(q.read(jid)) is False          # can't re-claim

    q.set_status(jid, dispatch.DONE, result="ok")
    job = q.read(jid)
    assert job.status == dispatch.DONE and job.result == "ok"
    assert job.finished is not None and job.is_terminal


def test_archive(tmp_path):
    q = JobQueue(tmp_path)
    jid = q.submit("x")
    q.archive(jid)
    assert q.read(jid) is None


def test_atomic_write_leaves_no_tmp(tmp_path):
    q = JobQueue(tmp_path)
    q.submit("x")
    assert list(tmp_path.glob("*.tmp")) == []
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_color_dim():
    from staunchpad import color
    assert color.rgb(40, 20, 0).dimmed(0.5) == color.rgb(20, 10, 0)
    assert color.rgb(10, 10, 10).dimmed(0) == color.rgb(0, 0, 0)   # dark, not palette OFF
    assert not color.rgb(10, 10, 10).dimmed(0)                     # ...but still falsy
    # palette colours are returned unchanged (can't scale precisely)
    assert color.RED.dimmed(0.5) == color.RED

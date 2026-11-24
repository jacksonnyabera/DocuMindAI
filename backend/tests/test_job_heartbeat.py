from unittest.mock import MagicMock
from uuid import uuid4

from app.services.job_heartbeat import JobLeaseHeartbeat


def make_heartbeat(rowcount=1):
    session_factory = MagicMock()
    db = session_factory.return_value.__enter__.return_value
    db.execute.return_value.rowcount = rowcount

    heartbeat = JobLeaseHeartbeat(
        session_factory=session_factory,
        job_id=uuid4(),
        worker_id="worker-test",
        interval_seconds=60,
    )

    return heartbeat, session_factory, db


def test_heartbeat_renews_owned_job():
    heartbeat, session_factory, db = make_heartbeat(rowcount=1)

    assert heartbeat.renew() is True
    assert heartbeat.lease_lost is False

    session_factory.assert_called_once()
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_heartbeat_detects_lost_lease():
    heartbeat, _, db = make_heartbeat(rowcount=0)

    assert heartbeat.renew() is False
    assert heartbeat.lease_lost is True
    db.commit.assert_called_once()


def test_heartbeat_does_not_report_success_on_database_error():
    heartbeat, _, db = make_heartbeat()
    db.execute.side_effect = RuntimeError("database unavailable")

    assert heartbeat.renew() is False
    assert heartbeat.lease_lost is False
    db.commit.assert_not_called()


def test_heartbeat_thread_stops_when_context_exits():
    heartbeat, _, _ = make_heartbeat()

    with heartbeat:
        assert heartbeat._thread is not None
        assert heartbeat._thread.is_alive()

    assert heartbeat._stop_event.is_set()
    assert heartbeat._thread is not None
    assert not heartbeat._thread.is_alive()

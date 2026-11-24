"""
RASTATIME 2026-11-24 - the CBA link mail after a finished upload
(backend/rastatime_worker/archive_jobs.py send_link_mail).  No database and
no SMTP: the cc_pref reads, the producer query and the sender are replaced.
"""

from __future__ import annotations

import pytest

from backend.rastatime_worker import archive_jobs as J
from backend.rastatime_worker import cba

PREFS_ON = {
    "cba_link_mail_enabled": "true",
    "alerts_smtp_host": "mail.example",
    "alerts_mail_from": "studio@example",
    "station_name": "Radio Test",
}


class FakeDb:
    def __init__(self, prefs, producers, columns=True):
        self.prefs = prefs
        self.producers = producers
        self.columns = columns
        self.updates = []

    def pref(self, key):
        return self.prefs.get(key)

    def rows(self, sql, params=None):
        if "cc_editor_profile" in sql:
            return [{"name": n, "email": e} for n, e in self.producers]
        if "FROM cc_pref" in sql:
            return [
                {"keystr": k, "valstr": v} for k, v in self.prefs.items() if k.startswith("alerts_")
            ]
        if "information_schema.columns" in sql:
            return [{"n": 1 if self.columns else 0}]
        raise AssertionError(sql)

    def execute(self, sql, params=None):
        self.updates.append((sql, params))
        return 1


@pytest.fixture
def db(monkeypatch):
    def make(prefs=None, producers=(("Ann", "ann@example"), ("Bo", "bo@example")), columns=True):
        fake = FakeDb(dict(PREFS_ON if prefs is None else prefs), list(producers), columns)
        monkeypatch.setattr(J, "_pref", fake.pref)
        monkeypatch.setattr(J, "_rows", fake.rows)
        monkeypatch.setattr(J, "_execute", fake.execute)
        return fake

    return make


class Spy:
    def __init__(self, fail_for=()):
        self.mails = []
        self.fail_for = fail_for

    def __call__(self, settings, subject, body, recipients=None):
        if recipients[0] in self.fail_for:
            raise OSError("refused")
        self.mails.append((recipients, subject, body))


EP = cba.Episode(show_name="Morning Show", starts_local="2026-11-24 08:00:00", status="publish")
META = {"title": "Episode One"}
JOB = {"id": 7, "instance_id": 30801}


def test_off_by_default(db):
    fake = db(prefs={})
    spy = Spy()
    assert J.send_link_mail(JOB, EP, META, 4711, sender=spy) is None
    assert spy.mails == [] and fake.updates == []


def test_one_mail_per_producer_with_the_link(db):
    fake = db()
    spy = Spy()
    note = J.send_link_mail(JOB, EP, META, 4711, sender=spy)
    assert note == "link e-mailed to ann@example, bo@example"
    assert [m[0] for m in spy.mails] == [["ann@example"], ["bo@example"]]
    subject, body = spy.mails[0][1], spy.mails[0][2]
    assert subject == "Morning Show: the episode of 2026-11-24 is online"
    assert "Hello Ann," in body and "https://cba.media/?p=4711" in body
    assert '"Episode One"' in body and "(2026-11-24 08:00)" in body and "Radio Test" in body
    assert "private" not in body
    assert fake.updates and fake.updates[0][1] == [note, 7]


def test_own_texts_and_unknown_braces(db):
    db(
        prefs=dict(
            PREFS_ON,
            cba_link_mail_subject="Online: {title}",
            cba_link_mail_body="Hallo {name}, {link} {unknown}",
        )
    )
    spy = Spy()
    J.send_link_mail(JOB, EP, META, 9, sender=spy)
    assert spy.mails[1][1] == "Online: Episode One"
    assert spy.mails[1][2] == "Hallo Bo, https://cba.media/?p=9 {unknown}"


def test_private_post_gets_the_note(db):
    db()
    spy = Spy()
    ep = cba.Episode(show_name="Morning Show", starts_local="2026-11-24 08:00:00", status="private")
    J.send_link_mail(JOB, ep, META, 1, sender=spy)
    assert spy.mails[0][2].endswith(J.LINK_MAIL_PRIVATE)


def test_no_producer_address(db):
    fake = db(producers=())
    spy = Spy()
    note = J.send_link_mail(JOB, EP, META, 1, sender=spy)
    assert "no active producer" in note and spy.mails == []
    assert fake.updates[0][1][0] == note


def test_smtp_missing(db):
    db(prefs={"cba_link_mail_enabled": "true"})
    spy = Spy()
    note = J.send_link_mail(JOB, EP, META, 1, sender=spy)
    assert "SMTP server or sender missing" in note and spy.mails == []


def test_one_failed_address_does_not_stop_the_others(db):
    db()
    spy = Spy(fail_for=("ann@example",))
    note = J.send_link_mail(JOB, EP, META, 1, sender=spy)
    assert note == "link e-mailed to bo@example; link e-mail failed: ann@example (OSError)"


def test_before_the_migration_nothing_is_written(db):
    fake = db(columns=False)
    J.send_link_mail(JOB, EP, META, 1, sender=Spy())
    assert fake.updates == []


def test_never_raises(db, monkeypatch):
    db()

    def boom(_):
        raise RuntimeError("db gone")

    monkeypatch.setattr(J, "producer_addresses", boom)
    assert (
        J.send_link_mail(JOB, EP, META, 1, sender=Spy()) == "link e-mail failed: unexpected error"
    )


def test_fill_template():
    assert J.fill_template("{a} {name}", {"name": "X"}) == "{a} X"
    assert J.post_link(12) == "https://cba.media/?p=12"

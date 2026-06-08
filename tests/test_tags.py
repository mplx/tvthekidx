import pytest

from tvthekidx import migration
from tvthekidx.database import addFileToDb, create_or_get_collection
from tvthekidx.tags import tag_add, tag_list, tag_delete, tag_delete_all, tag_scanfiles


@pytest.fixture
def db(tmp_path):
    conn = migration.initialize_db(str(tmp_path / "tags.db"))
    yield conn
    conn.close()


class TestTagAdd:
    def test_returns_tag_and_regex_id(self, db):
        tid, rid = tag_add(db, "action", r"\baction\b")
        assert tid is not None and rid is not None

    def test_same_tag_twice_is_idempotent(self, db):
        tid1, rid1 = tag_add(db, "comedy", r"\bcomedy\b")
        tid2, rid2 = tag_add(db, "comedy", r"\bcomedy\b")
        assert tid1 == tid2
        assert rid1 == rid2

    def test_second_regex_on_same_tag(self, db):
        tid1, _ = tag_add(db, "german", r"\[ard\]")
        tid2, _ = tag_add(db, "german", r"\[zdf\]")
        assert tid1 == tid2
        rows = tag_list(db, includeRegex=True)
        assert len([r for r in rows if r["tag"] == "german"]) == 2


class TestTagList:
    def test_empty_database(self, db):
        assert tag_list(db) == []

    def test_lists_added_tag(self, db):
        tag_add(db, "drama", r"\bdrama\b")
        rows = tag_list(db)
        assert len(rows) == 1
        assert rows[0]["tag"] == "drama"

    def test_includes_regex_when_requested(self, db):
        tag_add(db, "scifi", r"\bscifi\b")
        rows = tag_list(db, includeRegex=True)
        assert rows[0]["regex"] == r"\bscifi\b"

    def test_ordered_by_tag(self, db):
        tag_add(db, "zzz", r"\bzzz\b")
        tag_add(db, "aaa", r"\baaa\b")
        rows = tag_list(db)
        assert rows[0]["tag"] == "aaa"
        assert rows[1]["tag"] == "zzz"


class TestTagDelete:
    def test_delete_removes_tag(self, db):
        tag_add(db, "horror", r"\bhorror\b")
        assert tag_delete(db, "horror") is True
        assert tag_list(db) == []

    def test_delete_nonexistent_returns_false(self, db):
        assert tag_delete(db, "nonexistent") is False

    def test_delete_specific_regex_keeps_tag(self, db):
        tag_add(db, "news", r"\bnews\b")
        tag_add(db, "news", r"\bnachrichten\b")
        tag_delete(db, "news", r"\bnews\b")
        rows = tag_list(db, includeRegex=True)
        assert len(rows) == 1
        assert rows[0]["regex"] == r"\bnachrichten\b"
        assert rows[0]["tag"] == "news"


class TestTagDeleteAll:
    def test_clears_all_tags(self, db):
        tag_add(db, "a", r"\ba\b")
        tag_add(db, "b", r"\bb\b")
        tag_delete_all(db)
        assert tag_list(db) == []


class TestTagScanfiles:
    def test_matching_file_gets_tagged(self, db):
        col_id, _ = create_or_get_collection(db, "col")
        addFileToDb(db, col_id, "Die Hard (1988).mkv", "/movies")
        addFileToDb(db, col_id, "Shrek (2001).mkv", "/movies")
        db.commit()
        tid, _ = tag_add(db, "action", r"Die Hard")
        tag_scanfiles(db, "action")
        count = db.execute(
            "SELECT COUNT(*) FROM files_tags WHERE t_id=?", (tid,)
        ).fetchone()[0]
        assert count == 1

    def test_scan_by_integer_id(self, db):
        col_id, _ = create_or_get_collection(db, "col")
        addFileToDb(db, col_id, "Alien (1979).mkv", "/movies")
        db.commit()
        tid, _ = tag_add(db, "scifi", r"Alien")
        tag_scanfiles(db, tid)
        count = db.execute(
            "SELECT COUNT(*) FROM files_tags WHERE t_id=?", (tid,)
        ).fetchone()[0]
        assert count == 1

    def test_non_matching_file_not_tagged(self, db):
        col_id, _ = create_or_get_collection(db, "col")
        addFileToDb(db, col_id, "Bambi (1942).mkv", "/movies")
        db.commit()
        tid, _ = tag_add(db, "scifi", r"Alien")
        tag_scanfiles(db, "scifi")
        count = db.execute(
            "SELECT COUNT(*) FROM files_tags WHERE t_id=?", (tid,)
        ).fetchone()[0]
        assert count == 0

    def test_multiple_regex_patterns(self, db):
        col_id, _ = create_or_get_collection(db, "col")
        addFileToDb(db, col_id, "Tagesschau (2023) {ard}.mkv", "/news")
        addFileToDb(db, col_id, "ZDF Heute (2023) {zdf}.mkv", "/news")
        addFileToDb(db, col_id, "Shrek (2001).mkv", "/movies")
        db.commit()
        tid, _ = tag_add(db, "news", r"\{ard\}")
        tag_add(db, "news", r"\{zdf\}")
        tag_scanfiles(db, "news")
        count = db.execute(
            "SELECT COUNT(*) FROM files_tags WHERE t_id=?", (tid,)
        ).fetchone()[0]
        assert count == 2

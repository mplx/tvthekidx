import pytest

from tvthekidx.database import (
    initialize_db,
    addMovieToDb, addActorToDb, addActorToMovieDb,
    addFileToDb, get_file_id,
    add_file_attachment, get_file_attachments,
    count_file_attachments, delete_file_attachments,
    add_movie_attachment, get_movie_attachments,
    add_actor_attachment, get_actor_attachments,
    addGenreToDb, addGenreToMovieDb, getGenres_bulk,
    getCast, cleanup_db,
)

_MOVIE = {
    'tmdb_id': 12345,
    'title': 'Test Movie',
    'orig_title': 'Test Movie Original',
    'release_year': 2023,
    'description': 'A description.',
    'popularity': 7.5,
    'score': 75.0,
    'poster': None,
}

_ACTOR = {
    'tmdb_id': 9001,
    'name': 'Test Actor',
    'popularity': 20.0,
    'profile': None,
}


@pytest.fixture
def db(tmp_path):
    conn = initialize_db(str(tmp_path / "test.db"))
    yield conn
    conn.close()


class TestInitializeDb:
    def test_returns_connection(self, tmp_path):
        conn = initialize_db(str(tmp_path / "new.db"))
        assert conn is not None
        conn.close()

    def test_required_tables_exist(self, db):
        cur = db.cursor()
        for table in ("movies", "files", "actors", "actors_movies",
                      "crew_movies", "attachments", "tags", "tags_regex",
                      "files_tags", "settings", "genres", "movies_genres"):
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,)
            )
            assert cur.fetchone() is not None, f"Missing table: {table}"

    def test_schema_version_is_9(self, db):
        cur = db.cursor()
        cur.execute("SELECT value_int FROM settings WHERE dbkey='dbversion'")
        assert cur.fetchone()[0] == 9

    def test_existing_db_reopens(self, tmp_path):
        path = str(tmp_path / "existing.db")
        c1 = initialize_db(path)
        c1.close()
        c2 = initialize_db(path)
        assert c2 is not None
        c2.close()


class TestMovies:
    def test_add_returns_integer_id(self, db):
        mid = addMovieToDb(db, _MOVIE)
        assert isinstance(mid, int) and mid > 0

    def test_fields_stored_correctly(self, db):
        mid = addMovieToDb(db, _MOVIE)
        row = db.execute("SELECT * FROM movies WHERE id=?", (mid,)).fetchone()
        assert row["title"] == "Test Movie"
        assert row["year"] == 2023
        assert row["tmdb_id"] == 12345

    def test_title_normalized(self, db):
        mid = addMovieToDb(db, dict(_MOVIE, title="Müller", tmdb_id=99991))
        row = db.execute("SELECT title_normalized FROM movies WHERE id=?", (mid,)).fetchone()
        assert row[0] == "Muller"

    def test_oid_assigned(self, db):
        mid = addMovieToDb(db, _MOVIE)
        row = db.execute("SELECT oid FROM movies WHERE id=?", (mid,)).fetchone()
        assert row[0] is not None

    def test_poster_stored_as_attachment(self, db):
        mid = addMovieToDb(db, dict(_MOVIE, poster=b"FAKEIMAGE"))
        rows = get_movie_attachments(db, mid, "poster")
        assert len(rows) == 1
        assert bytes(rows[0]["data"]) == b"FAKEIMAGE"

    def test_cleanup_returns_true(self, db):
        assert cleanup_db(db) is True


class TestActors:
    def test_add_returns_integer_id(self, db):
        aid = addActorToDb(db, _ACTOR)
        assert isinstance(aid, int) and aid > 0

    def test_add_idempotent(self, db):
        aid1 = addActorToDb(db, _ACTOR)
        aid2 = addActorToDb(db, _ACTOR)
        assert aid1 == aid2

    def test_link_to_movie(self, db):
        mid = addMovieToDb(db, _MOVIE)
        aid = addActorToDb(db, _ACTOR)
        db.commit()
        addActorToMovieDb(db, mid, aid)
        cast = getCast(db, mid)
        assert len(cast) == 1
        assert cast[0]["name"] == "Test Actor"

    def test_profile_stored_as_attachment(self, db):
        aid = addActorToDb(db, dict(_ACTOR, profile=b"PROFILEDATA"))
        rows = get_actor_attachments(db, aid, "profile")
        assert len(rows) == 1
        assert bytes(rows[0]["data"]) == b"PROFILEDATA"


class TestFiles:
    def test_add_new_returns_true(self, db):
        assert addFileToDb(db, "Col", "movie.mkv", "/p") is True

    def test_add_duplicate_returns_row(self, db):
        addFileToDb(db, "Col", "movie.mkv", "/p")
        result = addFileToDb(db, "Col", "movie.mkv", "/p")
        assert result is not True

    def test_get_file_id(self, db):
        addFileToDb(db, "Col", "film.mp4", "/media")
        fid = get_file_id(db, "Col", "film.mp4", "/media")
        assert isinstance(fid, int) and fid > 0

    def test_get_file_id_missing_returns_none(self, db):
        assert get_file_id(db, "Col", "ghost.mp4", "/media") is None


class TestAttachments:
    @pytest.fixture
    def file_id(self, db):
        addFileToDb(db, "Col", "f.mkv", "/p")
        return get_file_id(db, "Col", "f.mkv", "/p")

    def test_add_and_retrieve(self, db, file_id):
        add_file_attachment(db, file_id, "screenshot", b"\xff\xd8\xff")
        rows = get_file_attachments(db, file_id, "screenshot")
        assert len(rows) == 1
        assert bytes(rows[0]["data"]) == b"\xff\xd8\xff"

    def test_count(self, db, file_id):
        add_file_attachment(db, file_id, "screenshot", b"a")
        add_file_attachment(db, file_id, "screenshot", b"b")
        assert count_file_attachments(db, file_id, "screenshot") == 2

    def test_count_all_types(self, db, file_id):
        add_file_attachment(db, file_id, "screenshot", b"a")
        add_file_attachment(db, file_id, "thumb", b"b")
        assert count_file_attachments(db, file_id) == 2

    def test_delete_by_type(self, db, file_id):
        add_file_attachment(db, file_id, "screenshot", b"x")
        delete_file_attachments(db, file_id, "screenshot")
        assert count_file_attachments(db, file_id, "screenshot") == 0

    def test_delete_all(self, db, file_id):
        add_file_attachment(db, file_id, "screenshot", b"x")
        add_file_attachment(db, file_id, "thumb", b"y")
        delete_file_attachments(db, file_id)
        assert count_file_attachments(db, file_id) == 0

    def test_movie_attachment(self, db):
        mid = addMovieToDb(db, _MOVIE)
        add_movie_attachment(db, mid, "poster", b"POSTER")
        rows = get_movie_attachments(db, mid, "poster")
        assert len(rows) == 1
        assert bytes(rows[0]["data"]) == b"POSTER"


class TestGenres:
    def test_add_genre_returns_id(self, db):
        gid = addGenreToDb(db, 28, "Action")
        assert isinstance(gid, int) and gid > 0

    def test_add_genre_idempotent(self, db):
        gid1 = addGenreToDb(db, 28, "Action")
        gid2 = addGenreToDb(db, 28, "Action")
        assert gid1 == gid2

    def test_add_genre_to_movie(self, db):
        mid = addMovieToDb(db, _MOVIE)
        db.commit()
        gid = addGenreToDb(db, 28, "Action")
        addGenreToMovieDb(db, mid, gid)
        db.commit()
        rows = getGenres_bulk(db, [mid])
        assert mid in rows
        assert rows[mid][0]["name"] == "Action"

    def test_add_genre_to_movie_idempotent(self, db):
        mid = addMovieToDb(db, _MOVIE)
        db.commit()
        gid = addGenreToDb(db, 28, "Action")
        addGenreToMovieDb(db, mid, gid)
        addGenreToMovieDb(db, mid, gid)
        db.commit()
        rows = getGenres_bulk(db, [mid])
        assert len(rows[mid]) == 1

    def test_get_genres_bulk_empty(self, db):
        assert getGenres_bulk(db, []) == {}

    def test_get_genres_bulk_multiple_movies(self, db):
        mid1 = addMovieToDb(db, _MOVIE)
        mid2 = addMovieToDb(db, dict(_MOVIE, title="Other", tmdb_id=99999))
        db.commit()
        gid_action = addGenreToDb(db, 28, "Action")
        gid_drama = addGenreToDb(db, 18, "Drama")
        addGenreToMovieDb(db, mid1, gid_action)
        addGenreToMovieDb(db, mid2, gid_drama)
        db.commit()
        rows = getGenres_bulk(db, [mid1, mid2])
        assert rows[mid1][0]["name"] == "Action"
        assert rows[mid2][0]["name"] == "Drama"

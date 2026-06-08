import pytest

from tvthekidx import migration
from tvthekidx.database import (
    addTVShowToDb, addSeasonToDb, addEpisodeToDb,
    addActorToDb, addActorToTVShowDb, addCrewToTVShowDb,
    addGenreToDb, addGenreToTVShowDb,
    assignEpisodeToFile, addFileToDb,
    getTVShows, getTVSeasons_bulk, getEpisodes_bulk,
    getEpisodeFiles_bulk, getTVCast_bulk, getTVCrew_bulk,
    getTVShowsByActor_bulk, getTVGenres_bulk,
    create_or_get_collection,
)

_SHOW = {
    'tmdb_id': 54321,
    'title': 'Test Show',
    'orig_title': 'Test Show Original',
    'year': 2022,
    'description': 'A TV series.',
    'popularity': 5.0,
    'score': 70.0,
    'poster': None,
}

_ACTOR = {
    'tmdb_id': 8001,
    'name': 'Show Actor',
    'popularity': 15.0,
    'profile': None,
}


@pytest.fixture
def db(tmp_path):
    conn = migration.initialize_db(str(tmp_path / "tv.db"))
    yield conn
    conn.close()


@pytest.fixture
def show_id(db):
    return addTVShowToDb(db, _SHOW)


@pytest.fixture
def season_id(db, show_id):
    return addSeasonToDb(db, show_id, _SHOW['tmdb_id'], 1, 'Season One', 2022)


@pytest.fixture
def episode_id(db, show_id, season_id):
    ep = {
        'tvshow_id': show_id,
        'tvshow_tmdb_id': _SHOW['tmdb_id'],
        'season_id': season_id,
        'season_number': 1,
        'episode_number': 1,
        'title': 'Pilot',
        'year': 2022,
        'description': 'First episode.',
        'score': 80.0,
    }
    return addEpisodeToDb(db, ep)


class TestTVShows:
    def test_addTVShowToDb_returns_id(self, db):
        sid = addTVShowToDb(db, _SHOW)
        assert isinstance(sid, int)
        assert sid > 0

    def test_addTVShowToDb_oid_set(self, db):
        addTVShowToDb(db, _SHOW)
        cur = db.cursor()
        cur.execute("SELECT oid FROM tvshows WHERE tmdb_id = ?", (_SHOW['tmdb_id'],))
        row = cur.fetchone()
        assert row is not None
        assert row[0] is not None

    def test_addTVShowToDb_idempotent_by_tmdb_id(self, db):
        sid1 = addTVShowToDb(db, _SHOW)
        sid2 = addTVShowToDb(db, _SHOW)
        assert sid1 == sid2
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM tvshows WHERE tmdb_id = ?", (_SHOW['tmdb_id'],))
        assert cur.fetchone()[0] == 1

    def test_getTVShows_empty_without_files(self, db, show_id):
        # getTVShows only returns shows that have files linked via episodes
        result = getTVShows(db)
        assert result == []

    def test_getTVShows_returns_show_with_files(self, db, show_id, season_id, episode_id):
        col_id, _ = create_or_get_collection(db, 'TestCol')
        addFileToDb(db, col_id, 'show_s01e01.mkv', '.')
        cur = db.cursor()
        cur.execute("SELECT id FROM files WHERE filename = 'show_s01e01.mkv'")
        fid = cur.fetchone()['id']
        assignEpisodeToFile(db, fid, episode_id)
        result = getTVShows(db)
        assert len(result) == 1
        assert result[0]['title'] == 'Test Show'


class TestSeasons:
    def test_addSeasonToDb_returns_id(self, db, show_id):
        sid = addSeasonToDb(db, show_id, _SHOW['tmdb_id'], 1, 'Season One', 2022)
        assert isinstance(sid, int)
        assert sid > 0

    def test_addSeasonToDb_idempotent(self, db, show_id):
        sid1 = addSeasonToDb(db, show_id, _SHOW['tmdb_id'], 1, 'Season One', 2022)
        sid2 = addSeasonToDb(db, show_id, _SHOW['tmdb_id'], 1, 'Season One', 2022)
        assert sid1 == sid2

    def test_getTVSeasons_bulk(self, db, show_id, season_id):
        result = getTVSeasons_bulk(db, [show_id])
        assert show_id in result
        assert len(result[show_id]) == 1
        assert result[show_id][0]['season_number'] == 1

    def test_getTVSeasons_bulk_empty(self, db):
        result = getTVSeasons_bulk(db, [])
        assert result == {}


class TestEpisodes:
    def test_addEpisodeToDb_returns_id(self, db, show_id, season_id):
        ep = {
            'tvshow_id': show_id, 'tvshow_tmdb_id': _SHOW['tmdb_id'],
            'season_id': season_id, 'season_number': 1, 'episode_number': 1,
            'title': 'Pilot', 'year': 2022, 'description': None, 'score': 0,
        }
        eid = addEpisodeToDb(db, ep)
        assert isinstance(eid, int) and eid > 0

    def test_addEpisodeToDb_idempotent(self, db, show_id, season_id):
        ep = {
            'tvshow_id': show_id, 'tvshow_tmdb_id': _SHOW['tmdb_id'],
            'season_id': season_id, 'season_number': 1, 'episode_number': 2,
            'title': 'E2', 'year': 2022, 'description': None, 'score': 0,
        }
        e1 = addEpisodeToDb(db, ep)
        e2 = addEpisodeToDb(db, ep)
        assert e1 == e2

    def test_assignEpisodeToFile(self, db, show_id, season_id, episode_id):
        col_id, _ = create_or_get_collection(db, 'Col')
        addFileToDb(db, col_id, 'ep1.mkv', '.')
        cur = db.cursor()
        cur.execute("SELECT id FROM files WHERE filename='ep1.mkv'")
        fid = cur.fetchone()['id']
        assignEpisodeToFile(db, fid, episode_id)
        cur.execute("SELECT episode_id FROM files WHERE id=?", (fid,))
        assert cur.fetchone()['episode_id'] == episode_id

    def test_getEpisodes_bulk(self, db, show_id, episode_id):
        result = getEpisodes_bulk(db, [show_id])
        assert show_id in result
        assert result[show_id][0]['episode_number'] == 1

    def test_getEpisodeFiles_bulk_empty_without_file(self, db, show_id, episode_id):
        result = getEpisodeFiles_bulk(db, [show_id])
        assert episode_id not in result

    def test_getEpisodeFiles_bulk_with_file(self, db, show_id, season_id, episode_id):
        col_id, _ = create_or_get_collection(db, 'Col2')
        addFileToDb(db, col_id, 'ep1b.mkv', '.')
        cur = db.cursor()
        cur.execute("SELECT id FROM files WHERE filename='ep1b.mkv'")
        fid = cur.fetchone()['id']
        assignEpisodeToFile(db, fid, episode_id)
        result = getEpisodeFiles_bulk(db, [show_id])
        assert episode_id in result
        assert len(result[episode_id]) == 1


class TestTVActors:
    def test_addActorToTVShowDb(self, db, show_id):
        aid = addActorToDb(db, _ACTOR)
        addActorToTVShowDb(db, show_id, aid)
        cur = db.cursor()
        cur.execute("SELECT 1 FROM actors_tvshows WHERE a_id=? AND s_id=?", (aid, show_id))
        assert cur.fetchone() is not None

    def test_addActorToTVShowDb_idempotent(self, db, show_id):
        aid = addActorToDb(db, _ACTOR)
        addActorToTVShowDb(db, show_id, aid)
        addActorToTVShowDb(db, show_id, aid)
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM actors_tvshows WHERE a_id=? AND s_id=?", (aid, show_id))
        assert cur.fetchone()[0] == 1

    def test_getTVCast_bulk(self, db, show_id):
        aid = addActorToDb(db, _ACTOR)
        addActorToTVShowDb(db, show_id, aid)
        result = getTVCast_bulk(db, [show_id])
        assert show_id in result
        assert result[show_id][0]['name'] == 'Show Actor'

    def test_getTVShowsByActor_bulk(self, db, show_id):
        aid = addActorToDb(db, _ACTOR)
        addActorToTVShowDb(db, show_id, aid)
        result = getTVShowsByActor_bulk(db, [aid])
        assert aid in result
        titles = [r['title'] for r in result[aid]]
        assert 'Test Show' in titles

    def test_getTVCrew_bulk(self, db, show_id):
        aid = addActorToDb(db, _ACTOR)
        addCrewToTVShowDb(db, show_id, aid, 'Creator')
        result = getTVCrew_bulk(db, [show_id])
        assert show_id in result
        assert result[show_id][0]['job'] == 'Creator'


class TestTVGenres:
    def test_addGenreToTVShowDb(self, db, show_id):
        gid = addGenreToDb(db, 18, 'Drama')
        addGenreToTVShowDb(db, show_id, gid)
        cur = db.cursor()
        cur.execute("SELECT 1 FROM tvshows_genres WHERE tvshow_id=? AND genre_id=?", (show_id, gid))
        assert cur.fetchone() is not None

    def test_addGenreToTVShowDb_idempotent(self, db, show_id):
        gid = addGenreToDb(db, 18, 'Drama')
        addGenreToTVShowDb(db, show_id, gid)
        addGenreToTVShowDb(db, show_id, gid)
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM tvshows_genres WHERE tvshow_id=? AND genre_id=?", (show_id, gid))
        assert cur.fetchone()[0] == 1

    def test_getTVGenres_bulk(self, db, show_id):
        gid = addGenreToDb(db, 99, 'Sci-Fi')
        addGenreToTVShowDb(db, show_id, gid)
        result = getTVGenres_bulk(db, [show_id])
        assert show_id in result
        names = [g['name'] for g in result[show_id]]
        assert 'Sci-Fi' in names

    def test_getTVGenres_bulk_empty(self, db):
        result = getTVGenres_bulk(db, [])
        assert result == {}


class TestTVShowDeduplication:
    def test_addTVShowToDb_same_tmdb_id_different_year_no_duplicate(self, db):
        show_2015 = dict(_SHOW, year=2015)
        show_2017 = dict(_SHOW, year=2017)
        sid1 = addTVShowToDb(db, show_2015)
        sid2 = addTVShowToDb(db, show_2017)
        assert sid1 == sid2
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM tvshows WHERE tmdb_id = ?", (_SHOW['tmdb_id'],))
        assert cur.fetchone()[0] == 1

    def test_migration_v12_merges_null_tmdb_id_title_duplicates(self, tmp_path):
        import sqlite3
        # Build a pre-v12 DB manually with two stub rows for the same title
        db_path = str(tmp_path / "dup.db")
        conn = migration.initialize_db(db_path)
        # Insert two stubs with same title but different years (simulates pre-fix state)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO tvshows(tmdb_id, title, title_orig, title_normalized, year, oid) VALUES (NULL, 'Dup Show', 'Dup Show', 'dup show', 2015, 'oid-dup-2015')"
        )
        id1 = cur.lastrowid
        cur.execute(
            "INSERT INTO tvshows(tmdb_id, title, title_orig, title_normalized, year, oid) VALUES (NULL, 'Dup Show', 'Dup Show', 'dup show', 2017, 'oid-dup-2017')"
        )
        id2 = cur.lastrowid
        conn.commit()
        # Manually set dbversion back to 11 to trigger migration
        cur.execute("UPDATE settings SET value_int = 11 WHERE dbkey = 'dbversion'")
        conn.commit()
        conn.close()

        conn2 = migration.initialize_db(db_path)
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM tvshows WHERE title = 'Dup Show'")
        assert cur2.fetchone()[0] == 1
        cur2.execute("SELECT id FROM tvshows WHERE title = 'Dup Show'")
        surviving_id = cur2.fetchone()[0]
        assert surviving_id == id1  # MIN(id) wins
        conn2.close()

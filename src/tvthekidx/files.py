# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

from . import database as _database
from .database import execute_sql, addFileToDb, updateLastSeen, create_or_get_collection, get_collection, DEFAULT_MOVIE_REGEX, DEFAULT_TVSHOW_REGEX
from .tags import tag_add_by_filename
from .utility import verbose

import os
import io
import re
import glob

import ffmpeg
from moviepy import VideoFileClip
from PIL import Image


def _close_clip(clip):
    try:
        clip.reader.close()
    except Exception:
        pass
    try:
        if clip.audio:
            clip.audio.reader.close_proc()
    except Exception:
        pass


def store_screenshot(db, collection_id, m, filename, relpath):
    file_id = _database.get_file_id(db, collection_id, filename, relpath)
    if file_id is None:
        return False
    try:
        clip = VideoFileClip(m)
        length = clip.duration
        _close_clip(clip)
    except Exception as e:
        verbose(f"store_screenshot open failed for {filename}: {e}", 2)
        return False
    offsets = [max(0.5, length * 0.2), length * 0.5, length * 0.8]
    _database.delete_file_attachments(db, file_id, 'screenshot')
    captured = 0
    for t in offsets:
        try:
            data = get_screenshot(m, t)
            _database.add_file_attachment(db, file_id, 'screenshot', data)
            captured += 1
        except Exception as e:
            verbose(f"store_screenshot frame at {t:.1f}s failed for {filename}: {e}", 2)
    return captured > 0


def get_screenshot(video_path, time):
    clip = VideoFileClip(video_path)
    length = clip.duration
    if time > length:
        time = int(length / 2)
    screenshot = clip.get_frame(time)
    _close_clip(clip)

    image = Image.fromarray(screenshot)
    image.thumbnail((600, 600))

    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='JPEG', quality=25, optimize=True)
    img_byte_array = img_byte_array.getvalue()

    return img_byte_array


def scanDir(db, collection_name, rootDir, recursiveSearch=False, libType="movies"):
    " scan all files found "
    idx = 0
    verbose("Scanning for new files...", 2)

    collection_id, _ = create_or_get_collection(db, collection_name)
    collection_row = get_collection(db, collection_name)
    if libType == "tvshows":
        file_regex = (collection_row['tvshow_filename_regex'] if collection_row else None) or DEFAULT_TVSHOW_REGEX
    else:
        file_regex = (collection_row['movie_filename_regex'] if collection_row else None) or DEFAULT_MOVIE_REGEX

    scanPath = os.path.join(rootDir, '')
    if recursiveSearch:
        scanPath = scanPath + '**/'
    fn = scanPath + '*.'
    all_files = list(glob.glob(fn + 'mp4', recursive=recursiveSearch))
    for ext in ('avi', 'm4v', 'mkv', 'mov', 'mpg'):
        all_files += glob.glob(fn + ext, recursive=recursiveSearch)
    files = sorted(
        [fpath for fpath in all_files if re.search(file_regex, os.path.basename(fpath))],
        key=lambda fpath: os.path.basename(fpath).lower()
    )

    for fpath in files:
        idx = idx + 1
        f = os.path.basename(fpath)
        absPath = os.path.dirname(fpath)
        relPath = os.path.relpath(absPath, rootDir)
        size = os.path.getsize(fpath)
        ctime = os.path.getctime(fpath)
        mtime = os.path.getmtime(fpath)
        entry = addFileToDb(db, collection_id, f, relPath, libType)
        if entry is True:
            tag_add_by_filename(db, f)
            from . import tvstation as _tvstation
            station = _tvstation.detect_tvstation_from_filename(f)
            if station is not None:
                file_id = _database.get_file_id(db, collection_id, f, relPath)
                if file_id is not None:
                    db.cursor().execute("UPDATE files SET tvstation = ? WHERE id = ?", (station, file_id))
        else:
            updateLastSeen(db, collection_id, f, relPath)
        forceScreenshot = False
        if ((entry is True) or (size != entry["size"]) or (entry["duration"] is None)):
            verbose(f"Updating meta data for {f}", 2)
            try:
                probe = ffmpeg.probe(fpath)
                video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
                width = video_streams[0]['width']
                height = video_streams[0]['height']
                duration = float(video_streams[0]['duration'])
                codec = video_streams[0]['codec_name']
                result = updateFileMeta(db, f, {"collection_id": collection_id, "size": size, "ctime": ctime, "mtime": mtime, "width": width, "height": height, "duration": duration, "codec": codec, 'screenshot': None})
                forceScreenshot = True
            except:
                verbose("ffprobe failed for " + fpath, 2)
                result = updateFileMeta(db, f, {"collection_id": collection_id, "size": size, "ctime": ctime, "mtime": mtime, "width": None, "height": None, "duration": None, "codec": None, 'screenshot': None})
                forceScreenshot = True
            if result is False:
                verbose(f"Update meta data for {f} failed", 2)
        existing_screenshots = []
        if entry is not True:
            file_id = _database.get_file_id(db, collection_id, f, relPath)
            if file_id is not None:
                existing_screenshots = _database.get_file_attachments(db, file_id, 'screenshot')
        if ((entry is True) or (forceScreenshot is True) or not existing_screenshots):
            verbose(f"Grabbing screenshot for {f}", 2)
            result = store_screenshot(db, collection_id, fpath, f, relPath)
            if result is False:
                verbose(f"Grabbing screenshot for {f} failed", 2)

    verbose(f"{idx} files found")

    " check if all database files exist "
    verbose("Scanning for obsolete files...", 2)
    selectSQL = "SELECT id, filename, relpath FROM files WHERE collection_id = ? ORDER BY relpath ASC, filename ASC"
    cur = execute_sql(db, selectSQL, (collection_id,))
    for row in cur.fetchall():
        fn = rootDir + '/'
        if row['relpath']:
            fn = fn + row['relpath'] + '/'
        fn = fn + row['filename']

        if (not os.path.isfile(fn)):
            file_id = row['id']
            _database.delete_file_attachments(db, file_id)
            execute_sql(db, "DELETE FROM files_tags WHERE f_id = ?", (file_id,))
            execute_sql(db, "DELETE FROM files WHERE id = ?", (file_id,))

    " finish "
    db.commit()
    _database.cleanup_orphan_tvshows(db)
    return None


def backfill_screenshots(db, collection, rootDir, threshold=3):
    cur = db.cursor()
    sql = """
        SELECT f.id, f.collection_id, f.filename, f.relpath
        FROM files f
        LEFT JOIN (
            SELECT ref_id, COUNT(*) AS cnt
            FROM attachments
            WHERE type = 'screenshot'
            GROUP BY ref_id
        ) sc ON f.id = sc.ref_id
        WHERE COALESCE(sc.cnt, 0) < ?
    """
    params = [threshold]
    if collection:
        sql += " AND f.collection_id = (SELECT id FROM collections WHERE name = ?)"
        params.append(collection)
    cur.execute(sql, params)
    rows = cur.fetchall()
    verbose(f"Capturing screenshots for {len(rows)} files (threshold={threshold})", 2)
    for idx, row in enumerate(rows, 1):
        relpath = row["relpath"]
        if relpath and relpath != '.':
            fn = os.path.join(rootDir, relpath, row["filename"])
        else:
            fn = os.path.join(rootDir, row["filename"])
        if not os.path.isfile(fn):
            verbose(f"  [{idx}/{len(rows)}] not found, skipping: {fn}", 2)
            continue
        verbose(f"  [{idx}/{len(rows)}] {row['filename']}", 3)
        result = store_screenshot(db, row["collection_id"], fn, row["filename"], row["relpath"])
        if not result:
            verbose(f"  [{idx}/{len(rows)}] failed: {row['filename']}", 2)


def updateFileMeta(db, filename, attributes):
    selectSQL = "SELECT * FROM files WHERE collection_id=? AND filename = ?"
    cur = execute_sql(db, selectSQL, (attributes['collection_id'], filename))
    entry = cur.fetchone()
    if entry is None:
        return False
    else:
        parameters = []
        updateSQL = "UPDATE FILES SET "
        for attr in ('size', 'ctime', 'mtime', 'width', 'height', 'duration', 'codec', 'screenshot'):
            if attributes.get(attr) is not None and attributes[attr] != entry[attr]:
                if attributes[attr] is None:
                    updateSQL = updateSQL + attr + " = NULL, "
                else:
                    updateSQL = updateSQL + attr + " = ?, "
                    parameters.append(attributes[attr])
        updateSQL = updateSQL + "lastmod=(cast(strftime('%s','now') as int)) WHERE filename = ? AND collection_id = ?"
        if len(parameters) > 0:
            parameters.append(filename)
            parameters.append(attributes['collection_id'])
            result = execute_sql(db, updateSQL, parameters, True)
            return result
        else:
            return False

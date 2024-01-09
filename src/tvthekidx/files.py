# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2024 developer@mplx.eu

from . database import execute_sql, addFileToDb, store_screenshot
from . utility import verbose

import os
import io
import glob

import ffmpeg
from moviepy.editor import VideoFileClip
from PIL import Image


def get_screenshot(video_path, time):
    clip = VideoFileClip(video_path)
    screenshot = clip.get_frame(time)
    clip.reader.close()
    clip.audio.reader.close_proc()

    image = Image.fromarray(screenshot)
    image.thumbnail((600, 600))

    img_byte_array = io.BytesIO()
    image.save(img_byte_array, format='JPEG', quality=25, optimize=True)
    img_byte_array = img_byte_array.getvalue()

    return img_byte_array


def scanDir(db, collection, rootDir, recursiveSearch=False):
    " scan all files found "
    idx = 0
    verbose("Scanning for new files...", 2)

    scanPath = os.path.join(rootDir, '')
    if recursiveSearch:
        scanPath = scanPath + '**/'
    fn = scanPath + '* ([0-9][0-9][0-9][0-9])*.'
    movies = glob.glob(fn + 'mp4', recursive=recursiveSearch)
    for ext in ('avi', 'm4v', 'mkv', 'mov', 'mpg'):
        movies.extend(glob.glob(fn + ext, recursive=recursiveSearch))

    for m in movies:
        idx = idx + 1
        f = os.path.basename(m)
        absPath = os.path.dirname(m)
        relPath = os.path.relpath(absPath, rootDir)
        size = os.path.getsize(m)
        ctime = os.path.getctime(m)
        mtime = os.path.getmtime(m)
        entry = addFileToDb(db, collection, f, relPath)
        forceScreenshot = False
        if ((entry is True) or (size != entry["size"]) or (entry["duration"] is None)):
            verbose(f"Updating meta data for {f}", 2)
            try:
                probe = ffmpeg.probe(m)
                video_streams = [stream for stream in probe["streams"] if stream["codec_type"] == "video"]
                width = video_streams[0]['width']
                height = video_streams[0]['height']
                duration = float(video_streams[0]['duration'])
                codec = video_streams[0]['codec_name']
                result = updateFileMeta(db, f, {"collection": collection, "size": size, "ctime": ctime, "mtime": mtime, "width": width, "height": height, "duration": duration, "codec": codec, 'screenshot': None})
                forceScreenshot = True
            except:
                verbose("ffprobe failed for " + m, 2)
                result = updateFileMeta(db, f, {"collection": collection, "size": size, "ctime": ctime, "mtime": mtime, "width": None, "height": None, "duration": None, "codec": None, 'screenshot': None})
                forceScreenshot = True
            if result is False:
                verbose(f"Update meta data for {f} failed", 2)
        if ((entry is True) or (forceScreenshot is True) or (entry["screenshot"] is None)):
            verbose(f"Grabbing screenshot for {f}", 2)
            result = store_screenshot(db, collection, m, f, relPath)
            if result is False:
                verbose(f"Grabbing screenshot for {f} failed", 2)

    verbose(f"{idx} files found")

    " check if all database files exist "
    verbose("Scanning for obsolete files...", 2)
    selectSQL = "SELECT id, filename, relpath FROM files"
    if collection:
        selectSQL = selectSQL + f" WHERE collection='{collection}'"
    selectSQL = selectSQL + " ORDER BY relpath ASC, filename ASC"
    cur = execute_sql(db, selectSQL, ())
    for row in cur.fetchall():
        fn = rootDir + '/'
        if row['relpath']:
            fn = fn + row['relpath'] + '/'
        fn = fn + row['filename']

        if (not os.path.isfile(fn)):
            deleteSQL = f"DELETE FROM files WHERE id = {row['id']}"
            execute_sql(db, deleteSQL)

    " finish "
    db.commit()
    return None


def updateFileMeta(db, filename, attributes):
    selectSQL = "SELECT * FROM files WHERE collection=? AND filename = ?"
    cur = execute_sql(db, selectSQL, (attributes['collection'], filename))
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
        updateSQL = updateSQL + "lastmod=(cast(strftime('%s','now') as int)) WHERE filename = ? AND collection = ?"
        if len(parameters) > 0:
            parameters.append(filename)
            parameters.append(attributes['collection'])
            result = execute_sql(db, updateSQL, parameters, True)
            return result
        else:
            return False

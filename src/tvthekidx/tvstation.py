# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import io
import os

from PIL import Image

_DEFAULT_MODEL = os.path.join(os.path.dirname(__file__), "tvstation.pt")


def load_model(model_path=None):
    from ultralytics import YOLO
    path = model_path or _DEFAULT_MODEL
    if not os.path.isfile(path):
        return None
    return YOLO(path)


def detect_tvstation(model, screenshot_bytes, min_confidence=0.5):
    if not screenshot_bytes:
        return None
    img = Image.open(io.BytesIO(bytes(screenshot_bytes)))
    results = model.predict(img, verbose=False)
    if not results:
        return None
    boxes = results[0].boxes
    if boxes is None or len(boxes) == 0:
        return None
    best_idx = int(boxes.conf.argmax())
    if float(boxes.conf[best_idx]) < min_confidence:
        return None
    cls_id = int(boxes.cls[best_idx])
    return results[0].names[cls_id]


def backfill_tvstation(db, model):
    cur = db.cursor()
    cur.execute("SELECT id, screenshot FROM files WHERE screenshot IS NOT NULL AND tvstation IS NULL")
    rows = cur.fetchall()
    for row in rows:
        tvstation = detect_tvstation(model, bytes(row["screenshot"]))
        db.cursor().execute("UPDATE files SET tvstation = ? WHERE id = ?", (tvstation, row["id"]))
    db.commit()


def clear_tvstation(db):
    db.cursor().execute("UPDATE files SET tvstation = NULL")
    db.commit()

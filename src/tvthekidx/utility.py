# -*- coding: utf-8 -*-

# TVThe(k)Idx
# Copyright (c) 2021-2026 developer@mplx.eu

import uuid
import time
import base64
import hashlib
import os
import io

from PIL import Image


VERBOSITY_LEVEL: int = 1


def verbose(text: str, level: int = 1):
    if VERBOSITY_LEVEL >= level:
        print(f"[{level}] {text}")


def setVerbosity(level: int = 1):
    global VERBOSITY_LEVEL

    VERBOSITY_LEVEL = level


def getVerbosity():
    return VERBOSITY_LEVEL


def generate_oid(text: str, id: str, randomize: bool = False, suffix: str = "", namespace: uuid.UUID = uuid.NAMESPACE_OID) -> str:
    if randomize:
        timestamp = int(time.time())
        unique_key = f"{text}:{id}:{timestamp}"
    else:
        unique_key = f"{text}:{id}"

    file_uuid = uuid.uuid5(namespace, unique_key)
    return f"{file_uuid}{suffix}"


def normalize_string(text: str) -> str:
    translation_table = str.maketrans({
        # german DIN 5007-1
        "Ä": "A", "ä": "a",
        "Ö": "O", "ö": "o",
        "Ü": "U", "ü": "u",
        "ß": "ss",
        # french
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "É": "E", "È": "E", "Ê": "E", "Ë": "E",
        "à": "a", "â": "a", "À": "A", "Â": "A",
        "î": "i", "ï": "i", "Î": "I", "Ï": "I",
        "ô": "o", "Ô": "O",
        "ù": "u", "û": "u", "Ù": "U", "Û": "U",
        "ç": "c", "Ç": "C",
        # typography
        "»": "", "«": "",
        '"': "", "'": "",
        "„": "", "“": "", "”": "",
        "–": "-", "—": "-"
    })
    return text.translate(translation_table)


def include_image(img_bytes, gfxmode, outdir="img", target_w=154, target_h=231, target_format="webp", prefix="tvthek"):
    if gfxmode == "disable":
        blank = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        buf = io.BytesIO()
        blank.save(buf, format="WEBP")
        blank_bytes = buf.getvalue()
        b64 = base64.b64encode(blank_bytes).decode("ascii")
        htmlsrc = f"data:image/webp;base64,{b64}"
        return htmlsrc, target_w, target_h

    try:
        img = Image.open(io.BytesIO(img_bytes))
    except Exception:
        return None, None, None

    orig_w, orig_h = img.size

    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = round(orig_w * scale)
    new_h = round(orig_h * scale)

    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

    left = max(0, (new_w - target_w) // 2)
    top = max(0, (new_h - target_h) // 2)
    right = min(new_w, left + target_w)
    bottom = min(new_h, top + target_h)

    img = img.crop((left, top, right, bottom))

    target_format = target_format.lower()
    buf = io.BytesIO()
    img.save(buf, format=target_format.upper())
    final_bytes = buf.getvalue()

    if gfxmode == "embed":
        b64 = base64.b64encode(final_bytes).decode("ascii")
        htmlsrc = f"data:image/{target_format};base64,{b64}"
        return htmlsrc, target_w, target_h

    elif gfxmode == "reference":
        md5 = hashlib.md5(final_bytes).hexdigest()
        shard = md5[:2]
        shard_dir = os.path.join(outdir, shard)
        os.makedirs(shard_dir, exist_ok=True)

        filename = f"{prefix}_{md5}_{target_w}_{target_h}.{target_format}"
        filepath = os.path.join(shard_dir, filename)

        if not os.path.exists(filepath):
            with open(filepath, "wb") as f:
                f.write(final_bytes)

        htmlsrc = f"{os.path.basename(outdir)}/{shard}/{filename}"
        return htmlsrc, target_w, target_h

    else:
        raise ValueError(f"Unknown gfxmode: {gfxmode}")

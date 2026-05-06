import io
import os
import pytest
from PIL import Image

from tvthekidx.utility import (
    normalize_string, generate_oid,
    setVerbosity, getVerbosity, verbose,
    include_image,
)


def _make_jpeg(w=100, h=150, color=(128, 64, 32)):
    img = Image.new("RGB", (w, h), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestNormalizeString:
    def test_german_umlauts(self):
        assert normalize_string("Ä") == "A"
        assert normalize_string("ä") == "a"
        assert normalize_string("Ö") == "O"
        assert normalize_string("ö") == "o"
        assert normalize_string("Ü") == "U"
        assert normalize_string("ü") == "u"

    def test_german_eszett(self):
        assert normalize_string("ß") == "ss"
        assert normalize_string("Straße") == "Strasse"

    def test_french_accents(self):
        assert normalize_string("é") == "e"
        assert normalize_string("è") == "e"
        assert normalize_string("ê") == "e"
        assert normalize_string("ç") == "c"
        assert normalize_string("à") == "a"
        assert normalize_string("î") == "i"

    def test_typography_quotes_removed(self):
        assert normalize_string("«Test»") == "Test"
        assert normalize_string('"Test"') == "Test"
        assert normalize_string("„Test“") == "Test"

    def test_typography_dashes_to_hyphen(self):
        assert normalize_string("–") == "-"
        assert normalize_string("—") == "-"

    def test_plain_ascii_unchanged(self):
        assert normalize_string("Hello World 123") == "Hello World 123"

    def test_mixed_word(self):
        assert normalize_string("Müller") == "Muller"


class TestGenerateOid:
    def test_deterministic(self):
        assert generate_oid("movie", "12345") == generate_oid("movie", "12345")

    def test_different_id_differs(self):
        assert generate_oid("movie", "12345") != generate_oid("movie", "99999")

    def test_different_type_differs(self):
        assert generate_oid("movie", "123") != generate_oid("actor", "123")

    def test_suffix_appended(self):
        result = generate_oid("movie", "123", suffix="-x")
        assert result.endswith("-x")

    def test_returns_string(self):
        assert isinstance(generate_oid("file", "abc"), str)

    def test_randomize_returns_string(self):
        assert isinstance(generate_oid("movie", "123", randomize=True), str)


class TestVerbosity:
    def setup_method(self):
        setVerbosity(1)

    def teardown_method(self):
        setVerbosity(1)

    def test_set_and_get(self):
        setVerbosity(3)
        assert getVerbosity() == 3

    def test_verbose_prints_at_matching_level(self, capsys):
        setVerbosity(2)
        verbose("hello", level=2)
        assert "hello" in capsys.readouterr().out

    def test_verbose_suppressed_when_level_too_high(self, capsys):
        setVerbosity(1)
        verbose("hidden", level=2)
        assert "hidden" not in capsys.readouterr().out


class TestIncludeImage:
    def test_disable_returns_blank_data_url(self):
        src, w, h = include_image(None, "disable")
        assert src.startswith("data:image/webp;base64,")
        assert w == 154
        assert h == 231

    def test_embed_returns_data_url(self):
        src, w, h = include_image(_make_jpeg(), "embed")
        assert src.startswith("data:image/webp;base64,")
        assert w == 154
        assert h == 231

    def test_embed_custom_dimensions(self):
        _, w, h = include_image(_make_jpeg(), "embed", target_w=80, target_h=120)
        assert w == 80
        assert h == 120

    def test_invalid_bytes_returns_none(self):
        src, w, h = include_image(b"not an image", "embed")
        assert src is None and w is None and h is None

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError):
            include_image(_make_jpeg(), "badmode")

    def test_reference_creates_file(self, tmp_path):
        outdir = str(tmp_path / "img")
        src, w, h = include_image(_make_jpeg(), "reference", outdir=outdir)
        assert src is not None
        assert (tmp_path / src).exists()

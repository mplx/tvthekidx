from tvthekidx.export_html import shorten_middle, movieRatingColor, actorListedChoice


class TestShortenMiddle:
    def test_short_string_unchanged(self):
        assert shorten_middle("Short", 55) == "Short"

    def test_exactly_max_len_unchanged(self):
        s = "x" * 55
        assert shorten_middle(s, 55) == s

    def test_single_long_word_uses_char_split(self):
        result = shorten_middle("a" * 100, 10)
        assert "..." in result
        assert len(result) == 10

    def test_multi_word_shortened(self):
        s = "The quick brown fox jumped over the lazy dog"
        result = shorten_middle(s, 20)
        assert "..." in result
        assert len(result) < len(s)

    def test_multi_word_preserves_start_and_end(self):
        s = "Start middle middle middle End"
        result = shorten_middle(s, 15)
        assert "Start" in result
        assert "End" in result

    def test_empty_string(self):
        assert shorten_middle("", 10) == ""


class TestMovieRatingColor:
    def test_zero_is_warning(self):
        assert movieRatingColor(0) == "warning"

    def test_below_50_is_danger(self):
        assert movieRatingColor(1) == "danger"
        assert movieRatingColor(49) == "danger"

    def test_50_to_69_is_info(self):
        assert movieRatingColor(50) == "info"
        assert movieRatingColor(69) == "info"

    def test_70_and_above_is_success(self):
        assert movieRatingColor(70) == "success"
        assert movieRatingColor(100) == "success"


class TestActorListedChoice:
    def test_high_popularity_always_listed(self):
        assert actorListedChoice(mcnt=0, popularity=40) is True
        assert actorListedChoice(mcnt=0, popularity=99) is True

    def test_many_movies_always_listed(self):
        assert actorListedChoice(mcnt=4, popularity=0) is True

    def test_moderate_popularity_with_enough_movies(self):
        assert actorListedChoice(mcnt=2, popularity=10) is True
        assert actorListedChoice(mcnt=3, popularity=5) is True

    def test_below_all_thresholds_not_listed(self):
        assert actorListedChoice(mcnt=0, popularity=0) is False
        assert actorListedChoice(mcnt=1, popularity=4) is False

    def test_boundary_mcnt_3_popularity_5(self):
        assert actorListedChoice(mcnt=3, popularity=5) is True
        assert actorListedChoice(mcnt=2, popularity=5) is False

    def test_boundary_mcnt_2_popularity_10(self):
        assert actorListedChoice(mcnt=2, popularity=10) is True
        assert actorListedChoice(mcnt=1, popularity=10) is False

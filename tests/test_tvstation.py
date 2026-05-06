from tvthekidx.tvstation import display_name, detect_tvstation_from_filename, YOLO_DISPLAY_NAMES


class TestDisplayName:
    def test_known_stations(self):
        assert display_name("ard") == "ARD"
        assert display_name("zdf") == "ZDF"
        assert display_name("orf") == "ORF"
        assert display_name("netflix") == "Netflix"
        assert display_name("yt") == "YouTube"
        assert display_name("3sat") == "3sat"

    def test_unknown_returns_input_unchanged(self):
        assert display_name("unknown") == "unknown"
        assert display_name("") == ""

    def test_all_entries_in_map(self):
        for key, expected in YOLO_DISPLAY_NAMES.items():
            assert display_name(key) == expected


class TestDetectTvstationFromFilename:
    def test_known_station_tag(self):
        assert detect_tvstation_from_filename("Movie Title (2023) {ard}.mkv") == "ard"
        assert detect_tvstation_from_filename("Film (2021) {zdf}.mp4") == "zdf"
        assert detect_tvstation_from_filename("Show (2020) {orf}.mkv") == "orf"

    def test_tag_normalised_to_lowercase(self):
        assert detect_tvstation_from_filename("Movie (2023) {ARD}.mkv") == "ard"
        assert detect_tvstation_from_filename("Movie (2023) {ZDF}.mkv") == "zdf"

    def test_unknown_tag_returns_none(self):
        assert detect_tvstation_from_filename("Movie (2023) {mystation}.mkv") is None

    def test_no_curly_tag_returns_none(self):
        assert detect_tvstation_from_filename("Movie Title (2023).mkv") is None

    def test_no_year_returns_none(self):
        assert detect_tvstation_from_filename("Movie Title {ard}.mkv") is None

    def test_empty_string_returns_none(self):
        assert detect_tvstation_from_filename("") is None

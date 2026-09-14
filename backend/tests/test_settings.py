from backend.settings import Settings


def test_blank_cors_origin_regex_is_disabled() -> None:
    assert Settings(cors_origin_regex="").parsed_cors_origin_regex is None


def test_cors_origin_regex_is_trimmed() -> None:
    assert (
        Settings(cors_origin_regex=" https://preview\\.example\\.com ").parsed_cors_origin_regex
        == "https://preview\\.example\\.com"
    )

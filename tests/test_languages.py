import pytest

from lessonlingo.languages import SUPPORTED_LANGUAGES, validate_targets


def test_all_required_languages_are_supported() -> None:
    """The public language list matches the Phase 1 product scope."""

    assert SUPPORTED_LANGUAGES == {
        "hin_Deva": "Hindi",
        "kan_Knda": "Kannada",
        "tam_Taml": "Tamil",
        "tel_Telu": "Telugu",
        "mal_Mlym": "Malayalam",
        "ben_Beng": "Bengali",
        "mar_Deva": "Marathi",
        "guj_Gujr": "Gujarati",
        "pan_Guru": "Punjabi",
        "ory_Orya": "Odia",
    }


def test_validate_targets_deduplicates_without_reordering() -> None:
    """Repeated CLI targets create one output in the requested order."""

    assert validate_targets(["hin_Deva", "kan_Knda", "hin_Deva"]) == [
        "hin_Deva",
        "kan_Knda",
    ]


def test_validate_targets_rejects_empty_and_unknown_values() -> None:
    """Invalid target lists produce actionable errors."""

    with pytest.raises(ValueError, match="at least one"):
        validate_targets([])
    with pytest.raises(ValueError, match="spa_Latn"):
        validate_targets(["spa_Latn"])

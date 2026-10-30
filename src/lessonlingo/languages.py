"""Supported IndicTrans2 target languages."""

from __future__ import annotations

SUPPORTED_LANGUAGES: dict[str, str] = {
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

NATIVE_NAMES: dict[str, str] = {
    "hin_Deva": "हिन्दी",
    "kan_Knda": "ಕನ್ನಡ",
    "tam_Taml": "தமிழ்",
    "tel_Telu": "తెలుగు",
    "mal_Mlym": "മലയാളം",
    "ben_Beng": "বাংলা",
    "mar_Deva": "मराठी",
    "guj_Gujr": "ગુજરાતી",
    "pan_Guru": "ਪੰਜਾਬੀ",
    "ory_Orya": "ଓଡ଼ିଆ",
}

SOURCE_LANGUAGE = "eng_Latn"


def validate_targets(targets: list[str]) -> list[str]:
    """Return target codes after rejecting unsupported or duplicate values."""

    if not targets:
        raise ValueError("Choose at least one target language.")

    unsupported = [target for target in targets if target not in SUPPORTED_LANGUAGES]
    if unsupported:
        supported = ", ".join(SUPPORTED_LANGUAGES)
        invalid = ", ".join(unsupported)
        raise ValueError(f"Unsupported target language: {invalid}. Choose from: {supported}")

    return list(dict.fromkeys(targets))

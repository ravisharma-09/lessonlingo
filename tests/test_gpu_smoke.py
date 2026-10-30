import re

import pytest

from lessonlingo.translator import IndicTransTranslator


@pytest.mark.gpu
def test_light_model_produces_devanagari() -> None:
    """Translate one sentence with the real light model on the test laptop."""

    translator = IndicTransTranslator("light", device="cuda", batch_size=1)
    try:
        output = translator.translate(["Water is essential for life."], "hin_Deva")
    finally:
        translator.close()

    assert output and output[0].strip()
    assert re.search(r"[\u0900-\u097f]", output[0])

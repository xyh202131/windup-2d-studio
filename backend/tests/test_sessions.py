import pytest

from app.sessions import select_available_image_model


PREFERRED = ["gemini-3.1-flash-image-preview", "gemini-2.5-flash-image"]


def test_requested_model_accepts_provider_prefixed_account_id():
    selected = select_available_image_model(
        "gemini-3.1-flash-image-preview",
        ["google/gemini-3.1-flash-image-preview"],
        PREFERRED,
    )

    assert selected == "google/gemini-3.1-flash-image-preview"


def test_first_preferred_account_model_is_used_when_requested_is_missing():
    selected = select_available_image_model(
        "gemini-3.1-flash-image-preview",
        ["text-model", "gemini-2.5-flash-image"],
        PREFERRED,
    )

    assert selected == "gemini-2.5-flash-image"


def test_non_image_account_models_are_rejected():
    with pytest.raises(ValueError, match="Gemini 图像模型"):
        select_available_image_model("missing", ["text-model"], PREFERRED)

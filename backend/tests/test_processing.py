from io import BytesIO

import pytest
from PIL import Image, ImageDraw

from app.processing import ImageQualityError, normalize_hd, validate_upload


def image_bytes(size=512):
    image = Image.new("RGB", (size, size), "#ff00d4")
    ImageDraw.Draw(image).rectangle((180, 80, 330, 460), fill="#223344")
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_upload_and_native_resolution_gate(tmp_path):
    data = image_bytes(512)
    assert validate_upload(data, "reference.png")[1] == (512, 512)
    source = tmp_path / "source.png"
    source.write_bytes(data)
    result = normalize_hd(source, tmp_path / "frame.png", 512)
    assert result["canvas"] == [512, 512]
    with pytest.raises(ImageQualityError, match="拒绝向上放大"):
        normalize_hd(source, tmp_path / "master.png", 1024)

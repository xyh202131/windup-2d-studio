from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


MAGENTA = (255, 0, 212)


class ImageQualityError(RuntimeError):
    pass


def validate_upload(data: bytes, filename: str) -> tuple[str, tuple[int, int]]:
    if len(data) > 15 * 1024 * 1024:
        raise ImageQualityError("参考图不能超过 15MB")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ImageQualityError("仅支持 PNG、JPEG 或 WebP")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            size = image.size
    except Exception as error:
        raise ImageQualityError("参考图无法读取") from error
    if min(size) < 256 or max(size) > 8192:
        raise ImageQualityError("参考图边长需在 256 到 8192 像素之间")
    return suffix, size


def _matte(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            red, green, blue, alpha = pixels[x, y]
            if alpha < 255:
                continue
            distance = math.sqrt((red - MAGENTA[0]) ** 2 + (green - MAGENTA[1]) ** 2 + (blue - MAGENTA[2]) ** 2)
            new_alpha = max(0, min(255, round((distance - 20) / 105 * 255)))
            if new_alpha < 220:
                spill = max(0, red - max(green, blue))
                red = max(green, red - spill)
                blue = min(255, blue + spill // 5)
            pixels[x, y] = (red, green, blue, new_alpha)
    return rgba


def normalize_hd(source: Path, destination: Path, target: int, *, foot_ratio: float = .9) -> dict:
    with Image.open(source) as opened:
        if opened.width < target or opened.height < target:
            raise ImageQualityError(f"模型原图 {opened.width}×{opened.height} 低于 {target}px，拒绝向上放大")
        image = _matte(opened)
    alpha = image.getchannel("A")
    bounds = alpha.getbbox()
    if not bounds:
        raise ImageQualityError("生成结果没有可见主体")
    subject = image.crop(bounds)
    max_width, max_height = int(target * .82), int(target * .80)
    scale = min(max_width / subject.width, max_height / subject.height, 1.0)
    if scale < 1:
        subject = subject.resize((max(1, round(subject.width * scale)), max(1, round(subject.height * scale))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    left = (target - subject.width) // 2
    top = round(target * foot_ratio - subject.height)
    canvas.alpha_composite(subject, (left, top))
    destination.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(destination, "PNG", optimize=True)
    visible = canvas.getchannel("A").getbbox()
    assert visible
    return {
        "canvas": [target, target],
        "bounds": list(visible),
        "coverage": round(((visible[2] - visible[0]) * (visible[3] - visible[1])) / (target * target), 4),
        "footY": visible[3],
        "warnings": [] if visible[3] <= target else ["主体超出画布"],
    }


def sequence_quality(paths: list[Path], loop: bool) -> dict:
    if not paths:
        return {"warnings": ["没有动作帧"]}
    frames = [Image.open(path).convert("RGBA") for path in paths]
    bounds = [frame.getchannel("A").getbbox() for frame in frames]
    visible = [box for box in bounds if box]
    warnings: list[str] = []
    if len(visible) != len(frames):
        warnings.append("包含空帧")
    if visible:
        feet = [box[3] for box in visible]
        centers = [(box[0] + box[2]) / 2 for box in visible]
        if max(feet) - min(feet) > frames[0].height * .035:
            warnings.append("脚底线波动较大")
        if max(centers) - min(centers) > frames[0].width * .18:
            warnings.append("主体水平位置波动较大")
    duplicate_pairs = []
    for index in range(len(frames) - 1):
        diff = ImageChops.difference(frames[index], frames[index + 1]).convert("RGB")
        if sum(ImageStat.Stat(diff).mean) / 3 < 1.8:
            duplicate_pairs.append([index, index + 1])
    if duplicate_pairs:
        warnings.append("存在近似重复帧")
    if loop and len(frames) > 1:
        seam = ImageChops.difference(frames[0], frames[-1]).convert("RGB")
        if sum(ImageStat.Stat(seam).mean) / 3 > 42:
            warnings.append("循环首尾差异较大")
    for frame in frames:
        frame.close()
    return {"warnings": warnings, "duplicatePairs": duplicate_pairs}


from __future__ import annotations

import base64
import io
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


class ProviderError(RuntimeError):
    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class QnAIGCProvider:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, api_key: str, body: dict | None = None, *, timeout: int = 180, retries: int = 3) -> dict:
        if not api_key:
            raise ProviderError("请先连接 API Key")
        payload = None if body is None else json.dumps(body).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(retries):
            try:
                request = urllib.request.Request(
                    self.base_url + path,
                    data=payload,
                    method=method,
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    return json.load(response)
            except urllib.error.HTTPError as error:
                raw = error.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                    detail = parsed.get("error", parsed)
                    message = detail.get("message", str(detail)) if isinstance(detail, dict) else str(detail)
                except Exception:
                    message = f"生成服务返回 HTTP {error.code}"
                last_error = ProviderError(message, error.code)
                if 400 <= error.code < 500:
                    raise last_error
            except Exception as error:
                last_error = error
            if attempt + 1 < retries:
                time.sleep(1 + attempt * 2)
        if isinstance(last_error, ProviderError):
            raise last_error
        raise ProviderError(f"无法连接生成服务：{last_error}")

    def verify(self, api_key: str) -> bool:
        if api_key == "demo":
            return True
        try:
            self._request("POST", "/chat/completions", api_key, {"model": "__windup_2d_probe__", "messages": []}, timeout=20, retries=1)
        except ProviderError as error:
            if error.status in {400, 404, 422}:
                return True
            raise
        return True

    def models(self, api_key: str) -> list[str]:
        if api_key == "demo":
            return ["windup-demo-image"]
        response = self._request("GET", "/models", api_key, timeout=20, retries=2)
        return [str(item["id"]) for item in response.get("data", []) if item.get("id")]

    @staticmethod
    def _content(prompt: str, references: list[Path]) -> str | list[dict]:
        if not references:
            return prompt
        content: list[dict] = [{"type": "text", "text": prompt}]
        for path in references:
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
        return content

    def generate_image(self, prompt: str, references: list[Path], api_key: str, model: str, *, size: int, seed_label: str) -> bytes:
        if api_key == "demo":
            return self._demo_image(size, seed_label)
        body = {"model": model, "stream": False, "messages": [{"role": "user", "content": self._content(prompt, references)}]}
        for _ in range(3):
            response = self._request("POST", "/chat/completions", api_key, body, timeout=240, retries=4)
            message = (response.get("choices") or [{}])[0].get("message", {})
            match = re.search(r"data:image/[^;]+;base64,([A-Za-z0-9+/=]{100,})", json.dumps(message))
            if match:
                data = base64.b64decode(match.group(1))
                if len(data) > 5000:
                    return data
        raise ProviderError("模型响应中没有可用图像")

    @staticmethod
    def _demo_image(size: int, label: str) -> bytes:
        image = Image.new("RGB", (size, size), "#ff00d4")
        draw = ImageDraw.Draw(image)
        cx, floor = size // 2, int(size * .9)
        ink = "#192032"
        accent = "#e7a94b"
        draw.ellipse((cx-size*.13, size*.12, cx+size*.13, size*.38), fill="#e1b49a", outline=ink, width=max(2, size//128))
        draw.rounded_rectangle((cx-size*.2, size*.34, cx+size*.2, size*.72), radius=size*.06, fill="#25324d", outline=accent, width=max(3, size//96))
        draw.polygon([(cx-size*.18,size*.7),(cx-size*.1,floor),(cx,floor-size*.2)], fill=ink)
        draw.polygon([(cx+size*.18,size*.7),(cx+size*.1,floor),(cx,floor-size*.2)], fill=ink)
        draw.text((size*.04, size*.04), label[:28], fill="#2b1732")
        image = image.filter(ImageFilter.GaussianBlur(radius=max(.2, size/2048)))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

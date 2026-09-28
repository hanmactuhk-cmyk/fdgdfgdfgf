from __future__ import annotations
import time
from pathlib import Path
from typing import Any, Callable, Optional
import requests

class GLabsError(RuntimeError):
    pass

class GLabsClient:
    def __init__(self, base_url="http://127.0.0.1:8765", api_key="", timeout=30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout

    @property
    def headers(self):
        return {"Content-Type": "application/json", "X-API-Key": self.api_key}

    def health(self):
        r = requests.get(f"{self.base_url}/api/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def generate_video(self, payload):
        r = requests.post(
            f"{self.base_url}/api/video/generate",
            json=payload,
            headers=self.headers,
            timeout=self.timeout,
        )
        if r.status_code != 202:
            raise GLabsError(f"HTTP {r.status_code}: {r.text[:2000]}")
        data = r.json()
        if not data.get("task_id"):
            raise GLabsError(f"Không có task_id: {data}")
        return str(data["task_id"])

    def status(self, task_id):
        r = requests.get(
            f"{self.base_url}/api/status/{task_id}",
            headers={"X-API-Key": self.api_key},
            timeout=self.timeout,
        )
        if r.status_code >= 400:
            raise GLabsError(f"Status HTTP {r.status_code}: {r.text[:2000]}")
        return r.json()

    def stop(self, task_id=None):
        if task_id:
            r = requests.post(
                f"{self.base_url}/api/stop/{task_id}",
                headers={"X-API-Key": self.api_key},
                timeout=self.timeout,
            )
        else:
            r = requests.post(
                f"{self.base_url}/api/stop",
                headers=self.headers,
                timeout=self.timeout,
            )
        if r.status_code >= 400:
            raise GLabsError(f"Stop HTTP {r.status_code}: {r.text[:2000]}")
        return r.json()

    def download(self, url_or_filename, destination):
        url = str(url_or_filename)
        if url.startswith("/"):
            url = self.base_url + url
        elif not url.startswith(("http://", "https://")):
            url = f"{self.base_url}/api/files/{url}"

        destination.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(url, stream=True, timeout=self.timeout)
        if r.status_code >= 400:
            raise GLabsError(f"Download HTTP {r.status_code}: {r.text[:1000]}")
        with destination.open("wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                if chunk:
                    f.write(chunk)
        return destination

    def wait(self, task_id, poll=4, timeout=1800, callback=None, stop_check=None):
        start = time.monotonic()
        while True:
            if stop_check and stop_check():
                raise GLabsError("Đã dừng bởi người dùng.")
            if time.monotonic() - start > timeout:
                raise GLabsError(f"Task timeout sau {timeout} giây.")

            data = self.status(task_id)
            if callback:
                callback(data)

            state = str(data.get("status", "")).lower()
            if state == "completed":
                return data
            if state == "failed":
                raise GLabsError(
                    f"{data.get('error_code','ERROR')}: "
                    f"{data.get('error','Task thất bại')}"
                )
            time.sleep(poll)

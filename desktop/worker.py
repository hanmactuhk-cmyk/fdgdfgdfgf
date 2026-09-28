from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from bridge.glabs_client import GLabsClient, GLabsError

class BatchWorker(QThread):
    row = Signal(int, str)
    log = Signal(str)
    progress = Signal(int, int)
    done = Signal()
    stopped = Signal()

    def __init__(self, jobs, client, output_dir, concurrency=1, wait_seconds=10, poll_seconds=4, timeout=1800):
        super().__init__()
        self.jobs = jobs
        self.client = client
        self.output_dir = Path(output_dir)
        self.concurrency = max(1, int(concurrency))
        self.wait_seconds = max(0, int(wait_seconds))
        self.poll_seconds = max(1, int(poll_seconds))
        self.timeout = int(timeout)
        self.stop_requested = False
        self.active = set()

    def request_stop(self):
        self.stop_requested = True
        for task_id in list(self.active):
            try:
                self.client.stop(task_id)
            except Exception as e:
                self.log.emit(f"Stop warning: {e}")

    def run(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        total = len(self.jobs)
        completed = 0

        def execute(job):
            nonlocal completed
            if self.stop_requested:
                return

            job.status = "Đang chạy"
            self.row.emit(job.number, job.status)

            payload = {
                "prompt": job.prompt,
                "model": job.model,
                "mode": job.mode,
                "aspect_ratio": job.aspect_ratio,
                "resolution": job.resolution,
                "video_length": job.video_length,
            }

            refs = []
            if job.first_image:
                refs.append({"path": job.first_image, "name": "first_frame"})
            if job.last_image:
                refs.append({"path": job.last_image, "name": "last_frame"})
            if refs:
                payload["reference_images"] = refs

            task_id = self.client.generate_video(payload)
            job.task_id = task_id
            self.active.add(task_id)
            self.log.emit(f"Task {job.number}: {task_id}")

            try:
                result = self.client.wait(
                    task_id,
                    poll=self.poll_seconds,
                    timeout=self.timeout,
                    callback=lambda d: self.row.emit(job.number, str(d.get("status","Đang chạy"))),
                    stop_check=lambda: self.stop_requested,
                )

                urls = result.get("results", [])
                if not isinstance(urls, list):
                    urls = [urls]
                urls = [x for x in urls if x]

                if not urls:
                    raise GLabsError("Task completed nhưng không có results.")

                for n, url in enumerate(urls, 1):
                    stem = Path(job.name or f"video_{job.number:03d}").stem
                    suffix = "" if len(urls) == 1 else f"_{n:02d}"
                    dest = self.output_dir / f"{stem}{suffix}.mp4"
                    self.client.download(url, dest)
                    job.result.append(str(dest))

                job.status = "Hoàn thành"
                self.row.emit(job.number, job.status)
            except Exception as e:
                job.status = "Lỗi"
                job.error = str(e)
                self.row.emit(job.number, f"Lỗi: {e}")
                self.log.emit(f"Task {job.number} ERROR: {e}")
            finally:
                self.active.discard(task_id)

        # Respect the concurrency setting. New jobs are submitted only as slots open.
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            futures = {}
            for job in self.jobs:
                if self.stop_requested:
                    break
                futures[pool.submit(execute, job)] = job
                if self.wait_seconds:
                    self.msleep(self.wait_seconds * 1000)

            for future in as_completed(futures):
                if self.stop_requested:
                    break
                try:
                    future.result()
                except Exception as e:
                    self.log.emit(str(e))
                completed += 1
                self.progress.emit(completed, total)

        if self.stop_requested:
            self.stopped.emit()
        else:
            self.done.emit()

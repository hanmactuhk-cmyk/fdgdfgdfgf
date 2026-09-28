from __future__ import annotations
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QLineEdit, QTextEdit,
    QFileDialog, QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox,
    QGroupBox, QHeaderView, QAbstractItemView, QSplitter
)

from bridge.glabs_client import GLabsClient
from .settings import load, save
from .job import Job
from .importers import import_prompts
from .worker import BatchWorker


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("G-Labs Studio 2.0.5 — Flow Video")
        self.resize(1280, 820)
        self.settings = load()
        self.jobs = []
        self.worker = None
        self.build()

    def build(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QHBoxLayout(central)

        # Left navigation
        nav = QVBoxLayout()
        title = QLabel("G-Labs Studio")
        title.setStyleSheet("font-size:20px;font-weight:bold;")
        nav.addWidget(title)

        for text in ["Flow Ảnh", "Flow Video", "Nhân Vật", "GPT Image 2", "Meta Media",
                     "Grok Media", "Workflow", "Dựng Video", "Nâng Cấp Ảnh", "Webhook API",
                     "Công Cụ Khác", "Log Chi Tiết", "Cài Đặt"]:
            b = QPushButton(text)
            b.setCheckable(text == "Flow Video")
            if text == "Flow Video":
                b.setChecked(True)
            nav.addWidget(b)

        nav.addStretch()
        navbox = QWidget()
        navbox.setLayout(nav)
        navbox.setFixedWidth(165)
        outer.addWidget(navbox)

        # Main
        main = QVBoxLayout()
        outer.addLayout(main, 1)

        top = QHBoxLayout()
        self.running = QLabel("▶ 0 Đang chạy")
        self.pending = QLabel("◷ 0 Hàng đợi")
        self.completed = QLabel("✓ 0 Xong")
        self.errors = QLabel("△ 0 Lỗi")
        for w in [self.running, self.pending, self.completed, self.errors]:
            w.setStyleSheet("font-weight:bold;padding:10px;border:1px solid #555;")
            top.addWidget(w)
        main.addLayout(top)

        cfg = QGroupBox("Cấu hình cơ bản")
        g = QGridLayout(cfg)

        self.model = QComboBox()
        self.model.addItems(["Lite [5 ~ 10 credit]", "Fast", "Quality", "Lite Lower Priority [0 Credit]"])
        self.aspect = QComboBox()
        self.aspect.addItems(["9:16 Dọc", "16:9 Ngang"])
        self.concurrent = QComboBox()
        self.concurrent.addItems(["1", "2", "3", "4", "5"])
        self.wait = QComboBox()
        self.wait.addItems(["0s", "5s", "10s", "20s", "30s", "60s"])
        self.output_mode = QComboBox()
        self.output_mode.addItems(["Tạo thư mục theo Task", "Một thư mục chung"])
        self.output = QLineEdit(self.settings["output_dir"])
        outbtn = QPushButton("📁")
        outbtn.clicked.connect(self.choose_output)

        g.addWidget(QLabel("Model:"), 0, 0)
        g.addWidget(self.model, 0, 1)
        g.addWidget(QLabel("Tỷ lệ video:"), 0, 2)
        g.addWidget(self.aspect, 0, 3)
        g.addWidget(QLabel("Số hàng tạo đồng thời:"), 1, 0)
        g.addWidget(self.concurrent, 1, 1)
        g.addWidget(QLabel("Thời gian chờ giữa các hàng:"), 1, 2)
        g.addWidget(self.wait, 1, 3)
        g.addWidget(QLabel("Chế độ lưu:"), 2, 0)
        g.addWidget(self.output_mode, 2, 1, 1, 2)
        g.addWidget(self.output, 3, 0, 1, 3)
        g.addWidget(outbtn, 3, 3)
        main.addWidget(cfg)

        advanced = QGroupBox("Cấu hình nâng cao / Ảnh tham chiếu")
        ag = QGridLayout(advanced)

        self.import_btn = QPushButton("Nhập tệp (TXT, Excel)")
        self.import_btn.clicked.connect(self.import_file)
        self.count = QComboBox()
        self.count.addItems(["1 hàng / 1 prompt", "2 hàng / 1 prompt", "4 hàng / 1 prompt"])
        self.use_one = QCheckBox("Dùng một prompt cho tất cả")
        self.prompt = QTextEdit()
        self.prompt.setPlaceholderText("Nhập danh sách prompt vào đây...")
        self.first = QLineEdit()
        self.last = QLineEdit()
        b1 = QPushButton("Ảnh đầu")
        b2 = QPushButton("Ảnh cuối")
        b1.clicked.connect(lambda: self.pick_image(self.first))
        b2.clicked.connect(lambda: self.pick_image(self.last))

        ag.addWidget(self.import_btn, 0, 0)
        ag.addWidget(self.count, 0, 1)
        ag.addWidget(self.use_one, 1, 0, 1, 2)
        ag.addWidget(QLabel("Prompt:"), 2, 0)
        ag.addWidget(self.prompt, 3, 0, 2, 2)
        ag.addWidget(QLabel("Ảnh đầu:"), 5, 0)
        ag.addWidget(self.first, 5, 1)
        ag.addWidget(b1, 6, 0)
        ag.addWidget(QLabel("Ảnh cuối:"), 6, 1)
        ag.addWidget(self.last, 7, 0, 1, 2)
        ag.addWidget(b2, 8, 0)
        main.addWidget(advanced)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["", "Tác vụ", "Ảnh đầu - Ảnh cuối", "Prompt", "Kết quả", "Tiến độ", "Trạng thái"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        main.addWidget(self.table, 1)

        controls = QHBoxLayout()
        self.add = QPushButton("+ Thêm vào hàng chờ")
        self.manage = QPushButton("☷ Quản lý hàng chờ")
        self.run = QPushButton("CHẠY NGAY")
        self.pause = QPushButton("TẠM DỪNG")
        self.stop = QPushButton("DỪNG")
        self.add.clicked.connect(self.add_jobs)
        self.run.clicked.connect(self.start)
        self.pause.clicked.connect(self.pause_resume)
        self.stop.clicked.connect(self.stop)
        for b in [self.add, self.manage, self.run, self.pause, self.stop]:
            controls.addWidget(b)
        main.addLayout(controls)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        main.addWidget(self.log)

    def choose_output(self):
        p = QFileDialog.getExistingDirectory(self, "Chọn thư mục lưu", self.output.text())
        if p:
            self.output.setText(p)

    def pick_image(self, target):
        p, _ = QFileDialog.getOpenFileName(self, "Chọn ảnh", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if p:
            target.setText(p)

    def import_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "Nhập prompt", "", "TXT/CSV/Excel (*.txt *.csv *.xlsx *.xlsm)")
        if not p:
            return
        try:
            prompts = import_prompts(p)
            self.prompt.setPlainText("\n".join(prompts))
            self.write_log(f"Đã nhập {len(prompts)} prompt.")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi nhập", str(e))

    def add_jobs(self):
        raw = self.prompt.toPlainText().strip()
        if not raw:
            QMessageBox.warning(self, "Prompt", "Chưa có prompt.")
            return
        prompts = [raw] if self.use_one.isChecked() else [x.strip() for x in raw.splitlines() if x.strip()]
        ratio = "9:16" if self.aspect.currentText().startswith("9:16") else "16:9"
        model_map = {
            "Lite [5 ~ 10 credit]": "veo_31_lite",
            "Fast": "veo_31_fast",
            "Quality": "veo_31_quality",
            "Lite Lower Priority [0 Credit]": "veo_31_lite_relaxed",
        }
        model = model_map[self.model.currentText()]
        mode = "text_to_video"
        if self.first.text().strip() and self.last.text().strip():
            mode = "start_end_image"
        elif self.first.text().strip():
            mode = "start_image"

        base = len(self.jobs)
        for i, p in enumerate(prompts, 1):
            for _ in range(self._copies()):
                n = len(self.jobs) + 1
                self.jobs.append(Job(
                    number=n, prompt=p, first_image=self.first.text().strip(),
                    last_image=self.last.text().strip(), mode=mode,
                    model=model, aspect_ratio=ratio, video_length=8,
                    name=f"Task {n:03d}",
                ))
        self.refresh()
        self.write_log(f"Đã thêm {len(self.jobs)-base} hàng vào queue.")

    def _copies(self):
        return int(self.count.currentText().split()[0])

    def refresh(self):
        self.table.setRowCount(len(self.jobs))
        for r, j in enumerate(self.jobs):
            vals = [
                "☐", j.name,
                ("Có ảnh đầu" if j.first_image else "") + (" + ảnh cuối" if j.last_image else ""),
                j.prompt, "",
                j.status, j.status
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(v))

    def start(self):
        if not self.jobs:
            QMessageBox.warning(self, "Queue", "Hãy thêm prompt vào hàng chờ.")
            return
        if not self.settings.get("api_key"):
            self.settings["api_key"] = ""
        self.settings["base_url"] = self.settings.get("base_url", "http://127.0.0.1:8765")
        self.settings["output_dir"] = self.output.text().strip()
        self.settings["concurrency"] = int(self.concurrent.currentText())
        self.settings["wait_seconds"] = int(self.wait.currentText().replace("s",""))
        save(self.settings)

        client = GLabsClient(self.settings["base_url"], self.settings["api_key"])
        self.worker = BatchWorker(
            self.jobs, client, self.output.text().strip(),
            int(self.concurrent.currentText()),
            int(self.wait.currentText().replace("s","")),
            self.settings.get("poll_seconds",4),
            self.settings.get("timeout_seconds",1800),
        )
        self.worker.row.connect(self.update_row)
        self.worker.log.connect(self.write_log)
        self.worker.progress.connect(lambda a,b: self.write_log(f"Tiến độ: {a}/{b}"))
        self.worker.done.connect(lambda: self.write_log("✓ Đã hoàn thành toàn bộ hàng chờ."))
        self.worker.stopped.connect(lambda: self.write_log("■ Đã dừng."))
        self.worker.start()
        self.write_log("▶ Bắt đầu chạy Flow Video.")

    def update_row(self, n, status):
        if 0 < n <= self.table.rowCount():
            self.table.setItem(n-1, 5, QTableWidgetItem(status))
            self.table.setItem(n-1, 6, QTableWidgetItem(status))

    def pause_resume(self):
        self.write_log("Tạm dừng: bản v3 sẽ hoàn thiện pause/resume ở bản tiếp theo; DỪNG có thể huỷ task đang chạy.")

    def stop(self):
        if self.worker:
            self.worker.request_stop()
            self.write_log("■ Đã gửi yêu cầu dừng.")

    def test_api(self):
        try:
            client = GLabsClient(self.settings.get("base_url","http://127.0.0.1:8765"), self.settings.get("api_key",""))
            self.write_log(str(client.health()))
        except Exception as e:
            self.write_log(f"API ERROR: {e}")

    def write_log(self, text):
        self.log.append(str(text))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec())

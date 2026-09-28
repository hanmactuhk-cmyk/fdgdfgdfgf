import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QFileDialog,
    QTableWidget,
    QTableWidgetItem,
    QCheckBox,
    QMessageBox,
    QGroupBox,
    QHeaderView,
    QAbstractItemView,
)

from bridge.glabs_client import GLabsClient
from desktop.settings import load, save
from desktop.job import Job
from desktop.importers import import_prompts
from desktop.worker import BatchWorker


class Window(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("G-Labs Studio 2.0.5 — Flow Video")
        self.resize(1280, 820)

        self.settings = load()
        self.jobs = []
        self.worker = None

        self.build()

    # =========================================================
    # GIAO DIỆN
    # =========================================================

    def build(self):

        central = QWidget()
        self.setCentralWidget(central)

        outer = QHBoxLayout(central)

        # -----------------------------------------------------
        # MENU TRÁI
        # -----------------------------------------------------

        nav = QVBoxLayout()

        title = QLabel("G-Labs Studio")
        title.setStyleSheet(
            "font-size:20px;font-weight:bold;padding:10px;"
        )

        nav.addWidget(title)

        menu_items = [
            "Flow Ảnh",
            "Flow Video",
            "Nhân Vật",
            "GPT Image 2",
            "Meta Media",
            "Grok Media",
            "Workflow",
            "Dựng Video",
            "Nâng Cấp Ảnh",
            "Webhook API",
            "Công Cụ Khác",
            "Log Chi Tiết",
            "Cài Đặt",
        ]

        for text in menu_items:

            button = QPushButton(text)

            if text == "Flow Video":
                button.setChecked(True)

            nav.addWidget(button)

        nav.addStretch()

        navbox = QWidget()
        navbox.setLayout(nav)
        navbox.setFixedWidth(165)

        outer.addWidget(navbox)

        # -----------------------------------------------------
        # MAIN
        # -----------------------------------------------------

        main = QVBoxLayout()

        outer.addLayout(main, 1)

        # -----------------------------------------------------
        # THỐNG KÊ
        # -----------------------------------------------------

        top = QHBoxLayout()

        self.running = QLabel("▶ 0 Đang chạy")
        self.pending = QLabel("◷ 0 Hàng đợi")
        self.completed = QLabel("✓ 0 Xong")
        self.errors = QLabel("△ 0 Lỗi")

        for widget in [
            self.running,
            self.pending,
            self.completed,
            self.errors,
        ]:

            widget.setStyleSheet(
                "font-weight:bold;padding:10px;border:1px solid #555;"
            )

            top.addWidget(widget)

        main.addLayout(top)

        # -----------------------------------------------------
        # CẤU HÌNH CƠ BẢN
        # -----------------------------------------------------

        cfg = QGroupBox("Cấu hình cơ bản")

        grid = QGridLayout(cfg)

        # Model
        self.model = QComboBox()

        self.model.addItems(
            [
                "Lite [5 ~ 10 credit]",
                "Fast",
                "Quality",
                "Lite Lower Priority [0 Credit]",
            ]
        )

        # Tỷ lệ
        self.aspect = QComboBox()

        self.aspect.addItems(
            [
                "9:16 Dọc",
                "16:9 Ngang",
            ]
        )

        # Số hàng chạy đồng thời
        self.concurrent = QComboBox()

        self.concurrent.addItems(
            [
                "1",
                "2",
                "3",
                "4",
                "5",
            ]
        )

        # Thời gian chờ
        self.wait = QComboBox()

        self.wait.addItems(
            [
                "0s",
                "5s",
                "10s",
                "20s",
                "30s",
                "60s",
            ]
        )

        # Chế độ lưu
        self.output_mode = QComboBox()

        self.output_mode.addItems(
            [
                "Tạo thư mục theo Task",
                "Một thư mục chung",
            ]
        )

        # Thư mục output
        self.output = QLineEdit(
            self.settings.get(
                "output_dir",
                str(
                    Path.home()
                    / "Documents"
                    / "G-Labs Studio"
                    / "output"
                    / "flow-video"
                ),
            )
        )

        output_button = QPushButton("📁")

        output_button.clicked.connect(
            self.choose_output
        )

        grid.addWidget(
            QLabel("Model:"),
            0,
            0,
        )

        grid.addWidget(
            self.model,
            0,
            1,
        )

        grid.addWidget(
            QLabel("Tỷ lệ video:"),
            0,
            2,
        )

        grid.addWidget(
            self.aspect,
            0,
            3,
        )

        grid.addWidget(
            QLabel("Số hàng tạo đồng thời:"),
            1,
            0,
        )

        grid.addWidget(
            self.concurrent,
            1,
            1,
        )

        grid.addWidget(
            QLabel("Thời gian chờ giữa các hàng:"),
            1,
            2,
        )

        grid.addWidget(
            self.wait,
            1,
            3,
        )

        grid.addWidget(
            QLabel("Chế độ lưu:"),
            2,
            0,
        )

        grid.addWidget(
            self.output_mode,
            2,
            1,
            1,
            2,
        )

        grid.addWidget(
            self.output,
            3,
            0,
            1,
            3,
        )

        grid.addWidget(
            output_button,
            3,
            3,
        )

        main.addWidget(cfg)

        # -----------------------------------------------------
        # CẤU HÌNH NÂNG CAO
        # -----------------------------------------------------

        advanced = QGroupBox(
            "Cấu hình nâng cao / Ảnh tham chiếu"
        )

        advanced_grid = QGridLayout(advanced)

        # Import
        self.import_button = QPushButton(
            "Nhập tệp (TXT, Excel)"
        )

        self.import_button.clicked.connect(
            self.import_file
        )

        # Số bản copy
        self.count = QComboBox()

        self.count.addItems(
            [
                "1 hàng / 1 prompt",
                "2 hàng / 1 prompt",
                "4 hàng / 1 prompt",
            ]
        )

        # Một prompt
        self.use_one = QCheckBox(
            "Dùng một prompt cho tất cả"
        )

        # Prompt
        self.prompt = QTextEdit()

        self.prompt.setPlaceholderText(
            "Nhập danh sách prompt vào đây..."
        )

        # Ảnh đầu
        self.first = QLineEdit()

        # Ảnh cuối
        self.last = QLineEdit()

        first_button = QPushButton("Ảnh đầu")
        last_button = QPushButton("Ảnh cuối")

        first_button.clicked.connect(
            lambda: self.pick_image(self.first)
        )

        last_button.clicked.connect(
            lambda: self.pick_image(self.last)
        )

        advanced_grid.addWidget(
            self.import_button,
            0,
            0,
        )

        advanced_grid.addWidget(
            self.count,
            0,
            1,
        )

        advanced_grid.addWidget(
            self.use_one,
            1,
            0,
            1,
            2,
        )

        advanced_grid.addWidget(
            QLabel("Prompt:"),
            2,
            0,
        )

        advanced_grid.addWidget(
            self.prompt,
            3,
            0,
            2,
            2,
        )

        advanced_grid.addWidget(
            QLabel("Ảnh đầu:"),
            5,
            0,
        )

        advanced_grid.addWidget(
            self.first,
            5,
            1,
        )

        advanced_grid.addWidget(
            first_button,
            6,
            0,
        )

        advanced_grid.addWidget(
            QLabel("Ảnh cuối:"),
            6,
            1,
        )

        advanced_grid.addWidget(
            self.last,
            7,
            0,
            1,
            2,
        )

        advanced_grid.addWidget(
            last_button,
            8,
            0,
        )

        main.addWidget(advanced)

        # -----------------------------------------------------
        # TABLE QUEUE
        # -----------------------------------------------------

        self.table = QTableWidget(
            0,
            7,
        )

        self.table.setHorizontalHeaderLabels(
            [
                "",
                "Tác vụ",
                "Ảnh đầu - Ảnh cuối",
                "Prompt",
                "Kết quả",
                "Tiến độ",
                "Trạng thái",
            ]
        )

        self.table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.Stretch,
        )

        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )

        main.addWidget(
            self.table,
            1,
        )

        # -----------------------------------------------------
        # BUTTONS
        # -----------------------------------------------------

        controls = QHBoxLayout()

        self.add_button = QPushButton(
            "+ Thêm vào hàng chờ"
        )

        self.manage_button = QPushButton(
            "☷ Quản lý hàng chờ"
        )

        self.run_button = QPushButton(
            "CHẠY NGAY"
        )

        self.pause_button = QPushButton(
            "TẠM DỪNG"
        )

        self.stop_button = QPushButton(
            "DỪNG"
        )

        self.add_button.clicked.connect(
            self.add_jobs
        )

        self.run_button.clicked.connect(
            self.start
        )

        self.pause_button.clicked.connect(
            self.pause_resume
        )

        self.stop_button.clicked.connect(
            self.stop
        )

        for button in [
            self.add_button,
            self.manage_button,
            self.run_button,
            self.pause_button,
            self.stop_button,
        ]:

            controls.addWidget(button)

        main.addLayout(controls)

        # -----------------------------------------------------
        # LOG
        # -----------------------------------------------------

        self.log = QTextEdit()

        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)

        main.addWidget(
            self.log
        )

    # =========================================================
    # CHỌN OUTPUT
    # =========================================================

    def choose_output(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Chọn thư mục lưu",
            self.output.text(),
        )

        if folder:
            self.output.setText(folder)

    # =========================================================
    # CHỌN ẢNH
    # =========================================================

    def pick_image(self, target):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn ảnh",
            "",
            "Images (*.png *.jpg *.jpeg *.webp)",
        )

        if path:
            target.setText(path)

    # =========================================================
    # IMPORT PROMPT
    # =========================================================

    def import_file(self):

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Nhập prompt",
            "",
            "TXT/CSV/Excel (*.txt *.csv *.xlsx *.xlsm)",
        )

        if not path:
            return

        try:

            prompts = import_prompts(path)

            self.prompt.setPlainText(
                "\n".join(prompts)
            )

            self.write_log(
                f"Đã nhập {len(prompts)} prompt."
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Lỗi nhập",
                str(error),
            )

    # =========================================================
    # THÊM JOB
    # =========================================================

    def add_jobs(self):

        raw = self.prompt.toPlainText().strip()

        if not raw:

            QMessageBox.warning(
                self,
                "Prompt",
                "Chưa có prompt.",
            )

            return

        if self.use_one.isChecked():

            prompts = [raw]

        else:

            prompts = [
                line.strip()
                for line in raw.splitlines()
                if line.strip()
            ]

        ratio = (
            "9:16"
            if self.aspect.currentText().startswith("9:16")
            else "16:9"
        )

        model_map = {
            "Lite [5 ~ 10 credit]":
                "veo_31_lite",

            "Fast":
                "veo_31_fast",

            "Quality":
                "veo_31_quality",

            "Lite Lower Priority [0 Credit]":
                "veo_31_lite_relaxed",
        }

        model = model_map[
            self.model.currentText()
        ]

        if (
            self.first.text().strip()
            and self.last.text().strip()
        ):

            mode = "start_end_image"

        elif self.first.text().strip():

            mode = "start_image"

        else:

            mode = "text_to_video"

        copies = self.get_copies()

        before = len(self.jobs)

        for prompt in prompts:

            for _ in range(copies):

                number = len(self.jobs) + 1

                job = Job(
                    number=number,
                    prompt=prompt,
                    first_image=self.first.text().strip(),
                    last_image=self.last.text().strip(),
                    mode=mode,
                    model=model,
                    aspect_ratio=ratio,
                    video_length=8,
                    name=f"Task {number:03d}",
                )

                self.jobs.append(job)

        self.refresh()

        added = len(self.jobs) - before

        self.write_log(
            f"Đã thêm {added} hàng vào queue."
        )

    # =========================================================
    # SỐ BẢN COPY
    # =========================================================

    def get_copies(self):

        text = self.count.currentText()

        return int(
            text.split()[0]
        )

    # =========================================================
    # REFRESH TABLE
    # =========================================================

    def refresh(self):

        self.table.setRowCount(
            len(self.jobs)
        )

        for row, job in enumerate(self.jobs):

            image_text = ""

            if job.first_image:
                image_text += "Có ảnh đầu"

            if job.last_image:

                if image_text:
                    image_text += " + "

                image_text += "ảnh cuối"

            values = [
                "☐",
                job.name,
                image_text,
                job.prompt,
                "",
                job.status,
                job.status,
            ]

            for column, value in enumerate(values):

                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        str(value)
                    ),
                )

        self.update_counters()

    # =========================================================
    # COUNTERS
    # =========================================================

    def update_counters(self):

        running = sum(
            1
            for job in self.jobs
            if job.status == "Đang chạy"
        )

        waiting = sum(
            1
            for job in self.jobs
            if job.status == "Chờ"
        )

        completed = sum(
            1
            for job in self.jobs
            if job.status == "Hoàn thành"
        )

        errors = sum(
            1
            for job in self.jobs
            if job.status == "Lỗi"
        )

        self.running.setText(
            f"▶ {running} Đang chạy"
        )

        self.pending.setText(
            f"◷ {waiting} Hàng đợi"
        )

        self.completed.setText(
            f"✓ {completed} Xong"
        )

        self.errors.setText(
            f"△ {errors} Lỗi"
        )

    # =========================================================
    # START
    # =========================================================

    def start(self):

        if not self.jobs:

            QMessageBox.warning(
                self,
                "Queue",
                "Hãy thêm prompt vào hàng chờ.",
            )

            return

        self.settings["base_url"] = (
            self.settings.get(
                "base_url",
                "http://127.0.0.1:8765",
            )
        )

        self.settings["output_dir"] = (
            self.output.text().strip()
        )

        self.settings["concurrency"] = int(
            self.concurrent.currentText()
        )

        self.settings["wait_seconds"] = int(
            self.wait.currentText().replace(
                "s",
                "",
            )
        )

        save(
            self.settings
        )

        client = GLabsClient(
            self.settings["base_url"],
            self.settings.get(
                "api_key",
                "",
            ),
        )

        self.worker = BatchWorker(
            self.jobs,
            client,
            self.output.text().strip(),
            int(
                self.concurrent.currentText()
            ),
            int(
                self.wait.currentText().replace(
                    "s",
                    "",
                )
            ),
            self.settings.get(
                "poll_seconds",
                4,
            ),
            self.settings.get(
                "timeout_seconds",
                1800,
            ),
        )

        self.worker.row.connect(
            self.update_row
        )

        self.worker.log.connect(
            self.write_log
        )

        self.worker.progress.connect(
            self.worker_progress
        )

        self.worker.done.connect(
            self.finished
        )

        self.worker.stopped.connect(
            self.stopped
        )

        self.worker.start()

        self.write_log(
            "▶ Bắt đầu chạy Flow Video."
        )

    # =========================================================
    # UPDATE ROW
    # =========================================================

    def update_row(
        self,
        number,
        status,
    ):

        if (
            number > 0
            and number <= self.table.rowCount()
        ):

            self.table.setItem(
                number - 1,
                5,
                QTableWidgetItem(
                    status
                ),
            )

            self.table.setItem(
                number - 1,
                6,
                QTableWidgetItem(
                    status
                ),
            )

        self.update_counters()

    # =========================================================
    # PROGRESS
    # =========================================================

    def worker_progress(
        self,
        current,
        total,
    ):

        self.write_log(
            f"Tiến độ: {current}/{total}"
        )

        self.update_counters()

    # =========================================================
    # PAUSE
    # =========================================================

    def pause_resume(self):

        self.write_log(
            "Tạm dừng hiện chưa được kích hoạt. "
            "Có thể dùng DỪNG để hủy các task đang chạy."
        )

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        if self.worker:

            self.worker.request_stop()

            self.write_log(
                "■ Đã gửi yêu cầu dừng."
            )

    # =========================================================
    # FINISHED
    # =========================================================

    def finished(self):

        self.update_counters()

        self.write_log(
            "✓ Đã hoàn thành toàn bộ hàng chờ."
        )

    # =========================================================
    # STOPPED
    # =========================================================

    def stopped(self):

        self.update_counters()

        self.write_log(
            "■ Đã dừng."
        )

    # =========================================================
    # LOG
    # =========================================================

    def write_log(
        self,
        text,
    ):

        self.log.append(
            str(text)
        )


# =============================================================
# START APPLICATION
# =============================================================

if __name__ == "__main__":

    app = QApplication(
        sys.argv
    )

    window = Window()

    window.show()

    sys.exit(
        app.exec()
    )

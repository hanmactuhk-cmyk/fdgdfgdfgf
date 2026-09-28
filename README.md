# G-Labs Flow Video — v3

Bản giao diện được thiết kế theo màn hình Flow Video mà người dùng cung cấp:

- Model
- Tỷ lệ video
- Số hàng tạo đồng thời
- Thời gian chờ giữa các hàng
- Chế độ lưu
- Thư mục lưu
- Nhập TXT/CSV/Excel
- Một prompt hoặc nhiều prompt
- Ảnh đầu / ảnh cuối
- Hàng chờ
- Chạy / Dừng
- Polling task và tải MP4

## API

Dùng Webhook G-Labs:

`http://127.0.0.1:8765/api/video/generate`

`GET /api/status/{task_id}`

`GET /api/files/{filename}`

`POST /api/stop/{task_id}`

API key được lưu trong AppData, không ghi vào GitHub.

## Cài trên Windows

```bat
pip install -r requirements.txt
python -m desktop.main
```

Hoặc chạy `build.bat` để tạo EXE.

## Lưu ý

Native Flow export của G-Labs chưa được cung cấp, vì vậy v3 tái tạo chức năng Flow Video thông qua Webhook API thay vì đọc dữ liệu nội bộ của giao diện G-Labs.

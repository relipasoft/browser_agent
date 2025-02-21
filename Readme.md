# Hướng Dẫn Chạy Dự Án

Dự án này bao gồm 2 file script để chạy ứng dụng FastAPI với **uvicorn** và tự động mở Chrome ở chế độ debugging (cổng 9222) nếu chưa có Chrome nào mở ở chế độ đó:

- **run.bat**: Dành cho Windows
- **run.command** : Dành cho macOS

Ngoài ra, dự án có một Chrome Extension nằm trong folder **chrome_extension**. Phần dưới đây hướng dẫn cách chạy các file script cũng như cài đặt extension.

---

## 1. Cài Đặt Các Package Cần Thiết
python version 3.11

Trước khi chạy bất kỳ file script nào, bạn cần cài đặt các package cần thiết từ file `requirements.txt`.

Mở Terminal (macOS) hoặc Command Prompt (Windows) và chạy lệnh:

```bash
pip install -r requirements.txt

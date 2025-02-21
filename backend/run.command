#!/bin/bash
# Cài đặt các package từ requirements.txt
pip install -r requirements.txt

# Chạy uvicorn ở chế độ background
uvicorn app:app --host localhost --port 8888 &
UVICORN_PID=$!

# Đợi vài giây để server khởi động (có thể điều chỉnh nếu cần)
sleep 3

# URL của ứng dụng
URL="http://localhost:8888"

# Kiểm tra nếu cổng 9222 đã có tiến trình sử dụng (Chrome ở chế độ debug)
if lsof -i :9222 >/dev/null 2>&1; then
    echo "Chrome debug mode đã được kích hoạt. Không mở thêm cửa sổ mới."
else
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 "$URL"
fi

# Đợi cho đến khi tiến trình uvicorn kết thúc (nếu cần)
wait $UVICORN_PID

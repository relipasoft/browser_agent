@echo off
REM Cài đặt các package từ requirements.txt
pip install -r requirements.txt

REM Chạy uvicorn trong một cửa sổ mới với title "Uvicorn Server"
start "Uvicorn Server" cmd /k "uvicorn app:app --host localhost --port 8888"

REM Đợi 3 giây để server khởi động
timeout /t 3 >nul

REM Kiểm tra nếu có tiến trình nào đang sử dụng cổng 9222 (Chrome debug mode)
netstat -aon | findstr ":9222" >nul
if %ERRORLEVEL%==0 (
    echo Chrome debug mode đã được kích hoạt. Không mở thêm cửa sổ mới.
) else (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 
)

# Sử dụng image Python 3.10 (phiên bản slim cho kích thước nhỏ)
FROM python:latest

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy file requirements.txt vào container và cài đặt các dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# Tạo các thư mục cần thiết để mount Chrome từ host vào container
RUN mkdir -p /host-chrome/windows /host-chrome/macos /host-chrome/linux

# Copy toàn bộ mã nguồn của dự án vào container
COPY . .

# Expose cổng 8888 để container có thể giao tiếp
EXPOSE 8888

# Lệnh chạy ứng dụng FastAPI sử dụng Uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8888"]

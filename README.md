<div align="center">

# 🚀 AI Screenshot Answer Tool & Gemini API Server

[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini AI](https://img.shields.io/badge/AI-Google_Gemini-orange.svg?logo=google&logoColor=white)](https://gemini.google.com/)
[![Perplexity AI](https://img.shields.io/badge/AI-Perplexity-black.svg?logo=ai&logoColor=white)](https://perplexity.ai/)

*Một hệ thống toàn diện kết hợp Desktop Client chụp ảnh màn hình giải trắc nghiệm tự động và Server REST API mạnh mẽ kết nối với Google Gemini.*

[Tính năng](#-tính-năng-nổi-bật) • [Cài đặt](#-cài-đặt) • [Sử dụng](#-hướng-dẫn-sử-dụng) • [Cấu trúc](#-cấu-trúc-dự-án)
</div>

---

## 🎨 Giới thiệu (Overview)

Ứng dụng bao gồm 2 thành phần hoạt động độc lập nhưng liên kết chặt chẽ với nhau:
1. **Desktop Client (Screenshot AI Answer)**: Công cụ chạy nền tích hợp hotkey, cho phép cắt ảnh màn hình phần thi trắc nghiệm, ngay lập tức phân tích hình ảnh (sử dụng Gemini hoặc Perplexity) và hiển thị kết quả đáp án trực tiếp trên màn hình dạng Overlay đẹp mắt.
2. **API Server (Gemini Multi-Service API)**: Hệ thống backend xây dựng trên FastAPI, cung cấp nhiều endpoint chuyên sâu tương tác với API của Google Gemini thông qua cookie, hỗ trợ nhận diện ảnh (Vision), tệp tin (File), và xử lý đa tác vụ chuyên sâu.

## ✨ Tính năng nổi bật

### 🖥️ Desktop Client
- 📸 **Chụp màn hình thông minh**: Nhấn phím tắt để kéo chọn vùng màn hình nhanh chóng.
- 🎯 **Trích xuất & Trả lời tự động**: Gửi hình ảnh lên AI để đọc OCR & giải câu hỏi trắc nghiệm.
- ⚡ **Overlay siêu tốc**: Hiển thị riêng đáp án (A/B/C/D) lơ lửng trên màn hình một cách gọn gàng mà không cắt ngang luồng thao tác.
- ⚙️ **Chế độ ẩn (Stealth)**: Hỗ trợ chạy không Console (`main.pyw`).

### 🌐 Backend Server
- 💬 **Lõi Text & Chat**: Xử lý logic, trò chuyện đa lượt, giữ vững context.
- 👁️ **Mô-đun Vision**: Phân tích hình ảnh, đọc ảnh chụp màn hình chuẩn xác.
- 📂 **Mô-đun File & Structured**: Hỗ trợ bóc tách thông tin, trả về cấu trúc JSON tĩnh.
- 🛡️ **Quản lý Session**: Database SQLite đi kèm, phân quyền & lưu log kết nối thông minh.

## 🛠 Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10/11
- **Môi trường**: Python 3.10 trở lên
- API Key (Perplexity) **hoặc** Tài khoản Google có cấp quyền/Cookie để sử dụng API (Gemini base).

---

## 🚀 Cài đặt (Installation)

### 1. Tải dự án và Cài đặt Dependencies
```bash
# Clone source code
git clone <đường-dẫn-repo-của-bạn>
cd AI-Screenshot-Tool

# Cài đặt thư viện bắt buộc
pip install -r requirements.txt
```

### 2. Thiết lập biến môi trường (Configuration)

**Cách 1: Client sử dụng dịch vụ nội bộ (Gemini Server)**
- Đi chuyển vào thư mục `server/` và thiết lập biến môi trường (Tham khảo `server/LAY_COOKIES_MOI.md` để lấy cookie).
- Theo mặc định, cấu hình .env trong folder server:
```ini
GEMINI_COOKIES=your_gemini_cookie_here
ADMIN_KEY=your_secret_admin_key
```

**Cách 2: Client gọi Perplexity trực tiếp**
Tạo file `.env` ở **thư mục gốc** dự án (hoặc cấp quyền Command Prompt):
```ini
# File .env ở thư mục root
PERPLEXITY_API_KEY=your_actual_api_key_here
```

---

## 🎯 Hướng dẫn sử dụng

### 1. Khởi động Server API (Tùy chọn nếu dùng Gemini) 🟢
Di chuyển vào thư mục server và chạy FastAPI qua Uvicorn:
```bash
cd server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
> **Note:** API Docs tự động sinh tại: `http://localhost:8000/docs`

### 2. Khởi động Desktop Client 💻
Bạn có thể khởi chạy Desktop Tool từ thư mục gốc thông qua nhiều hình thức:

*Chế độ hiển thị Terminal (Để theo dõi log lỗi):*
```bash
python main.py
```
*Chế độ chạy ngầm (Không hiện cửa sổ đen Console):*
```bash
python main.pyw
```

### ⌨️ Thiết lập phím tắt
- Vui lòng xem logs trên console hoặc tuỳ chỉnh phím tắt mặc định trong code (thông thường ấn Hotkey để khoanh chọn màn hình).
- **`Esc`**: Tắt giao diện kết quả overlay trên màn hình.

---

## 📁 Cấu trúc thư mục (Folder Structure)

```text
📦 AI Screenshot Tool
 ┣ 📂 server/                   # Thư mục chứa API Backend (FastAPI x Gemini)
 ┃ ┣ 📂 api/                    # Core các Route API (admin, files, vision, text...)
 ┃ ┣ 📂 database/               # Database SQLite và Models
 ┃ ┣ 📂 services/               # Logic xử lý giao tiếp tích hợp AI
 ┃ ┣ 📜 README.md               # Tài liệu server chi tiết
 ┃ ┗ 📜 main.py                 # System Backend Entrypoint
 ┣ 📜 ai_client.py              # Class đảm nhiệm gọi API trên Client Desktop
 ┣ 📜 bot.py                    # Khởi tạo và định nghĩa logic cho Tool
 ┣ 📜 main.py / main.pyw        # Tool Client Entrypoint
 ┣ 📜 overlay.py                # Xử lý UX/UI (giao diện lơ lửng đáp án A, B, C, D)
 ┣ 📜 screenshot.py             # Cắt tọa độ ảnh qua Pillow & mss
 ┗ 📜 requirements.txt          # Các cài đặt thư viện hệ thống
```

---

## 🤝 Đóng góp & Bản quyền (Contributing & License)
- **License**: Vui lòng xem ở file phân phối. Có thể tuỳ sử dụng ở mục đích cá nhân.
- Mọi đóng góp Pull Request giúp Code/UI overlay xinh đẹp hơn hoặc tối ưu Backend đều được hoan nghênh.

---
💖 *Nếu dự án mang lại giá trị lớn cho bạn, một nhấp Star ⭐ sẽ là động lực rất lớn tiếp thêm sức mạnh cho team phát triển!*

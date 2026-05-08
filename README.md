<div align="center">

# 🚀 AI Screenshot Answer Tool
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Gemini CLI](https://img.shields.io/badge/AI-Google_Gemini_CLI-orange.svg?logo=google&logoColor=white)](https://gemini.google.com/)

*Công cụ chụp ảnh màn hình giải trắc nghiệm tự động, phân tích hình ảnh và trả về kết quả đáp án trực tiếp trên màn hình nền dưới dạng Overlay cực đẹp mắt.*

[Tính năng](#-tính-năng-nổi-bật) • [Cài đặt](#-cài-đặt) • [Sử dụng](#-hướng-dẫn-sử-dụng) • [Cấu trúc](#-cấu-trúc-dự-án)
</div>

---

## 🎨 Giới thiệu (Overview)

**Desktop Client (Screenshot AI Answer)** chạy nền tích hợp hotkey. Khi thi trắc nghiệm, bạn chỉ cần nhấn phím tắt, kéo chọn vùng câu hỏi, hệ thống sẽ sử dụng công cụ dòng lệnh **Gemini CLI** (và **Tesseract OCR**) để phân tích, sau đó kết xuất riêng đáp án (A/B/C/D) lơ lửng trên góc màn hình một cách vô cùng tiện lợi và tinh tế mà không bị lộ các cửa sổ UI chat khác.

## ✨ Tính năng nổi bật

### 🖥️ Desktop Screenshot Tool
- 📸 **Chụp màn hình thông minh**: Nhấn phím tắt để kéo dãn chọn vùng màn hình nhanh chóng.
- 🎯 **Trích xuất chữ (OCR) & Trợ lý thông minh**: Hoạt động kết hợp với Tesseract OCR để nhận diện chữ trong ảnh, và đẩy lên mô hình phân tích qua CLI.
- ⚡ **Overlay siêu tốc**: Hiển thị riêng chữ cái đáp án (A, B, C, D) lơ lửng trên màn hình (Overlay), không chặn click chuột, không cản trở thao tác thi.
- ⚙️ **Chế độ chạy ẩn (Stealth process)**: Hỗ trợ chạy background không có khung đen Terminal thông qua `main.pyw`.

## 🛠 Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10/11
- **Môi trường**: Python 3.10 trở lên
- **Phụ thuộc cốt lõi**: Công cụ `gemini cli` có khả dụng trong PATH.
- **Tesseract OCR**: Cần được cài đặt sẵn trên hệ thống Windows để trích xuất text chữ.

---

## 🚀 Cài đặt (Installation)

### 1. Tải dự án và Cài đặt phần mềm bắt buộc (Python Packages)
```bash
# Clone mã nguồn
git clone https://github.com/hungvu25/Cheat-Exam.git
cd Cheat-Exam

# Cài đặt thư viện Python (bao gồm chuột/phím, hình ảnh)
pip install -r requirements.txt
```

### 2. Cài đặt công cụ nền tảng (Gemini CLI và Tesseract OCR)

Vì Tool hoạt động ngầm thông qua CLI và trích chữ trực tiếp từ màn hình nên cần 2 ứng dụng sau hoạt động trên Máy Windows:

**Cài đặt Gemini CLI:**
- Yêu cầu máy tính của bạn đã cài đặt sẵn [Node.js](https://nodejs.org/).
- Mở Terminal (Command Prompt hoặc PowerShell) và chạy lệnh sau để tải trình CLI về máy một cách toàn cục:
  ```bash
  npm install -g gemini-chat-cli
  ```
  *(Hoặc cài đặt một package Gemini CLI tương đương tùy theo project bạn đang sử dụng, miễn sao gõ lệnh `gemini` trên Terminal chạy thành công)*.

**Cài đặt Tesseract OCR:**
- Tải bộ cài Tesseract OCR dành cho Windows tại: [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/releases/tag/v5.4.0.20240606) (Khuyên dùng bản 64-bit mới nhất).
- Chạy trình cài đặt và làm theo hướng dẫn (bên trong mục lựa chọn Additional language data, có thể tick chọn `Vietnamese` nếu nhận diện tiếng Việt).
- **Quan trọng:** Thêm đường dẫn `C:\Program Files\Tesseract-OCR` vào biến môi trường **PATH** của Windows.

### 3. Cấu hình biến & Phím tắt (`config.py`)
Mở file mã nguồn `config.py` ra và chỉnh sửa thông số cho hợp ý của bạn:
```python
# Để trống ("") để cho phép Gemini CLI tự động phân tích và chọn Model tốt nhất (Auto Mode).
# Hoặc điền tên model cụ thể (VD: "gemini-2.5-flash-lite") nếu bạn ưu tiên tốc độ hiển thị.
GEMINI_CLI_MODEL = ""

# Phím tắt của tool để chạy chọn vùng
DEFAULT_HOTKEY = "z"
```
Không cần phải lấy Cookie từ trình duyệt hay tạo file `.env` rườm rà. Hệ thống sẽ kết xuất thẳng lên tool!

---

## 🎯 Hướng dẫn sử dụng

### Khởi động Tool thi 💻
Bạn có thể khởi chạy Desktop Tool từ thư mục dự án qua 2 cách tùy kịch bản:

*Chế độ hiển thị Terminal (Để theo dõi tiến độ log xử lý hoặc xem lỗi nếu có):*
```bash
python main.py
```
*Chế độ chạy ngầm (Không hiện bất kì cửa sổ đen Console nào - Lựa chọn số 1 khi làm bài):*
```bash
python main.pyw
```

### ⌨️ Phím tắt hoạt động
- Nhấn phím **`Z`** (hoặc tổ hợp phím bạn đã config) và dùng chuột khoanh vùng câu hỏi trắc nghiệm (bao gồm cả các đáp án để AI đọc).
- Tool sẽ tốn 2-4s xử lý và bung ảnh chữ nổi A, B, C, D ra mép màn hình.
- Phím **`Esc`**: Hủy lập tức đáp án nổi trên màn hình.

---

## 📁 Cấu trúc thư mục (Folder Structure)

```text
📦 Cheat-Exam
 ┣ 📜 config.py                 # File cấu hình trung tâm (Hotkey, kích thước...)
 ┣ 📜 ai_client.py              # Xử lý Logic ảnh & giao tiếp lệnh đến AI
 ┣ 📜 main.py / main.pyw        # Trình khởi chạy Tool có / không có Console
 ┣ 📜 overlay.py                # Xử lý Giao diện đáp án lơ lửng màn hình
 ┣ 📜 screenshot.py             # Script trích hình tọa độ con trỏ (mss & Pillow)
 ┗ 📜 requirements.txt          # Chứa các gói python phụ trợ Overlay / OCR
```

---

## 🤝 Đóng góp & Bản quyền (Contributing & License)
- **License**: Vui lòng tham khảo License gốc để biết thêm cấu trúc phân phối.
- Mọi đóng góp Pull Request giúp tính năng bắt điểm OCR nét hơn hoặc tăng tốc CLI đều vô cùng mong chờ.

---
💖 *Nếu dự án mang lại trải nghiệm thi cử siêu mượt và an toàn, hãy tặng kho lưu trữ một nhấp Star ⭐ khích lệ nhé!*

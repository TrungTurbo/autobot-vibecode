# 🤖 HYCSC Autobot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-v2.4%2B-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![yt-dlp](https://img.shields.io/badge/yt--dlp-Audio_Stream-red?style=for-the-badge&logo=youtube&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Bot Discord tùy chỉnh thế hệ mới dành riêng cho Câu lạc bộ HYCSC.**  
*Tích hợp thông báo thành viên thông minh & hệ thống phát nhạc đa nền tảng chất lượng cao.*

</div>

---

## 🌟 Tính Năng Nổi Bật

### 1. 📢 Quản Lý Thành Viên (Welcome & Goodbye)
* **Thông báo vào server:** Tự động gửi Discord Embed chào mừng khi có thành viên mới, kèm avatar đại diện, ngày khởi tạo tài khoản và số thứ tự thành viên trong CLB.
* **Thông báo rời server:** Gửi thông điệp tạm biệt văn minh kèm số lượng thành viên còn lại.
* **Cấu hình động:** Quản trị viên có thể chỉ định kênh chào mừng/tạm biệt bằng lệnh trực tiếp trong Discord (`/setwelcome`, `/setleave`) mà không cần sửa file code.
* **Bản xem trước:** Lệnh `/testwelcome` và `/testleave` hỗ trợ kiểm tra giao diện thông báo trước khi áp dụng thực tế.

### 2. 🎵 Hệ Thống Âm Nhạc Đa Nền Tảng (Music Streaming)
* **Hỗ trợ đa nguồn:** Stream mượt mà từ **YouTube** (tìm kiếm theo từ khóa hoặc link) và **Spotify** (nhận diện bài hát qua Spotify link và đồng bộ phát trực tiếp).
* **Hàng đợi thông minh (Queue System):** Quản lý danh sách phát linh hoạt cho từng server riêng biệt.
* **Đầy đủ tính năng player:** Bỏ qua (`skip`), tạm dừng (`pause`), tiếp tục (`resume`), lặp lại bài hát (`loop`), điều chỉnh âm lượng (`volume`), xem bài đang phát (`nowplaying`).
* **Tiết kiệm tài nguyên:** Tự động ngắt kết nối sau 3 phút nếu hàng đợi trống hoặc không còn ai trong phòng voice.

### 3. ⚡ Trải Nghiệm Tương Tác Kép
* Hỗ trợ song song **Slash Commands** (`/`) chuẩn Discord hiện đại và **Prefix Commands** (`!`) truyền thống.
* Kiến trúc **Cogs Module** hỗ trợ tự động nhận diện module mới và nạp lại code nóng (**Hot-Reload**) ngay khi đang chạy bằng `!reload`.

---

## 📂 Cấu Trúc Thư Mục

```plaintext
hycsc-autobot/
├── cogs/
│   ├── __init__.py
│   ├── welcome.py          # Quản lý sự kiện và thông báo thành viên
│   └── music.py            # Quản lý audio streaming, voice client và hàng đợi
├── .env.example            # Mẫu biến môi trường
├── .gitignore              # Bỏ qua file nhạy cảm và môi trường ảo
├── config.py               # Quản lý cấu hình & lưu trữ cài đặt server
├── guild_settings.json     # Tự động tạo: Lưu ID kênh của từng server
├── main.py                 # Điểm khởi chạy chính & đăng ký lệnh
├── requirements.txt        # Danh sách thư viện phụ thuộc
└── README.md               # Tài liệu hướng dẫn
```

---

## 🚀 Hướng Dẫn Cài Đặt & Triển Khai

### 1. Chuẩn Bị Bot Trên Discord Developer Portal
1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications) và tạo một **New Application** với tên `hycsc autobot`.
2. Vào mục **Bot**:
   * Bấm **Reset Token** để lấy chuỗi mã bí mật (`DISCORD_TOKEN`).
   * Kéo xuống phần **Privileged Gateway Intents** và **BẬT cả 2 mục sau**:
     * ✅ **SERVER MEMBERS INTENT** *(Bắt buộc để nhận diện người vào/ra)*
     * ✅ **MESSAGE CONTENT INTENT** *(Bắt buộc để nhận diện lệnh prefix)*
3. Mời Bot vào Server:
   * Vào **OAuth2** > **URL Generator**.
   * Chọn Scopes: `bot`, `applications.commands`.
   * Chọn Permissions: `Administrator` (hoặc tối thiểu quyền Quản lý kênh, Gửi tin nhắn, Kết nối và Phát âm thanh trong Voice).
   * Mở link vừa tạo để thêm bot vào server của bạn.

---

### 2. Cài Đặt Môi Trường (Linux / Ubuntu)

Cài đặt các gói công cụ hệ thống cần thiết (bao gồm `ffmpeg` phục vụ việc giải mã âm thanh):

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip ffmpeg
```

---

### 3. Cài Đặt Thư Viện

Clone mã nguồn về máy hoặc mở thư mục dự án:

```bash
# 1. Tạo môi trường ảo
python3 -m venv venv

# 2. Kích hoạt môi trường ảo
source venv/bin/activate

# 3. Cài đặt các dependencies
pip install -r requirements.txt
```

---

### 4. Thiết Lập Biến Môi Trường (`.env`)

Sao chép file mẫu và cấu hình:

```bash
cp .env.example .env
nano .env
```

Nội dung file `.env`:
```env
DISCORD_TOKEN=dán_token_bot_vào_đây
COMMAND_PREFIX=!
```

---

### 5. Khởi Chạy Bot

```bash
python3 main.py
```

Khi bot online, console sẽ hiển thị thông báo đã đồng bộ Slash Commands thành công!

---

## 📖 Bảng Lệnh Chi Tiết

### 🎵 Lệnh Âm Nhạc
| Slash Command | Prefix Command | Mô Tả |
| :--- | :--- | :--- |
| `/play <query>` | `!play <query>` hoặc `!p` | Phát nhạc từ từ khóa tìm kiếm, link YouTube hoặc Spotify |
| `/skip` | `!skip` hoặc `!s` | Bỏ qua bài hát hiện tại |
| `/pause` | `!pause` | Tạm dừng phát nhạc |
| `/resume` | `!resume` | Tiếp tục phát nhạc |
| `/stop` | `!stop` hoặc `!dc` | Dừng phát, xóa hàng đợi và rời khỏi voice channel |
| `/queue` | `!queue` hoặc `!q` | Xem danh sách bài hát đang chờ |
| `/nowplaying` | `!np` | Xem thông tin chi tiết bài hát đang phát |
| `/loop` | `!loop` | Bật hoặc tắt chế độ lặp lại bài hát hiện tại |
| `/volume <1-100>` | `!vol <1-100>` | Điều chỉnh âm lượng phát |

### 📢 Lệnh Quản Lý (Admin / Manage Server)
| Slash Command | Prefix Command | Mô Tả |
| :--- | :--- | :--- |
| `/setwelcome #kênh` | `!setwelcome #kênh` | Thiết lập kênh nhận thông báo chào mừng |
| `/setleave #kênh` | `!setleave #kênh` | Thiết lập kênh nhận thông báo tạm biệt |
| `/testwelcome` | `!testwelcome` | Gửi thử thông báo chào mừng |
| `/testleave` | `!testleave` | Gửi thử thông báo tạm biệt |

### 🛠️ Lệnh Dành Cho Developer / Bot Owner
* `!reload <tên_cog>`: Nạp lại một module ngay lập tức mà không cần tắt bot (Ví dụ: `!reload music`).
* `!sync`: Ép đồng bộ lại toàn bộ Slash Commands lên Discord.

---

## 🔧 Bảo Trì & Xử Lý Sự Cố

* **YouTube đổi thuật toán chặn stream:**  
  YouTube thường xuyên cập nhật làm các bot nhạc cũ bị lỗi. Với `hycsc autobot`, bạn chỉ cần nâng cấp `yt-dlp`:
  ```bash
  source venv/bin/activate
  pip install --upgrade yt-dlp
  ```
* **Chạy 24/7:**  
  Khuyến nghị sử dụng **PM2** hoặc cấu hình **Systemd Service** trên VPS/Linux server để bot tự động chạy ngầm và tự bật lại khi khởi động máy.

---

## 👥 Tác Giả & Đóng Góp

Dự án được xây dựng và hoàn thiện bởi:
* **`trungis_maris`**
* **`antigravity 3.8 flash high`**

> *🍁 Vibe ngày 13/10 — một buổi tối lập trình chill cùng những giai điệu âm nhạc.*
# autobot-vibecode

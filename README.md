# Telegram Bot with Aiogram and SQLite

> 📜 **License:** Apache 2.0  
> 🐍 **Python Version:** 3.7+  
> 🤖 **Aiogram Version:** 2.x  
> 🗄️ **Database:** SQLite

This project is a **fast, menu-driven Telegram bot** built with **Aiogram** and **SQLite**. It supports nested sections, rich content, and an admin control panel for easy management — all directly from Telegram.

## ✨ Features

- 📂 **Nested Menu Structure** — Organize content into categories and subcategories.
- 🔙 **Back & Home Buttons** — Smooth, intuitive navigation.
- 🎨 **Rich Content Support** — Text, photos, documents, videos, audio, and animations.
- 🛠️ **Admin Panel** — Add, rename, delete sections and items from Telegram.
- 💾 **Persistent Data** — SQLite storage ensures data stays after restarts.
- 🌐 **Arabic Interface** — Fully localized in Arabic.

## 📦 Requirements

- Python 3.7+
- Aiogram 2.x
- SQLite

## 🚀 Installation

```bash
git clone <repository_url>
cd <repository_directory>
pip install aiogram==2.*
```

## ⚙️ Configuration

Set environment variables:

```bash
export BOT_TOKEN="YOUR_BOT_TOKEN"
export ADMIN_ID="YOUR_ADMIN_ID"
export DB_PATH="bot.db"
```

Or edit directly in `bot.py`.

## ▶️ Usage

```bash
python bot.py
```

Commands:
- `/start` — Start the bot
- `/menu` — Go to main menu
- `/admin` — Open admin panel (admin only)

## 🗄️ Database Structure

**sections**
- `id` — Primary key
- `name` — Section name
- `parent_id` — Parent section ID (nullable)
- `position` — Order index

**items**
- `id` — Primary key
- `section_id` — Linked section
- `type` — text/photo/document/video/audio/animation
- `text`, `file_id`, `caption` — Content fields
- `position` — Order index

## 🛡 License

Licensed under the **Apache 2.0 License** — see the LICENSE file for details.
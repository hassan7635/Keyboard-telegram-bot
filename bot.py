# bot.py
# -*- coding: utf-8 -*-
"""
Telegram bot using aiogram (v2.x) + SQLite
Features:
- Main menu with sections (supports nested sub-sections)
- Back ⬅️ and Home 🏠 buttons everywhere
- Each section can hold multiple items of different types: text, photo, document, video, audio, animation
- Admin-only inline control panel to add/rename/delete sections and add content from inside Telegram
- Stored in SQLite so data persists across restarts

Run:
1) pip install aiogram==2.*
2) Set TOKEN and ADMIN_ID below (or via env vars)
3) python bot.py
"""

import os
import sqlite3
from contextlib import closing
from typing import Optional, List, Tuple

from aiogram import Bot, Dispatcher, types
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.filters import Text

# ---------------------- CONFIG ----------------------
TOKEN = os.getenv("BOT_TOKEN", "PUT_YOUR_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "PUT_YOUR_OWNER_ID)  # replace with your Telegram user ID
DB_PATH = os.getenv("DB_PATH", "bot.db")

# ---------------------- DB LAYER ----------------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with closing(get_db()) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER NULL REFERENCES sections(id) ON DELETE CASCADE,
                position INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
                type TEXT NOT NULL CHECK (type IN ('text','photo','document','video','audio','animation')),
                text TEXT,
                file_id TEXT,
                caption TEXT,
                position INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_sections_parent ON sections(parent_id);
            CREATE INDEX IF NOT EXISTS idx_items_section ON items(section_id);
            """
        )
        db.commit()


def fetch_sections(parent_id: Optional[int]) -> List[sqlite3.Row]:
    with closing(get_db()) as db:
        cur = db.execute(
            "SELECT * FROM sections WHERE parent_id IS ? ORDER BY position, id",
            (parent_id,)
        )
        return cur.fetchall()


def fetch_section(section_id: int) -> Optional[sqlite3.Row]:
    with closing(get_db()) as db:
        cur = db.execute("SELECT * FROM sections WHERE id=?", (section_id,))
        return cur.fetchone()


def add_section(name: str, parent_id: Optional[int]) -> int:
    with closing(get_db()) as db:
        cur = db.execute(
            "INSERT INTO sections(name, parent_id, position) VALUES (?,?,?)",
            (name, parent_id, 0)
        )
        db.commit()
        return cur.lastrowid


def rename_section(section_id: int, new_name: str) -> None:
    with closing(get_db()) as db:
        db.execute("UPDATE sections SET name=? WHERE id=?", (new_name, section_id))
        db.commit()


def delete_section(section_id: int) -> None:
    with closing(get_db()) as db:
        db.execute("DELETE FROM sections WHERE id=?", (section_id,))
        db.commit()


def fetch_items(section_id: int) -> List[sqlite3.Row]:
    with closing(get_db()) as db:
        cur = db.execute(
            "SELECT * FROM items WHERE section_id=? ORDER BY position, id",
            (section_id,)
        )
        return cur.fetchall()


def fetch_item_page(section_id: int, page: int) -> Tuple[Optional[sqlite3.Row], int]:
    items = fetch_items(section_id)
    total = len(items)
    if total == 0:
        return None, 0
    page = max(0, min(page, total - 1))
    return items[page], total


def add_item(section_id: int, type_: str, text: Optional[str], file_id: Optional[str], caption: Optional[str]) -> int:
    with closing(get_db()) as db:
        cur = db.execute(
            "INSERT INTO items(section_id, type, text, file_id, caption, position) VALUES (?,?,?,?,?,0)",
            (section_id, type_, text, file_id, caption)
        )
        db.commit()
        return cur.lastrowid

# ---------------------- BOT SETUP ----------------------

bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ---------------------- KEYBOARDS ----------------------

HOME_BTN = InlineKeyboardButton("🏠 الرئيسية", callback_data="home")
BACK_PREFIX = "back:"  # back:<parent_id or 'root'>


def build_sections_kb(parent_id: Optional[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    sections = fetch_sections(parent_id)
    for s in sections:
        kb.insert(InlineKeyboardButton(f"📂 {s['name']}", callback_data=f"section:{s['id']}"))
    # Admin add-section shortcut
    kb.add(InlineKeyboardButton("➕ إضافة قسم", callback_data=f"admin:add_section:{parent_id if parent_id is not None else 'root'}"))

    # Nav row
    if parent_id is None:
        kb.add(HOME_BTN)  # home = main
    else:
        kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"{BACK_PREFIX}{'root' if fetch_section(parent_id)['parent_id'] is None else fetch_section(parent_id)['parent_id']}"), HOME_BTN)
    return kb


def build_section_view_kb(section_id: int, parent_id: Optional[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    # Subsections
    subsections = fetch_sections(section_id)
    for s in subsections:
        kb.insert(InlineKeyboardButton(f"📂 {s['name']}", callback_data=f"section:{s['id']}"))

    # Content navigation entry point
    kb.add(InlineKeyboardButton("▶️ عرض المحتوى", callback_data=f"show:{section_id}:0"))

    # Admin tools for this section
    kb.add(
        InlineKeyboardButton("✏️ إعادة تسمية", callback_data=f"admin:rename:{section_id}"),
        InlineKeyboardButton("🗑 حذف", callback_data=f"admin:delete:{section_id}")
    )
    kb.add(InlineKeyboardButton("➕ إضافة عنصر لهذا القسم", callback_data=f"admin:add_item:{section_id}"))

    # Nav row
    if parent_id is None:
        kb.add(HOME_BTN)
    else:
        kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"{BACK_PREFIX}{parent_id}"), HOME_BTN)

    return kb


def build_items_nav_kb(section_id: int, page: int, total: int, parent_id: Optional[int]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=3)
    prev_page = max(0, page - 1)
    next_page = min(total - 1, page + 1)
    kb.add(
        InlineKeyboardButton("⏮", callback_data=f"show:{section_id}:0"),
        InlineKeyboardButton("◀️", callback_data=f"show:{section_id}:{prev_page}"),
        InlineKeyboardButton(f"{page+1}/{total}", callback_data="noop"),
        InlineKeyboardButton("▶️", callback_data=f"show:{section_id}:{next_page}"),
        InlineKeyboardButton("⏭", callback_data=f"show:{section_id}:{total-1}")
    )
    if parent_id is None:
        kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"section:{section_id}"), HOME_BTN)
    else:
        kb.add(InlineKeyboardButton("⬅️ رجوع", callback_data=f"section:{section_id}"), HOME_BTN)
    return kb

# ---------------------- FSM STATES ----------------------

class AddSectionSG(StatesGroup):
    waiting_for_name = State()
    waiting_for_parent = State()

class RenameSectionSG(StatesGroup):
    waiting_for_name = State()

class AddItemSG(StatesGroup):
    waiting_for_section = State()
    waiting_for_item = State()

# ---------------------- HELPERS ----------------------

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def ensure_admin(call_or_msg):
    uid = call_or_msg.from_user.id
    if not is_admin(uid):
        if isinstance(call_or_msg, types.CallbackQuery):
            await call_or_msg.answer("❌ ليس لديك صلاحية", show_alert=True)
        else:
            await call_or_msg.answer("❌ ليس لديك صلاحية")
        return False
    return True

# ---------------------- HANDLERS (USER) ----------------------

@dp.message_handler(commands=["start", "menu", "home"])
async def cmd_start(message: types.Message):
    init_db()
    await message.answer("📌 القائمة الرئيسية:", reply_markup=ReplyKeyboardRemove())
    await message.answer("اختر قسمًا:", reply_markup=build_sections_kb(parent_id=None))


@dp.callback_query_handler(Text(equals="home"))
async def cb_home(call: types.CallbackQuery):
    await call.message.edit_text("📌 القائمة الرئيسية:")
    await call.message.edit_reply_markup(build_sections_kb(parent_id=None))


@dp.callback_query_handler(Text(startswith=BACK_PREFIX))
async def cb_back(call: types.CallbackQuery):
    target = call.data.split(":", 1)[1]
    parent_id = None if target == "root" else int(target)
    if parent_id is None:
        await cb_home(call)
    else:
        parent = fetch_section(parent_id)
        if not parent:
            await cb_home(call)
            return
        # parent of parent for the next back
        await call.message.edit_text(f"📂 {parent['name']}")
        await call.message.edit_reply_markup(build_section_view_kb(parent_id, parent['parent_id']))


@dp.callback_query_handler(Text(startswith="section:"))
async def cb_open_section(call: types.CallbackQuery):
    section_id = int(call.data.split(":")[1])
    section = fetch_section(section_id)
    if not section:
        await call.answer("⚠️ القسم غير موجود")
        return
    await call.message.edit_text(f"📂 <b>{section['name']}</b>")
    await call.message.edit_reply_markup(build_section_view_kb(section_id, section['parent_id']))


@dp.callback_query_handler(Text(startswith="show:"))
async def cb_show_item(call: types.CallbackQuery):
    _, sid, page_str = call.data.split(":")
    section_id = int(sid)
    page = int(page_str)
    item, total = fetch_item_page(section_id, page)
    section = fetch_section(section_id)
    if total == 0:
        await call.answer("لا يوجد محتوى في هذا القسم بعد")
        return

    # Replace current message with placeholder (to keep nav in one place)
    await call.message.edit_text(f"📂 <b>{section['name']}</b> — عنصر {page+1}/{total}")
    await call.message.edit_reply_markup(build_items_nav_kb(section_id, page, total, section['parent_id']))

    # Then send the actual item as a new message underneath
    if item["type"] == "text":
        await call.message.answer(item["text"] or "")
    elif item["type"] == "photo":
        await call.message.answer_photo(item["file_id"], caption=item["caption"])
    elif item["type"] == "document":
        await call.message.answer_document(item["file_id"], caption=item["caption"])
    elif item["type"] == "video":
        await call.message.answer_video(item["file_id"], caption=item["caption"])
    elif item["type"] == "audio":
        await call.message.answer_audio(item["file_id"], caption=item["caption"])
    elif item["type"] == "animation":
        await call.message.answer_animation(item["file_id"], caption=item["caption"])


# ---------------------- HANDLERS (ADMIN) ----------------------

@dp.message_handler(commands=["admin"])
async def cmd_admin(message: types.Message):
    if not await ensure_admin(message):
        return
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة قسم", callback_data="admin:add_section:root"),
        InlineKeyboardButton("✏️ إعادة تسمية قسم", callback_data="admin:rename:pick"),
        InlineKeyboardButton("🗑 حذف قسم", callback_data="admin:delete:pick"),
        InlineKeyboardButton("➕ إضافة عنصر لمحتوى قسم", callback_data="admin:add_item:pick"),
    )
    await message.answer("🛠 لوحة تحكم الأدمن:", reply_markup=kb)


# ---- Add Section ----
@dp.callback_query_handler(Text(startswith="admin:add_section:"))
async def admin_add_section(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin(call):
        return
    target = call.data.split(":")[-1]
    parent_id = None if target == "root" else int(target)
    await state.update_data(parent_id=parent_id)
    await AddSectionSG.waiting_for_name.set()
    await call.message.answer("✏️ أرسل اسم القسم الجديد:")


@dp.message_handler(state=AddSectionSG.waiting_for_name)
async def admin_add_section_name(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    data = await state.get_data()
    parent_id = data.get("parent_id")
    sid = add_section(message.text.strip(), parent_id)
    await message.answer(f"✅ تم إنشاء القسم: <b>{message.text.strip()}</b>")
    await state.finish()
    # Refresh current menu
    if parent_id is None:
        await message.answer("📌 القائمة الرئيسية:", reply_markup=build_sections_kb(parent_id=None))
    else:
        parent = fetch_section(parent_id)
        await message.answer(f"📂 {parent['name']}", reply_markup=build_section_view_kb(parent_id, parent['parent_id']))


# ---- Rename Section ----
@dp.callback_query_handler(Text(startswith="admin:rename:"))
async def admin_rename_pick(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin(call):
        return
    parts = call.data.split(":")
    if parts[-1] == "pick":
        # Ask for section id
        await call.message.answer("📌 أرسل رقم معرف القسم (ID) الذي تريد إعادة تسميته.\nيمكنك الحصول على ID بالضغط مطولًا على رسالة عرض القسم (أو أرسل /list لتفاصيل).")
        await RenameSectionSG.waiting_for_name.set()
        await state.update_data(stage="ask_id")
    else:
        # direct rename from a specific section
        section_id = int(parts[-1])
        await state.update_data(section_id=section_id)
        await RenameSectionSG.waiting_for_name.set()
        await call.message.answer("✏️ أرسل الاسم الجديد للقسم:")


@dp.message_handler(commands=["list"])
async def cmd_list(message: types.Message):
    if not await ensure_admin(message):
        return
    # Simple tree dump
    def dump(parent_id: Optional[int], indent: int) -> List[str]:
        lines: List[str] = []
        for s in fetch_sections(parent_id):
            lines.append("  "*indent + f"- {s['name']} (ID={s['id']})")
            lines.extend(dump(s['id'], indent+1))
        return lines
    tree = "\n".join(dump(None, 0)) or "(لا توجد أقسام بعد)"
    await message.answer(f"<pre>{tree}</pre>")


@dp.message_handler(state=RenameSectionSG.waiting_for_name)
async def admin_rename_section(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    data = await state.get_data()
    stage = data.get("stage")
    if stage == "ask_id":
        try:
            section_id = int(message.text.strip())
        except ValueError:
            await message.answer("❌ أرسل رقمًا صحيحًا للـ ID.")
            return
        sec = fetch_section(section_id)
        if not sec:
            await message.answer("⚠️ قسم غير موجود.")
            return
        await state.update_data(section_id=section_id, stage="ask_name")
        await message.answer("✏️ أرسل الاسم الجديد:")
        return

    section_id = data.get("section_id")
    new_name = message.text.strip()
    rename_section(section_id, new_name)
    await state.finish()
    await message.answer("✅ تم التحديث.")


# ---- Delete Section ----
@dp.callback_query_handler(Text(startswith="admin:delete:"))
async def admin_delete_section(call: types.CallbackQuery):
    if not await ensure_admin(call):
        return
    target = call.data.split(":")[-1]
    if target == "pick":
        await call.message.answer("🗑 أرسل ID القسم الذي تريد حذفه (يحذف محتواه وكل فروعه):")
        dp.register_message_handler(admin_delete_receive_id, content_types=types.ContentTypes.TEXT, state=None)
    else:
        section_id = int(target)
        delete_section(section_id)
        await call.message.answer("✅ تم حذف القسم.")


async def admin_delete_receive_id(message: types.Message):
    if not await ensure_admin(message):
        return
    try:
        sid = int(message.text.strip())
    except ValueError:
        await message.answer("❌ أرسل رقم ID صحيح.")
        return
    delete_section(sid)
    await message.answer("✅ تم الحذف.")
    # Unregister this ad-hoc handler
    dp.message_handlers.unregister(admin_delete_receive_id)


# ---- Add Item ----
@dp.callback_query_handler(Text(startswith="admin:add_item:"))
async def admin_add_item(call: types.CallbackQuery, state: FSMContext):
    if not await ensure_admin(call):
        return
    target = call.data.split(":")[-1]
    if target == "pick":
        await call.message.answer("📌 أرسل ID القسم الذي تريد الإضافة إليه (أو اكتب اسمه بالضبط):")
        await AddItemSG.waiting_for_section.set()
    else:
        section_id = int(target)
        await state.update_data(section_id=section_id)
        await AddItemSG.waiting_for_item.set()
        await call.message.answer("📎 أرسل المحتوى الآن (نص/صورة/ملف/فيديو/صوت/صورة متحركة).\nيمكنك أيضًا إضافة توضيح (Caption) للوسائط.")


@dp.message_handler(state=AddItemSG.waiting_for_section)
async def admin_add_item_pick_section(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    text = message.text.strip()
    sid: Optional[int] = None
    # Try ID first
    try:
        sid = int(text)
    except ValueError:
        # Try by exact name at any depth (first match)
        with closing(get_db()) as db:
            cur = db.execute("SELECT id FROM sections WHERE name=? ORDER BY id LIMIT 1", (text,))
            row = cur.fetchone()
            if row:
                sid = row["id"]
    if sid is None or not fetch_section(sid):
        await message.answer("⚠️ قسم غير موجود. أعد المحاولة بإرسال ID أو اسم مطابق.")
        return
    await state.update_data(section_id=sid)
    await AddItemSG.waiting_for_item.set()
    await message.answer("📎 أرسل المحتوى الآن (نص/صورة/ملف/فيديو/صوت/صورة متحركة).\nيمكنك إضافة Caption.")


@dp.message_handler(state=AddItemSG.waiting_for_item, content_types=types.ContentTypes.ANY)
async def admin_add_item_receive(message: types.Message, state: FSMContext):
    if not await ensure_admin(message):
        return
    data = await state.get_data()
    section_id = data.get("section_id")

    ctype = message.content_type
    file_id = None
    text = None
    caption = None

    if ctype == types.ContentType.TEXT:
        type_ = "text"
        text = message.html_text
    elif ctype == types.ContentType.PHOTO:
        type_ = "photo"
        file_id = message.photo[-1].file_id
        caption = message.html_caption
    elif ctype == types.ContentType.DOCUMENT:
        type_ = "document"
        file_id = message.document.file_id
        caption = message.html_caption
    elif ctype == types.ContentType.VIDEO:
        type_ = "video"
        file_id = message.video.file_id
        caption = message.html_caption
    elif ctype == types.ContentType.AUDIO:
        type_ = "audio"
        file_id = message.audio.file_id
        caption = message.html_caption
    elif ctype == types.ContentType.ANIMATION:
        type_ = "animation"
        file_id = message.animation.file_id
        caption = message.html_caption
    else:
        await message.answer("⚠️ نوع غير مدعوم حاليًا.")
        return

    add_item(section_id, type_, text, file_id, caption)
    await state.finish()
    await message.answer("✅ تم إضافة العنصر إلى القسم.")


# ---------------------- FALLBACKS ----------------------

@dp.callback_query_handler(Text(equals="noop"))
async def cb_noop(call: types.CallbackQuery):
    await call.answer("")


@dp.errors_handler()
async def on_error(update, error):
    # Minimal generic error handler
    try:
        if isinstance(update, types.Update) and update.callback_query:
            await update.callback_query.answer("حدث خطأ غير متوقع.", show_alert=True)
    except Exception:
        pass
    return True


# ---------------------- MAIN ----------------------
if __name__ == "__main__":
    init_db()
    print("Bot is running...")
    executor.start_polling(dp, skip_updates=True)

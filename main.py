"""
📚 Course Materials Telegram Bot
Built for Amoud University students
"""

import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ─────────────────────────────────────────────
# CONFIGURATION — edit these two lines only
# ─────────────────────────────────────────────
BOT_TOKEN     = "8893149580:AAGv1IqqklllpgghOJTCLy7XB0BIGWyur28"   # From @BotFather
ADMIN_IDS     = [1407379732]         # Your Telegram numeric ID
MATERIALS_DIR = "materials"
BOT_NAME      = "Amoud University"
# ─────────────────────────────────────────────

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


def get_courses():
    os.makedirs(MATERIALS_DIR, exist_ok=True)
    return sorted(d for d in os.listdir(MATERIALS_DIR)
                  if os.path.isdir(os.path.join(MATERIALS_DIR, d)))

def get_files(course):
    path = os.path.join(MATERIALS_DIR, course)
    if not os.path.isdir(path):
        return []
    return sorted(f for f in os.listdir(path)
                  if os.path.isfile(os.path.join(path, f)))

def is_admin(user_id):
    return user_id in ADMIN_IDS

def courses_keyboard():
    courses = get_courses()
    rows = [[InlineKeyboardButton(f"📘 {c}", callback_data=f"COURSE|{c}")] for c in courses]
    if not courses:
        rows = [[InlineKeyboardButton("⚠️ No courses yet", callback_data="NOOP")]]
    return InlineKeyboardMarkup(rows)

def chapters_keyboard(course):
    files = get_files(course)
    rows = []
    for f in files:
        label = os.path.splitext(f)[0]
        rows.append([InlineKeyboardButton(f"📄 {label}", callback_data=f"FILE|{course}|{f}")])
    rows.append([InlineKeyboardButton("⬅️ Back to Courses", callback_data="BACK|courses")])
    return InlineKeyboardMarkup(rows)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello *{user}*! Welcome to the *{BOT_NAME}* materials bot.\n\n"
        "📚 Select a course below to browse and download chapters:",
        parse_mode="Markdown",
        reply_markup=courses_keyboard()
    )

async def cmd_courses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Available Courses:*\nTap a course to see its chapters.",
        parse_mode="Markdown",
        reply_markup=courses_keyboard()
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_section = ""
    if is_admin(update.effective_user.id):
        admin_section = (
            "\n\n*🔐 Admin Commands:*\n"
            "`/addcourse Name` — Create a new course\n"
            "`/upload Course Name` — Set course, then send files\n"
            "`/listcourses` — List all courses and files\n"
            "`/deletefile Course | file.pdf` — Delete a file"
        )
    await update.message.reply_text(
        "📖 *Help*\n\n"
        "`/start` — Show course list\n"
        "`/courses` — Browse courses\n"
        "`/help` — Show this message"
        + admin_section,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "NOOP":
        return

    if data.startswith("COURSE|"):
        course = data.split("|", 1)[1]
        files = get_files(course)
        if not files:
            await query.edit_message_text(
                f"📘 *{course}*\n\n⚠️ No files uploaded yet.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Back", callback_data="BACK|courses")
                ]])
            )
        else:
            await query.edit_message_text(
                f"📘 *{course}*\n\nSelect a chapter to download 👇",
                parse_mode="Markdown",
                reply_markup=chapters_keyboard(course)
            )

    elif data.startswith("FILE|"):
        _, course, filename = data.split("|", 2)
        file_path = os.path.join(MATERIALS_DIR, course, filename)
        if not os.path.exists(file_path):
            await query.edit_message_text("❌ File not found. Contact your instructor.")
            return
        await query.edit_message_text(f"⏳ Sending *{filename}*…", parse_mode="Markdown")
        with open(file_path, "rb") as f:
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=filename,
                caption=f"📘 *{course}*\n📄 {os.path.splitext(filename)[0]}",
                parse_mode="Markdown"
            )
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Done! Need another file?",
            reply_markup=chapters_keyboard(course)
        )

    elif data.startswith("BACK|"):
        await query.edit_message_text(
            "📚 *Course List*\n\nSelect a course:",
            parse_mode="Markdown",
            reply_markup=courses_keyboard()
        )

async def cmd_addcourse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/addcourse Course Name`", parse_mode="Markdown")
        return
    name = " ".join(context.args)
    os.makedirs(os.path.join(MATERIALS_DIR, name), exist_ok=True)
    await update.message.reply_text(f"✅ Course *{name}* created!", parse_mode="Markdown")

async def cmd_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: `/upload Course Name`", parse_mode="Markdown")
        return
    course = " ".join(context.args)
    os.makedirs(os.path.join(MATERIALS_DIR, course), exist_ok=True)
    context.user_data["upload_course"] = course
    await update.message.reply_text(
        f"📤 Ready! Send files and they'll go into *{course}*.",
        parse_mode="Markdown"
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    course = context.user_data.get("upload_course")
    if not course:
        await update.message.reply_text(
            "⚠️ No course selected. Use `/upload Course Name` first.",
            parse_mode="Markdown"
        )
        return
    doc = update.message.document
    course_dir = os.path.join(MATERIALS_DIR, course)
    os.makedirs(course_dir, exist_ok=True)
    tg_file = await doc.get_file()
    await tg_file.download_to_drive(os.path.join(course_dir, doc.file_name))
    await update.message.reply_text(
        f"✅ *{doc.file_name}* saved to *{course}*!",
        parse_mode="Markdown"
    )

async def cmd_listcourses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    courses = get_courses()
    if not courses:
        await update.message.reply_text("No courses yet.")
        return
    lines = ["📂 *All Courses & Files:*\n"]
    for c in courses:
        files = get_files(c)
        lines.append(f"📘 *{c}* — {len(files)} file(s)")
        for f in files:
            lines.append(f"  • {f}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_deletefile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    full = " ".join(context.args)
    if "|" not in full:
        await update.message.reply_text("Usage: `/deletefile Course | filename.pdf`", parse_mode="Markdown")
        return
    course, filename = [x.strip() for x in full.split("|", 1)]
    path = os.path.join(MATERIALS_DIR, course, filename)
    if os.path.exists(path):
        os.remove(path)
        await update.message.reply_text(f"🗑️ Deleted *{filename}*.", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ File not found.", parse_mode="Markdown")


async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("courses", cmd_courses))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("addcourse", cmd_addcourse))
    app.add_handler(CommandHandler("upload", cmd_upload))
    app.add_handler(CommandHandler("listcourses", cmd_listcourses))
    app.add_handler(CommandHandler("deletefile", cmd_deletefile))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("🤖 Bot is running! Press Ctrl+C to stop.")

    async with app:
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        await asyncio.Event().wait()  # Run forever


if __name__ == "__main__":
    asyncio.run(main())

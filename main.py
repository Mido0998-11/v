import os
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from engine import SUSTEngine

# سيرفر الـ Keep Alive لـ Render
web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Full Core Online"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

STEP_USER, STEP_PASS = range(2)
user_sessions = {}
user_names = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions:
        name = user_names.get(cid, "دكتور")
        kb = [['📚 مقرراتي الدراسية'], ['📊 كشف الدرجات الشامل'], ['🚪 تسجيل خروج']]
        await update.message.reply_text(
            f"✨ **مرحباً بك مجدداً، {name}**\nكل صلاحيات المنصة مفتوحة لك الآن في البوت.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown'
        )
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text(
            "🔒 **نظام SUST المتكامل - الوصول مقيد!**\n\nالبوت مقفل بالكامل لضمان أمن البيانات الأكاديمية. يرجى تسجيل دخولك أولاً لفتح السستم الدراسي الخاص بك.",
            reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown'
        )

# --- محادثة الدخول المتسلسلة الدقيقة ---
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 **الخطوة 1:** أرسل **الرقم الجامعي** الخاص بك:", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
    return STEP_USER

async def process_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("🔑 **الخطوة 2:** أرسل **كلمة المرور** الخاصة بك:\n_(سيتم حذفها فوراً لحماية حسابك الجامعي 🛡️)_", parse_mode='Markdown')
    return STEP_PASS

async def process_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['username']
    cid = update.effective_chat.id
    
    try: await update.message.delete()
    except: pass
    
    status_msg = await update.message.reply_text("⏳ جاري تسجيل الدخول وفحص الهوية الأكاديمية وصيد اسمك...")
    
    engine = SUSTEngine()
    if engine.login(user, pw):
        user_sessions[cid] = engine
        data = engine.get_profile_and_courses()
        real_name = data['name']
        user_names[cid] = real_name
        
        await context.bot.edit_message_text(
            chat_id=cid, message_id=status_msg.message_id,
            text=f"🎉 **مرحباً بك دكتور: {real_name}**\n\n✅ تم التحقق من هويتك الجامعية بنجاح! السستم جاهز بالكامل.",
            parse_mode='Markdown'
        )
        kb = [['📚 مقرراتي الدراسية'], ['📊 كشف الدرجات الشامل'], ['🚪 تسجيل خروج']]
        await context.bot.send_message(chat_id=cid, text="🗂️ استخدم القائمة للتحكم الكامل في حساب المنصة:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text="❌ **فشل التحقق!** البيانات غير مطابقة لسجلات الجامعة. اضغط على الزر وأعد المحاولة.")
        await context.bot.send_message(chat_id=cid, text="🔄 إعادة المحاولة:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END

# --- الحارس الحديدي وعرض البيانات ---
async def strict_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    text = update.message.text
    
    if cid in user_sessions:
        if text == '📚 مقرراتي الدراسية':
            status = await update.message.reply_text("🔍 جاري جلب وقراءة المواد المسجلة الحالية...")
            data = user_sessions[cid].get_profile_and_courses()
            courses = data['courses']
            if not courses:
                await status.edit_text("📭 لم نجد مواد نشطة في حسابك حالياً.")
                return
            btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
            await status.edit_text("📚 **اختر المقرر لعرض (كل المحاضرات، الفيديوهات، الشيتات):**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
        
        elif text == '📊 كشف الدرجات الشامل':
            status = await update.message.reply_text("📊 جاري سحب كشف العلامات الحالي من الكنترول...")
            grades = user_sessions[cid].get_student_grades()
            if not grades:
                await status.edit_text("🧐 لم نجد درجات مرصودة حالياً أو أن صفحة العلامات مغلقة من الجامعة.")
                return
            
            report = f"📊 **كشف الدرجات الأكاديمي للطالب: {user_names.get(cid, '')}**\n\n"
            for g in grades:
                report += f"🔹 *{g['course']}:*\n🎯 الدرجة: `{g['grade']}`\n\n"
            await status.edit_text(report, parse_mode='Markdown')
            
        elif text == '🚪 تسجيل خروج':
            if cid in user_sessions: del user_sessions[cid]
            if cid in user_names: del user_names[cid]
            kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
            await update.message.reply_text("🔒 تم تسجيل الخروج بنجاح وتأمين الحساب.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text("🚫 **الوصول مرفوض!** البوت مقفل تماماً. يجب عليك تسجيل الدخول أولاً لتتمكن من استخدامه.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if cid not in user_sessions:
        await query.message.reply_text("⚠️ انتهت جلستك الأمنية، يرجى إعادة تسجيل الدخول.")
        return

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        progress_msg = await query.message.reply_text("🔄 جاري فحص عميق للمادة وصيد كوووول المحتويات والفيديوهات المخفية...")
        
        all_content = user_sessions[cid].get_course_deep_content(course_id)
        if not all_content:
            await progress_msg.edit_text("📭 المنصة فارغة تماماً من أي ملفات أو محاضرات لهذه المادة حالياً.")
            return
            
        report_text = "🎁 **المحاضرات والمحتويات المرصودة في المادة:**\n\n"
        for item in all_content:
            report_text += f"{item['type']}:\n🔹 [{item['title']}]({item['url']})\n\n"
            
        await progress_msg.delete()
        await context.bot.send_message(chat_id=cid, text=report_text, parse_mode='Markdown', disable_web_page_preview=False)

if __name__ == '__main__':
    threading.Thread(target=run_web).start()
    app = ApplicationBuilder().token(TOKEN).build()
    
    login_wizard = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^🔐 ابدأ تسجيل الدخول الإلزامي$'), login_start)],
        states={
            STEP_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_user)],
            STEP_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_pass)],
        },
        fallbacks=[CommandHandler('start', start)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(login_wizard)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, strict_guard))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.run_polling()

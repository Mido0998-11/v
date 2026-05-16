import os
import threading
import uuid
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, 
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from engine import SUSTEngine

web_app = Flask('')
@web_app.route('/')
def home(): return "SUST Full Platform Super Charged"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

STEP_USER, STEP_PASS = range(2)
user_sessions = {}
user_names = {}
video_storage = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions:
        name = user_names.get(cid, "يا دكتور")
        kb = [['📚 مقرراتي الدراسية', '📊 كشف الدرجات'], ['📅 المفكرة والأحداث', '👤 ملفي الشخصي'], ['🚪 تسجيل خروج']]
        await update.message.reply_text(f"✨ **مرحباً بك مجدداً، {name}**\nلوحة تحكم منصة جامعة السودان كاملة بين يديك الآن.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text("🔒 **بوابة جامعة السودان الذكية (SUST)**\n\nالسستم مقفل بشكل صارم وإلزامي؛ الرجاء إثبات هويتك الأكاديمية لفتح الصلاحيات وسحب ملفاتك وفيديوهاتك.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 **الخطوة 1:** أرسل **الرقم الجامعي** الخاص بك:", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
    return STEP_USER

async def process_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("🔑 **الخطوة 2:** أرسل **كلمة المرور** الخاصة بك:\n_(تنبيه: سيتم مسحها فوراً لحمايتك 🛡️)_", parse_mode='Markdown')
    return STEP_PASS

async def process_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['username']
    cid = update.effective_chat.id
    try: await update.message.delete()
    except: pass
    
    status_msg = await update.message.reply_text("⏳ جاري فحص الحساب ومطابقة الاسم والبيانات في السستم الحقيقي...")
    engine = SUSTEngine()
    if engine.login(user, pw):
        user_sessions[cid] = engine
        prof = engine.get_user_profile()
        user_names[cid] = prof['name']
        
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text=f"🎉 **مرحباً بك دكتور: {prof['name']}**\n\n✅ تم تسجيل الدخول بنجاح! السستم مفتوح بالكامل الآن لك.", parse_mode='Markdown')
        kb = [['📚 مقرراتي الدراسية', '📊 كشف الدرجات'], ['📅 المفكرة والأحداث', '👤 ملفي الشخصي'], ['🚪 تسجيل خروج']]
        await context.bot.send_message(chat_id=cid, text="🗂️ القائمة الكاملة للمنصة:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text="❌ **فشل التحقق!** البيانات خاطئة. اضغط على الزر للبدء من جديد.")
        return ConversationHandler.END

async def strict_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    text = update.message.text
    
    if cid in user_sessions:
        engine = user_sessions[cid]
        if text == '📚 مقرراتي الدراسية':
            status = await update.message.reply_text("🔍 جاري فحص صفحة المقررات الشاملة وسحب المواد...")
            courses = engine.get_courses()
            if not courses:
                await status.edit_text("📭 لم نجد مواد مسجلة حالياً.")
                return
            btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
            await status.edit_text("📚 **اختر المقرر لتصفح (الفيديوهات والملفات والشيتات):**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
        
        elif text == '📊 كشف الدرجات':
            status = await update.message.reply_text("📊 جاري قراءة الكنترول وسحب علاماتك الدراسية...")
            grades = engine.get_student_grades()
            if not grades:
                await status.edit_text("🧐 لا توجد درجات مرصودة حتى الآن.")
                return
            report = "📊 **كشف الدرجات الأكاديمي الحالي:**\n\n"
            for g in grades: report += f"🔹 *{g['course']}:*\n🎯 الدرجة: `{g['grade']}`\n\n"
            await status.edit_text(report, parse_mode='Markdown')
            
        elif text == '📅 المفكرة والأحداث':
            status = await update.message.reply_text("📅 جاري فحص تقويم المنصة للأحداث والواجبات...")
            events = engine.get_calendar_events()
            if not events:
                await status.edit_text("✅ لا توجد أحداث أو واجبات قادمة مطلوبة منك حالياً.")
                return
            report = "📅 **الأحداث والواجبات القادمة في التقويم:**\n\n"
            for e in events: report += f"🚨 *{e['title']}*\n⏰ الموعد: `{e['date']}`\n\n"
            await status.edit_text(report, parse_mode='Markdown')
            
        elif text == '👤 ملفي الشخصي':
            prof = engine.get_user_profile()
            report = f"👤 **الملف الأكاديمي للطالب:**\n\nاسم الطالب: `{prof['name']}`\nالبريد الإلكتروني: `{prof['email']}`\nالحالة الأكاديمية: نشط ✅"
            await update.message.reply_text(report, parse_mode='Markdown')
            
        elif text == '🚪 تسجيل خروج':
            if cid in user_sessions: del user_sessions[cid]
            kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
            await update.message.reply_text("🔒 تم تسجيل الخروج بنجاح وتأمين بياناتك الأكاديمية.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text("🚫 **الوصول مرفوض!** البوت محمي، يرجى تسجيل الدخول أولاً.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if cid not in user_sessions:
        await query.message.reply_text("⚠️ انتهت جلستك الأمنيّة.")
        return

    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        progress = await query.message.reply_text("🔄 جاري الكشط المتعمق وقراءة كافة الفيديوهات والمحاضرات القديمة والحالية...")
        
        all_content = user_sessions[cid].get_course_deep_content(course_id)
        if not all_content:
            await progress.edit_text("📭 المادة لا تحتوي على ملفات أو فيديوهات مرفوعة.")
            return
            
        await progress.delete()
        for item in all_content:
            if "🎥 فيديو مباشر" in item['type']:
                vid_id = str(uuid.uuid4())[:8]
                video_storage[vid_id] = item['url']
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ تشغيل فوري داخل تلجرام", callback_data=f"play_{vid_id}")]])
                await context.bot.send_message(chat_id=cid, text=f"🎬 **محاضرة مرئية مكتشفة:**\n🔹 {item['title']}", reply_markup=btn, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=cid, text=f"{item['type']}:\n🔹 [{item['title']}]({item['url']})", parse_mode='Markdown')

    elif query.data.startswith("play_"):
        vid_id = query.data.split("_")[1]
        video_url = video_storage.get(vid_id)
        if not video_url:
            await query.message.reply_text("⚠️ الرابط منتهي.")
            return
            
        loading = await query.message.reply_text("📥 جاري الدفق السريع للمحاضرة المرئية وتشغيلها داخل مشغل تلجرام... انتظر لحظات...")
        try:
            engine = user_sessions[cid]
            res = engine.session.get(video_url, stream=True, timeout=30)
            cl = res.headers.get('Content-Length')
            size = int(cl) if cl else 0
            
            if 0 < size < 50 * 1024 * 1024:
                await context.bot.send_video(
                    chat_id=cid, video=res.raw, filename="lecture.mp4",
                    supports_streaming=True, caption="🎬 **مشاهدة ممتعة! تم دفق المحاضرة بنجاح.**", parse_mode='Markdown'
                )
                await loading.delete()
            else:
                await loading.edit_text(f"ℹ️ حجم المحاضرة كبير جداً ({round(size/(1024*1024), 1)} MB)، يمكنك مشاهدتها فوراً في المتصفح من الرابط السريع المباشر:\n\n🔗 {video_url}")
        except:
            await loading.edit_text(f"🎥 يمكنك فتح الرابط ومشاهدة المحاضرة من المتصفح فوراً دون استهلاك كوكيز السيرفر:\n\n🔗 {video_url}")

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

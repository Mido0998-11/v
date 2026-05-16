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
def home(): return "SUST Streaming Core Active"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host='0.0.0.0', port=port)

TOKEN = os.environ.get('BOT_TOKEN', '8215409550:AAGAZazGrhP8-vqn9XwrHJu0pVuZuhTTd0s')

STEP_USER, STEP_PASS = range(2)
user_sessions = {}
user_names = {}
video_storage = {} # تخزين مؤقت لروابط الفيديوهات الطويلة لتلجرام

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid in user_sessions:
        name = user_names.get(cid, "دكتور")
        kb = [['📚 مقرراتي الدراسية'], ['📊 كشف الدرجات الشامل'], ['🚪 تسجيل خروج']]
        await update.message.reply_text(f"✨ **مرحباً بك مجدداً، {name}**\nكل سستم المنصة جاهز تحت أمرك الآن.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text("🔒 **بوابة جامعة السودان الأمنية**\n\nالسستم مقفل بالكامل، يرجى إثبات هويتك الأكاديمية لتتمكن من تشغيل المحاضرات وسحب الملفات والدرجات.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True), parse_mode='Markdown')

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👤 **الخطوة 1:** أرسل **الرقم الجامعي** الخاص بك:", reply_markup=ReplyKeyboardRemove(), parse_mode='Markdown')
    return STEP_USER

async def process_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("🔑 **الخطوة 2:** أرسل **كلمة المرور** الخاصة بك:\n_(سيتم حذفها فوراً تلقائياً للأمان التام 🛡️)_", parse_mode='Markdown')
    return STEP_PASS

async def process_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pw = update.message.text
    user = context.user_data['username']
    cid = update.effective_chat.id
    try: await update.message.delete()
    except: pass
    
    status_msg = await update.message.reply_text("⏳ جاري فحص الحساب ومطابقة الهوية في سستم الجامعة الأكاديمي...")
    engine = SUSTEngine()
    if engine.login(user, pw):
        user_sessions[cid] = engine
        data = engine.get_profile_and_courses()
        real_name = data['name']
        user_names[cid] = real_name
        
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text=f"🎉 **مرحباً بك دكتور: {real_name}**\n\n✅ تم التحقق بنجاح وفتح كامل المنصة داخل البوت!", parse_mode='Markdown')
        kb = [['📚 مقرراتي الدراسية'], ['📊 كشف الدرجات الشامل'], ['🚪 تسجيل خروج']]
        await context.bot.send_message(chat_id=cid, text="🗂️ تحكم بكامل المنصة من القائمة أدناه:", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
        return ConversationHandler.END
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await context.bot.edit_message_text(chat_id=cid, message_id=status_msg.message_id, text="❌ **بيانات خاطئة!** لم نتمكن من مطابقة الحساب. اضغط على الزر وحاول مجدداً.")
        return ConversationHandler.END

async def strict_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    text = update.message.text
    
    if cid in user_sessions:
        if text == '📚 مقرراتي الدراسية':
            status = await update.message.reply_text("🔍 جاري فحص حسابك وسحب المقررات الحالية والقديمة المتاحة...")
            data = user_sessions[cid].get_profile_and_courses()
            courses = data['courses']
            if not courses:
                await status.edit_text("📭 لم نجد مواد مسجلة نشطة حالياً في البروفايل.")
                return
            btns = [[InlineKeyboardButton(f"📖 {c['name']}", callback_data=f"c_{c['id']}")] for c in courses]
            await status.edit_text("📚 **اختر المادة لعرض (كل محتوياتها ومحاضراتها المرئية):**", reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
        
        elif text == '📊 كشف الدرجات الشامل':
            status = await update.message.reply_text("📊 جاري فحص وتجميع كشف العلامات الحالي...")
            grades = user_sessions[cid].get_student_grades()
            if not grades:
                await status.edit_text("🧐 لم يتم رصد درجات حالياً أو أن صفحة الكنترول مغلقة.")
                return
            report = f"📊 **كشف الدرجات الأكاديمي الشامل للجامعة:**\n\n"
            for g in grades: report += f"🔹 *{g['course']}:*\n🎯 الدرجة المرصودة: `{g['grade']}`\n\n"
            await status.edit_text(report, parse_mode='Markdown')
            
        elif text == '🚪 تسجيل خروج':
            if cid in user_sessions: del user_sessions[cid]
            kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
            await update.message.reply_text("🔒 تم تسجيل الخروج بنجاح وتأمين بياناتك.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))
    else:
        kb = [['🔐 ابدأ تسجيل الدخول الإلزامي']]
        await update.message.reply_text("🚫 **الوصول مرفوض تماماً!** السستم مغلق ومحمي، سجل دخولك أولاً لتتمكن من استخدامه.", reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cid = update.effective_chat.id

    if cid not in user_sessions:
        await query.message.reply_text("⚠️ انتهت جلستك، أعد تسجيل الدخول.")
        return

    # 1. عند اختيار مادة: نعرض كل شيء (ملفات، مجلدات، صفحات)
    if query.data.startswith("c_"):
        course_id = query.data.split("_")[1]
        progress = await query.message.reply_text("🔄 جاري عمل فحص عميق للمادة وقراءة كل الملفات والمحاضرات المرفوعة حالياً وسابقاً...")
        
        all_content = user_sessions[cid].get_course_deep_content(course_id)
        if not all_content:
            await progress.edit_text("📭 لا توجد ملفات أو محتويات مرفوعة داخل هذه المادة حالياً.")
            return
            
        await progress.delete()
        
        # إرسال المحتويات العادية، وإذا كان فيديو نضع له زر تشغيل فوري جوه تلجرام
        for item in all_content:
            if "🎥 فيديو مباشر" in item['type']:
                vid_id = str(uuid.uuid4())[:8] # توليد ID قصير للرابط
                video_storage[vid_id] = item['url']
                btn = InlineKeyboardMarkup([[InlineKeyboardButton("▶️ تشغيل المحاضرة داخل تلجرام", callback_data=f"play_{vid_id}")]])
                await context.bot.send_message(chat_id=cid, text=f"🎬 **محاضرة مرئية مكتشفة:**\n🔹 {item['title']}", reply_markup=btn, parse_mode='Markdown')
            else:
                await context.bot.send_message(chat_id=cid, text=f"{item['type']}:\n🔹 [{item['title']}]({item['url']})", parse_mode='Markdown')

    # 2. ماسورة الدفق (هنا السحر! تشغيل الفيديو مباشرة جوه تلجرام)
    elif query.data.startswith("play_"):
        vid_id = query.data.split("_")[1]
        video_url = video_storage.get(vid_id)
        if not video_url:
            await query.message.reply_text("⚠️ الرابط منتهي الصلاحية، يرجى إعادة تحديث قائمة المواد.")
            return
            
        loading = await query.message.reply_text("📥 جاري فتح قناة آمنة ودفق المحاضرة المرئية لتشغيلها داخل تلجرام مباشرة... انتظر ثواني...")
        
        try:
            engine = user_sessions[cid]
            # طلب دفق البيانات لايف بالكوكيز حقت الطالب
            res = engine.session.get(video_url, stream=True, timeout=30)
            cl = res.headers.get('Content-Length')
            size = int(cl) if cl else 0
            
            # إذا كان الفيديو حجمه أقل من 50 ميجا (حد رفع تلجرام الأقصى للبوتات)
            if 0 < size < 50 * 1024 * 1024:
                await context.bot.send_video(
                    chat_id=cid,
                    video=res.raw, # ضخ محتوى السيرفر مباشرة لتلجرام دون حفظه في الرام
                    filename="lecture.mp4",
                    supports_streaming=True, # السماح للمستخدم بتشغيله فوراً أثناء التحميل المباشر
                    caption="🎬 **تم دفق المحاضرة بنجاح وجاهزة للمشاهدة الفورية!**",
                    parse_mode='Markdown'
                )
                await loading.delete()
            else:
                # إذا كان أكبر من 50 ميجا، نرسل له رابط المشاهدة المباشر يفتح في المتصفح تلقائياً
                await loading.edit_text(f"ℹ️ حجم هذه المحاضرة كبير جداً ({round(size/(1024*1024), 1)} MB) ويتخطى حد الدفق السريع لبوتات تلجرام، يمكنك الضغط على الرابط ومشاهدته فوراً في المتصفح:\n\n🔗 {video_url}")
        except Exception as e:
            await loading.edit_text(f"🔗 سيرفر الجامعة يمنع البث الخارجي المباشر، يمكنك فتح الرابط ومشاهدته من المتصفح فوراً:\n\n{video_url}")

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

# main.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from sympy import *
from sympy.parsing.sympy_parser import parse_expr
from PIL import Image
import pytesseract
import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# تعريف الرموز
x, y, z = symbols("x y z")
init_printing(use_unicode=True)

# تفعيل Tesseract على ويندوز فقط:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

CHOOSE_OPERATION, ENTER_EXPRESSION = range(2)
user_state = {}

# بدء البوت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("تكامل", callback_data="integrate"),
         InlineKeyboardButton("مشتقة", callback_data="diff")],
        [InlineKeyboardButton("حل معادلة", callback_data="solve_eq"),
         InlineKeyboardButton("نظام معادلات", callback_data="solve_system")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("مرحبًا! اختر نوع العملية:", reply_markup=reply_markup)
    return CHOOSE_OPERATION

# عند اختيار عملية من الأزرار
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_state[query.from_user.id] = query.data
    await query.edit_message_text("أدخل التعبير أو المعادلة:")
    return ENTER_EXPRESSION

# تحليل النص
async def expression_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    operation = user_state.get(user_id)

    try:
        text = text.replace("^", "**")
        result, steps = "", ""

        if operation == "solve_eq":
            lhs, rhs = text.split("=")
            equation = Eq(parse_expr(lhs.strip()), parse_expr(rhs.strip()))
            result = solve(equation)
            steps = f"المعادلة:
{equation}
الحل:
{result}"

        elif operation == "solve_system":
            eqs = text.split(";")
            equations = [Eq(parse_expr(e.split("=")[0]), parse_expr(e.split("=")[1])) for e in eqs]
            result = solve(equations)
            steps = f"النظام:
" + "\n".join([str(eq) for eq in equations]) + f"\nالحل:
{result}"

        elif operation == "integrate":
            expr = parse_expr(text)
            result = integrate(expr)
            steps = f"التعبير:
{expr}
الخطوة 1: تحديد نوع التكامل
الخطوة 2: التكامل
النتيجة:
{result}"

        elif operation == "diff":
            if "," in text:
                expr, var = text.split(",")
                expr = parse_expr(expr.strip())
                var = Symbol(var.strip())
            else:
                expr = parse_expr(text)
                var = x
            result = diff(expr, var)
            steps = f"التعبير:
{expr}
المتغير: {var}
الخطوة 1: الاشتقاق
النتيجة:
{result}"

        else:
            steps = "عملية غير معروفة."

        await update.message.reply_text(steps)
    except Exception as e:
        await update.message.reply_text(f"حدث خطأ أثناء الحساب:
{str(e)}")

    return ConversationHandler.END

# OCR من صورة
async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await photo.get_file()
    path = f"image_{update.message.from_user.id}.png"
    await file.download_to_drive(path)

    try:
        text = pytesseract.image_to_string(Image.open(path), lang="ara+eng")
        os.remove(path)

        await update.message.reply_text(f"تم التعرف على النص:
{text}")

        if "=" in text:
            lhs, rhs = text.split("=")
            equation = Eq(parse_expr(lhs.strip()), parse_expr(rhs.strip()))
            result = solve(equation)
            await update.message.reply_text(f"المعادلة:
{equation}
الحل:
{result}")
        else:
            await update.message.reply_text("لم يتم العثور على معادلة تحتوي على '='.")
    except Exception as e:
        await update.message.reply_text(f"خطأ أثناء تحليل الصورة:
{str(e)}")

# إلغاء العملية
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

# تشغيل التطبيق
def main():
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_OPERATION: [CallbackQueryHandler(button_handler)],
            ENTER_EXPRESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, expression_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.PHOTO, image_handler))

    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()

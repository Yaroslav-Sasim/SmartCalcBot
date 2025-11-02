import os
from flask import Flask
from threading import Thread
import telebot
from telebot import types
from fractions import Fraction
import math
import re

# --- Токен и админ ---
BOT_TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = os.environ.get('ADMIN_ID')
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)

print("ADMIN_ID:", ADMIN_ID)

bot = telebot.TeleBot(BOT_TOKEN)

# --- Список пользователей (в памяти) ---
users = []

# --- Главное меню ---
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📏 Конвертер единиц", "🧮 Калькулятор процентов")
    markup.add("🌡 Температура", "➗ Дроби")
    markup.add("📐 Геометрия")
    return markup

# --- Старт ---
@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    print("Ваш chat.id:", chat_id)
    print("ADMIN_ID:", ADMIN_ID)

    if user_id not in users:
        users.append(user_id)

    bot.send_message(chat_id, "👋 Привет! Что хочешь посчитать?",
                     reply_markup=main_menu())

# --- Статистика для админа ---
@bot.message_handler(commands=['stats'])
def stats(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    if ADMIN_ID and user_id == ADMIN_ID:
        bot.send_message(chat_id, f"📊 Всего пользователей: {len(users)}")
    else:
        bot.send_message(chat_id, "⛔ У тебя нет прав для этой команды.")

# --- Обработчик меню ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    chat_id = message.chat.id
    text = message.text

    if text == "📏 Конвертер единиц":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📐 Длина", "⚖️ Масса", "🔙 Назад")
        bot.send_message(chat_id, "Выберите, что хотите конвертировать:", reply_markup=markup)

    elif text == "📐 Длина":
        select_unit_from(message)

    elif text == "⚖️ Масса":
        msg = bot.send_message(chat_id, "Введите массу в граммах:")
        bot.register_next_step_handler(msg, convert_mass)

    elif text == "🌡 Температура":
        msg = bot.send_message(chat_id, "Введите температуру в °C:")
        bot.register_next_step_handler(msg, convert_temperature)

    elif text == "🧮 Калькулятор процентов":
        msg = bot.send_message(chat_id, "Введите число и процент через пробел (например: 200 15):")
        bot.register_next_step_handler(msg, calculate_percent)

    elif text == "➗ Дроби":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📊 Десятичные", "➕ Обыкновенные", "🔙 Назад")
        msg = bot.send_message(chat_id, "Выберите, в каком виде вывести результат:", reply_markup=markup)
        bot.register_next_step_handler(msg, select_fraction_mode)

    elif text == "📐 Геометрия":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("⬛ Площадь", "📏 Периметр", "⚪ Радиус", "🔙 Назад")
        bot.send_message(chat_id, "Выберите, что хотите вычислить:", reply_markup=markup)

    elif text == "🔙 Назад":
        bot.send_message(chat_id, "Возвращаемся в меню 🔙", reply_markup=main_menu())

    else:
        bot.send_message(chat_id, "Пожалуйста, выбери вариант из меню 🙂", reply_markup=main_menu())

# --- Конвертер длины ---
units = ["мм", "см", "дм", "м", "км", "in", "ft"]
unit_factors = {"мм": 0.001, "см": 0.01, "дм": 0.1, "м": 1, "км": 1000, "in": 0.0254, "ft": 0.3048}

def select_unit_from(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for u in units:
        markup.add(u)
    markup.add("🔙 Назад")
    msg = bot.send_message(chat_id, "Выберите единицу, из которой конвертируем:", reply_markup=markup)
    bot.register_next_step_handler(msg, select_unit_to)

def select_unit_to(message):
    chat_id = message.chat.id
    if message.text not in units:
        bot.send_message(chat_id, "Пожалуйста, выберите единицу из меню 🙂", reply_markup=main_menu())
        return
    from_unit = message.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for u in units:
        if u != from_unit:
            markup.add(u)
    markup.add("🔙 Назад")
    msg = bot.send_message(chat_id, f"Выберите единицу, в которую конвертируем {from_unit}:", reply_markup=markup)
    bot.register_next_step_handler(msg, enter_value, from_unit)

def enter_value(message, from_unit):
    chat_id = message.chat.id
    if message.text not in units:
        bot.send_message(chat_id, "Пожалуйста, выберите единицу из меню 🙂", reply_markup=main_menu())
        return
    to_unit = message.text
    msg = bot.send_message(chat_id, f"Введите значение в {from_unit}:")
    bot.register_next_step_handler(msg, perform_conversion, from_unit, to_unit)

def perform_conversion(message, from_unit, to_unit):
    chat_id = message.chat.id
    try:
        value = float(message.text)
        meters = value * unit_factors[from_unit]
        result = meters / unit_factors[to_unit]
        bot.send_message(chat_id, f"📏 {value} {from_unit} = {result:.4f} {to_unit}", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "Введите число!", reply_markup=main_menu())

# --- Конвертер массы ---
def convert_mass(message):
    chat_id = message.chat.id
    try:
        grams = float(message.text)
        kilograms = grams / 1000
        bot.send_message(chat_id, f"⚖️ {grams:.2f} г = {kilograms:.2f} кг", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "Введите число!", reply_markup=main_menu())

# --- Температура ---
def convert_temperature(message):
    chat_id = message.chat.id
    try:
        celsius = float(message.text)
        fahrenheit = (celsius * 9 / 5) + 32
        bot.send_message(chat_id, f"🌡 {celsius:.2f}°C = {fahrenheit:.2f}°F", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "Введите число!", reply_markup=main_menu())

# --- Проценты ---
def calculate_percent(message):
    chat_id = message.chat.id
    try:
        num, percent = map(float, message.text.split())
        result = num * percent / 100
        bot.send_message(chat_id, f"🧮 {percent}% от {num} = {result:.2f}", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "Введите два числа через пробел!", reply_markup=main_menu())

# --- Дроби ---
user_state = {}

def select_fraction_mode(message):
    chat_id = message.chat.id
    mode = message.text

    if mode == "🔙 Назад":
        bot.send_message(chat_id, "Возвращаемся в меню 🔙", reply_markup=main_menu())
        return

    if mode == "📊 Десятичные":
        user_state[chat_id] = "decimal"
    elif mode == "➕ Обыкновенные":
        user_state[chat_id] = "fraction"
    else:
        bot.send_message(chat_id, "Выберите вариант из меню 🙂", reply_markup=main_menu())
        return

    msg = bot.send_message(chat_id, "Введите выражение с дробями (например: 1/2 + 3/4 * 2):")
    bot.register_next_step_handler(msg, calculate_fraction)

def calculate_fraction(message):
    chat_id = message.chat.id
    mode = user_state.get(chat_id, "fraction")
    expr = message.text.replace("×", "*").replace(":", "/").replace(" ", "")

    try:
        expr = re.sub(r'(\d+/\d+)', r'Fraction("\1")', expr)
        result = eval(expr, {"__builtins__": None}, {"Fraction": Fraction})

        if mode == "fraction":
            bot.send_message(chat_id, f"Результат: {result}")
        else:
            bot.send_message(chat_id, f"Результат: {float(result):.4f}")

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Ввести ещё", "🔙 Назад")
        msg = bot.send_message(chat_id, "Что делаем дальше?", reply_markup=markup)
        bot.register_next_step_handler(msg, handle_fraction_next_step)

    except Exception:
        bot.send_message(chat_id, "Ошибка в выражении. Пример: 1/2 + 3/4")
        msg = bot.send_message(chat_id, "Попробуем снова:")
        bot.register_next_step_handler(msg, calculate_fraction)

def handle_fraction_next_step(message):
    chat_id = message.chat.id
    if message.text == "Ввести ещё":
        msg = bot.send_message(chat_id, "Введите выражение с дробями:")
        bot.register_next_step_handler(msg, calculate_fraction)
    else:
        bot.send_message(chat_id, "Возвращаемся в меню 🔙", reply_markup=main_menu())

# --- Геометрия ---
def calculate_area(message):
    chat_id = message.chat.id
    try:
        a, b = map(float, message.text.split())
        result = a * b
        bot.send_message(chat_id, f"⬛ Площадь: {result:.2f}", reply_markup=main_menu())
    except:
        bot.send_message(chat_id, "Введите два числа через пробел!", reply_markup=main_menu())

def calculate_perimeter(message):
    chat_id = message.chat.id
    try:
        a, b = map(float, message.text.split())
        result = 2 * (a + b)
        bot.send_message(chat_id, f"📏 Периметр: {result:.2f}", reply_markup=main_menu())
    except:
        bot.send_message(chat_id, "Введите два числа через пробел!", reply_markup=main_menu())

def calculate_radius(message):
    chat_id = message.chat.id
    try:
        circumference = float(message.text)
        r = circumference / (2 * math.pi)
        bot.send_message(chat_id, f"⚪ Радиус: {r:.2f}", reply_markup=main_menu())
    except:
        bot.send_message(chat_id, "Введите число!", reply_markup=main_menu())

# --- Flask сервер для 24/7 ---
app = Flask('')

@app.route('/')
def home():
    return "Бот живой!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- Запуск ---
if __name__ == "__main__":
    print("Бот запущен...")
    Thread(target=run_flask).start()
    bot.infinity_polling()

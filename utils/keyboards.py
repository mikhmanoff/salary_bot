from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

# === Клавиатура главного меню ===
def create_main_menu():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="FAQ"), KeyboardButton(text="Авторизоваться")]
        ],
        resize_keyboard=True
    )
    return keyboard

# === Клавиатура выбора типа данных для зарплаты ===
def create_salary_type_buttons():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Зарплата за месяц", callback_data="salary_month")],
        [InlineKeyboardButton(text="Зарплата с начала года", callback_data="salary_year")],
        [InlineKeyboardButton(text="Зарплата за период", callback_data="salary_period")]
    ])
    return keyboard

# === Клавиатура для выбора месяца ===
def create_month_buttons(month_sheets):
    keyboard = []
    for sheet in month_sheets:
        button = InlineKeyboardButton(text=sheet, callback_data=f"month_{sheet}")
        keyboard.append([button])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

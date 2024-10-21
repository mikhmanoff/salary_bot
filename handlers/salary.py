from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from services.google_services import get_google_sheet
from services.sheet_operations import get_month_sheets, get_employee_data
from utils.keyboards import create_month_buttons

import asyncio

router = Router()

class SalaryStates(StatesGroup):
    waiting_for_month = State()
    waiting_for_period_start = State()
    waiting_for_period_end = State()
    
# === Создаем группу состояний для FSM ===
class AuthStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_passport_digits = State()
    waiting_for_salary_type = State()
    waiting_for_period_start = State()
    waiting_for_period_end = State()
    waiting_for_month = State()  # Для выбора зарплаты за месяц

@router.callback_query(StateFilter(AuthStates.waiting_for_salary_type), lambda c: c.data in ["salary_month", "salary_year", "salary_period"])
async def salary_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    salary_type = callback_query.data
    user_data = await state.get_data()
    file_id = user_data['file_id']

    sheet = get_google_sheet(file_id)
    month_sheets = get_month_sheets(sheet)

    if salary_type == "salary_month":
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты за месяц.")
        await callback_query.message.answer("Выберите месяц:", reply_markup=create_month_buttons(month_sheets))
        await state.set_state(SalaryStates.waiting_for_month)
    elif salary_type == "salary_year":
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты с начала года.")
        await sum_salary(callback_query.message, month_sheets, user_data['employee_id'], state)
        await state.clear()
    elif salary_type == "salary_period":
        await callback_query.message.edit_text("Вы выбрали просмотр зарплаты за период.")
        await callback_query.message.answer("Выберите начало периода:", reply_markup=create_month_buttons(month_sheets))
        await state.set_state(SalaryStates.waiting_for_period_start)

@router.callback_query(StateFilter(SalaryStates.waiting_for_month), lambda c: c.data.startswith("month_"))
async def month_salary_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    
    # Изменяем сообщение с кнопками
    await callback_query.message.edit_text(f"Вы выбрали месяц {selected_month}.")

    file_id = user_data['file_id']  # Получаем выбранный файл (год)

    # Получаем данные за конкретный месяц
    sheet = get_google_sheet(file_id).worksheet(selected_month)
    employee_data = get_employee_data(sheet, employee_id)
    
    print(sheet)

    if employee_data:
        # Используем метод .get() для безопасного доступа к значениям
        salary = employee_data.get('Зарплата', 'Не указано')
        taxes = employee_data.get('Налоги и удержания', 'Не указано')
        net = employee_data.get('На руки', 'Не указано')
        fio = employee_data.get('ФИО', 'Не указано')
        
        if isinstance(salary, int):
            salary = salary / 100
        if isinstance(taxes, int):
            taxes = taxes / 100
        if isinstance(net, int):
            net = net / 100

        response_message = (
            f"ФИО: {fio}\n"
            f"Зарплата за {selected_month}: {salary}\n"
            f"Налоги и удержания: {taxes}\n"
            f"На руки: {net}\n"
        )
        await callback_query.message.answer(response_message)
    else:
        await callback_query.message.answer("Ошибка: Не удалось найти данные о пользователе.")

    await state.clear()

@router.callback_query(StateFilter(SalaryStates.waiting_for_period_start), lambda c: c.data.startswith("month_"))
async def period_start_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]
    
    user_data = await state.get_data()
    file_id = user_data['file_id']  # Получаем выбранный файл (год)

    # Изменяем сообщение, убираем кнопки
    await callback_query.message.edit_text(f"Начало периода выбрано: **{selected_month}**", parse_mode="Markdown")

    await state.update_data(period_start=selected_month)
    sheet = get_google_sheet(file_id)
    month_sheets = get_month_sheets(sheet)

   # Переход к выбору конца периода
    await callback_query.message.answer("Выберите конец периода:", reply_markup=create_month_buttons(month_sheets))
    await state.set_state(SalaryStates.waiting_for_period_end)

@router.callback_query(StateFilter(SalaryStates.waiting_for_period_end), lambda c: c.data.startswith("month_"))
async def period_end_handler(callback_query: types.CallbackQuery, state: FSMContext):
    selected_month = callback_query.data.split("_")[1]
    user_data = await state.get_data()
    period_start = user_data['period_start']
    employee_id = user_data['employee_id']

    # Изменяем сообщение, убираем кнопки
    await callback_query.message.edit_reply_markup(reply_markup=None)

    # Отправляем отдельное сообщение о выборе конца периода
    await callback_query.message.answer(f"Конец периода выбрано: **{selected_month}**", parse_mode="Markdown")

    # Добавляем задержку в 2 секунды (можно изменить значение)
    await asyncio.sleep(0.5)

    # Отправляем сообщение с выбранным диапазоном, выделяя месяцы жирным
    await callback_query.message.answer(f"Вы выбрали просмотр зарплаты с месяца **{period_start}** по месяц **{selected_month}**.", parse_mode="Markdown")

    # Добавляем еще одну задержку перед суммированием (по желанию)
    await asyncio.sleep(0.5)

    # Суммируем зарплату за период
    await sum_salary_period(callback_query.message, period_start, selected_month, employee_id, state)
    await state.clear()

async def sum_salary_period(message: types.Message, period_start: str, period_end: str, employee_id: str, state: FSMContext):
    user_data = await state.get_data()
    file_id = user_data['file_id']  # Получаем выбранный файл (год)
    
    sheet = get_google_sheet(file_id)
    month_sheets = get_month_sheets(sheet)
    start_index = month_sheets.index(period_start)
    end_index = month_sheets.index(period_end) + 1
    selected_months = month_sheets[start_index:end_index]

    total_salary = 0
    total_taxes = 0
    total_net = 0

    for month in selected_months:
        employee_data = get_employee_data(sheet.worksheet(month), employee_id)
        if employee_data:
            # Используем .get() для безопасного доступа к данным
            salary = employee_data.get('Зарплата', 'Не указано')
            taxes = employee_data.get('Налоги и удержания', 'Не указано')
            net = employee_data.get('На руки', 'Не указано')
            
            # Проверка на целое число
            if isinstance(salary, int):
                salary = salary / 100
            if isinstance(taxes, int):
                taxes = taxes / 100
            if isinstance(net, int):
                net = net / 100
                
            # Проверка и преобразование строк в float
            if isinstance(salary, str):
                salary = salary.replace('\xa0', '').replace(' ', '').replace(',', '.')
            if isinstance(taxes, str):
                taxes = taxes.replace('\xa0', '').replace(' ', '').replace(',', '.')
            if isinstance(net, str):
                net = net.replace('\xa0', '').replace(' ', '').replace(',', '.')

            total_salary += float(salary)
            total_taxes += float(taxes)
            total_net += float(net)

    # Форматируем суммы с разделением тысяч
    formatted_salary = f"{total_salary:,.2f}".replace(',', "'")
    formatted_taxes = f"{total_taxes:,.2f}".replace(',', "'")
    formatted_net = f"{total_net:,.2f}".replace(',', "'")

    await message.reply(f"Зарплата за период с {period_start} по {period_end}:\n"
                        f"Зарплата: {formatted_salary}\n"
                        f"Налоги и удержания: {formatted_taxes}\n"
                        f"На руки: {formatted_net}")

# === Логика для суммирования зарплаты с начала года ===
async def sum_salary(message: types.Message, month_sheets, employee_id, state: FSMContext):
    total_salary = 0
    total_taxes = 0
    total_net = 0
    
    user_data = await state.get_data()
    file_id = user_data['file_id']  # Получаем выбранный файл (год)
    
    sheet = get_google_sheet(file_id)  # Получаем объект Google Sheet

    for month in month_sheets:
        employee_data = get_employee_data(sheet.worksheet(month), employee_id)
        if employee_data:
            # Используем .get() для безопасного доступа к данным
            salary = employee_data.get('Зарплата', 'Не указано')
            taxes = employee_data.get('Налоги и удержания', 'Не указано')
            net = employee_data.get('На руки', 'Не указано')
            
            if isinstance(salary, int):
                salary = salary / 100
            if isinstance(taxes, int):
                taxes = taxes / 100
            if isinstance(net, int):
                net = net / 100
                
            # Проверка и преобразование строк в float
            if isinstance(salary, str):
                salary = salary.replace('\xa0', '').replace(' ', '').replace(',', '.')
            if isinstance(taxes, str):
                taxes = taxes.replace('\xa0', '').replace(' ', '').replace(',', '.')
            if isinstance(net, str):
                net = net.replace('\xa0', '').replace(' ', '').replace(',', '.')
            
            # Преобразуем строки в float и складываем
            total_salary += float(salary)
            total_taxes += float(taxes)
            total_net += float(net)

    # Форматируем суммы с разделением тысяч
    formatted_salary = f"{total_salary:,.2f}".replace(',', "'")
    formatted_taxes = f"{total_taxes:,.2f}".replace(',', "'")
    formatted_net = f"{total_net:,.2f}".replace(',', "'")

    await message.reply(f"Зарплата с начала года: {formatted_salary}\n"
                        f"Налоги и удержания: {formatted_taxes}\n"
                        f"На руки: {formatted_net}")

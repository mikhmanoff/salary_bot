from aiogram import Router, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from services.google_services import get_google_sheet, get_google_services
from services.sheet_operations import check_auth, list_files_exclude_auth
from utils.keyboards import create_salary_type_buttons
from config.settings import GOOGLE_SHEET_ID, FOLDER_ID

router = Router()

class AuthStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_passport_digits = State()
    waiting_for_salary_type = State()

@router.message(lambda message: message.text == "Авторизоваться")
async def start_authorization(message: types.Message, state: FSMContext):
    await message.reply("Введите ваш номер табеля:")
    await state.set_state(AuthStates.waiting_for_employee_id)

@router.message(AuthStates.waiting_for_employee_id)
async def employee_id_handler(message: types.Message, state: FSMContext):
    employee_id = message.text
    await state.update_data(employee_id=employee_id)
    
    await message.reply("Введите последние 4 цифры вашего паспорта:")
    await state.set_state(AuthStates.waiting_for_passport_digits)

@router.message(AuthStates.waiting_for_passport_digits)
async def passport_digits_handler(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    employee_id = user_data['employee_id']
    passport_digits = message.text

    sheet = get_google_sheet(GOOGLE_SHEET_ID).worksheet('Авторизация')
    if check_auth(sheet, employee_id, passport_digits):
        drive_service, _, _ = get_google_services()
        files = list_files_exclude_auth(drive_service, FOLDER_ID, GOOGLE_SHEET_ID)

        if files:
            keyboard_buttons = []
            for file in files:
                button = types.InlineKeyboardButton(text=file['name'], callback_data=f"file_{file['id']}")
                keyboard_buttons.append([button])
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.reply("Выберите файл (год) для просмотра данных:", reply_markup=keyboard)
            await state.set_state(AuthStates.waiting_for_salary_type)
        else:
            await message.reply("Файлы в папке не найдены.")
    else:
        await message.reply("Неверные данные, попробуйте снова.")
        await state.clear()

@router.callback_query(StateFilter(AuthStates.waiting_for_salary_type), lambda c: c.data.startswith("file_"))
async def file_selection_handler(callback_query: types.CallbackQuery, state: FSMContext):
    file_id = callback_query.data.split("_")[1]
    await state.update_data(file_id=file_id)

    await callback_query.message.edit_text("Файл выбран. Выберите тип данных:", reply_markup=create_salary_type_buttons())
    await state.set_state(AuthStates.waiting_for_salary_type)
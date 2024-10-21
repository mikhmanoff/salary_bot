from aiogram import Router, types
from aiogram.filters import Command
from utils.keyboards import create_main_menu

router = Router()

@router.message(Command("start"))
async def start(message: types.Message):
    await message.reply("Добро пожаловать! Выберите одну из опций:", reply_markup=create_main_menu())

@router.message(lambda message: message.text == "FAQ")
async def faq(message: types.Message):
    await message.reply("Этот бот позволяет вам получить информацию о зарплате. Для начала нажмите 'Авторизоваться' и введите ваш номер табеля и последние 4 цифры паспорта.")
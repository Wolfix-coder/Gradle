from aiogram import Router, types
from aiogram import F
from aiogram.filters import Command

from config import Config
from text import help_text, about_text, price_text

basic_router = Router()

@basic_router.message(F.text.lower().contains("допомога"))
async def text_help(message: types.Message):
    await message.answer(help_text, reply_markup=types.ReplyKeyboardRemove())

@basic_router.message(Command("help"))
async def help_handler(message: types.Message):
    await message.answer(help_text, reply_markup=types.ReplyKeyboardRemove())

@basic_router.message(Command("about"))
async def cmd_about(message: types.Message):
    await message.answer(about_text, reply_markup=types.ReplyKeyboardRemove())

@basic_router.message(Command("price"))
async def cmd_price(message: types.Message):
    await message.answer(price_text, reply_markup=types.ReplyKeyboardRemove())

@basic_router.message(Command("support"))
async def cmd_support(message: types.Message):
    await message.answer(f"Натисніть для переходу до підтримки: {Config.support_url}", 
                         reply_markup=types.ReplyKeyboardRemove())

@basic_router.message(Command("report"))
async def cmd_report(message: types.Message):
    await message.answer(f"Натисніть для переходу до підтримки: {Config.support_url}", 
                         reply_markup=types.ReplyKeyboardRemove())
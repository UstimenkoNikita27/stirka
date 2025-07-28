from aiogram import Bot, Dispatcher, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import CommandStart, Command
import asyncio
from datetime import datetime, timedelta

WASHING_DURATION = 50 # Длительность стирки в минутах
CHECK_INTERVAL = 10 # Проверка каждых x секунд
MACHINES_COUNT = 5 # Количество стиралок
washing_machines = {num: {"status": "free", "until": None, "user_id": None, "broken": False} for num in range(1, MACHINES_COUNT+1)}
ADMIN_IDS = [5983331777, 2087466437] # ТГ айди админов (пока только моё)

bot = Bot(token='7759293791:AAFz1qN7c-ayhGF0aSvHOeUbwf7KGC8lSZI')
dp = Dispatcher()

markup_admin = InlineKeyboardMarkup(inline_keyboard=[
	[InlineKeyboardButton(
		text=f"Машинка {num} - {'🚫' if data['broken'] else '✅'}",
		callback_data=f'toggle_broken_{num}'
	)] for num, data in washing_machines.items()
])

async def check_and_free_machines():
	while True:
		await asyncio.sleep(CHECK_INTERVAL)
		current_time = datetime.now()
		for num, data in washing_machines.items():
			if data["status"] == "busy" and data["until"] <= current_time and not data["broken"]:
				user_id = data["user_id"]
				washing_machines[num] = {"status": "free", "until": None, "user_id": None, "broken": data["broken"]}
				if user_id:
					try:
						await bot.send_message(
							user_id,
							f"🔔 Машинка №{num} освободилась!\n"
							"Можете забрать бельё."
						)
					except Exception as e:
						print(f"Не удалось отправить уведомление пользователю {user_id}: {e}")


def markup_admin():
	return InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(
			text=f"Машинка {num} - {'🚫' if data['broken'] else '✅'}",
			callback_data=f'toggle_broken_{num}'
		)] for num, data in washing_machines.items()
	])


@dp.message(Command('admin'))
async def admin_panel(message: Message):
	"""Панель администратора"""
	if message.from_user.id not in ADMIN_IDS:
		await message.answer("Доступ запрещён")
		return
	markup = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(
			text=f"Машинка {num} - {'🚫' if data['broken'] else '✅'}",
			callback_data=f'toggle_broken_{num}'
		)] for num, data in washing_machines.items()
	])
	await message.answer("⚙ Админ-панель (статус машинок):",reply_markup=markup)

	
@dp.callback_query(F.data.startswith('toggle_broken_'))
async def toggle_broken(callback: CallbackQuery):
	"""Переключение статуса поломки"""
	machine_num = int(callback.data.split('_')[2])
	washing_machines[machine_num]["broken"] = not washing_machines[machine_num]["broken"]
	status = "🚫 Неисправна" if washing_machines[machine_num]["broken"] else "✅ Исправна"
	markup = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(
			text=f"Машинка {num} - {'🚫' if data['broken'] else '✅'}",
			callback_data=f'toggle_broken_{num}'
		)] for num, data in washing_machines.items()
	])
	await callback.message.edit_text("⚙ Админ-панель (статус машинок):",reply_markup=markup)
	await callback.answer(f"Машинка {machine_num}: {status}", show_alert=True)


@dp.message(CommandStart())
async def start(message: Message):
	markup = ReplyKeyboardMarkup(keyboard=[
		[KeyboardButton(text='Посмотреть занятость')],
		[KeyboardButton(text='Стираю')]],
		resize_keyboard=True,
		input_field_placeholder='Выберите услугу...')
	await message.answer('''🏆 Стиральный Бот
	
🚀 Всё просто:

📊 "Занятость" → Свободные/занятые машинки

🧺 "Я стираю!" → Закрепляешь за собой → Получаешь таймер

🔔 Авто-оповещение когда освободится

💡 Выгоды:
• Никаких споров за очередь
• Чёткий таймер вместо догадок
• Видно все машинки в одном месте

👉 Выбирай действие в меню ↓''', reply_markup=markup)
	
	
@dp.message(F.text == 'Посмотреть занятость')
async def view_employment(message: Message):
	current_time = datetime.now()
	text = ""
	for num, data in washing_machines.items():
		if data["broken"]:
			text += f"🔴 {num} - сломана\n"
		elif data["status"] == "free":
			text += f"🟢 {num} - свободна\n"
		else:
			time_left = data["until"] - current_time
			minutes = max(0, int(time_left.total_seconds() // 60)+1)
			text += f"🔴 {num} - занята (осталось {minutes} мин)\n"
	await message.answer(text)
	
	
@dp.message(F.text == 'Стираю')
async def wash(message: Message):
	markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=str(i), callback_data=f'wash_{i}') for i in range(1, MACHINES_COUNT+1)]])
	await message.answer(f"Выберите стиралку (стирка занимает {WASHING_DURATION} минут):", reply_markup=markup)


@dp.callback_query(F.data.startswith('wash_'))
async def washing_machine(callback: CallbackQuery):
	washing_machine_number = int(callback.data.split('_')[1])
	if washing_machines[washing_machine_number]["status"] == "busy":
		await callback.answer("❌ Эта машинка уже занята!", show_alert=True)
		return
	if washing_machines[washing_machine_number]["broken"]:
		await callback.answer("❌ Эта машинка поломана!", show_alert=True)
		return
	end_time = datetime.now() + timedelta(minutes=WASHING_DURATION)
	washing_machines[washing_machine_number] = {"status": "busy", "until": end_time, "user_id": callback.from_user.id, "broken": washing_machines[washing_machine_number]["broken"]}
	await callback.message.edit_text(
		f"✅ Вы заняли машинку №{washing_machine_number}\n"
		f"⏳ Время окончания: {end_time.strftime('%H:%M')}\n"
	)
	
	
async def main():
	await bot.delete_webhook(drop_pending_updates=True)
	asyncio.create_task(check_and_free_machines())
	await dp.start_polling(bot)

if __name__ == "__main__":
	asyncio.run(main())
	
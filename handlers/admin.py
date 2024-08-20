from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from create_bot import job_stores
from database.db_manage import get_user, update_user_sql
from handlers.client_handlers import ADMINS
from keyboards.kb import payment_on_btn, payment_of_btn, black_list_btn, back_to_admin


class FSMAdmin(StatesGroup):
    user_id = State()


async def admin(message, state):
    await state.clear()
    if message.from_user.id in ADMINS:
        redis_obj = job_stores.get('default')
        result = redis_obj.redis.get('payment')
        if (result and result.decode('utf-8') == 'off') or not result:
            payment_btn = payment_on_btn
            text = '🔴 Функція деактивована'
        elif result and result.decode('utf-8') == 'on':
            payment_btn = payment_of_btn
            text = '🟢 Функція активна'
        kb = InlineKeyboardMarkup(inline_keyboard=[[payment_btn, black_list_btn]])
        if isinstance(message, types.Message):
            await message.answer(text=f'{text}\n\n👇 Оберіть варіант:', reply_markup=kb)
        else:
            try:
                await message.message.edit_text(text=f'{text}\n\n👇 Оберіть варіант:', reply_markup=kb)
            except:
                pass


async def deny_user_access(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(FSMAdmin.user_id)
    await call.message.edit_text(text='👋🏻 Вітаю!\n'
                                      'Надішліть <b>id</b> користувача для надання або скасування прав:',
                                 parse_mode='html',
                                 reply_markup=InlineKeyboardMarkup().add(back_to_admin))


async def user_access(message: types.Message, state: FSMContext):
    user_id = message.text
    try:
        user = await get_user(user_id)
        kb = InlineKeyboardMarkup(inline_keyboard=[])
        if user.is_blocked:
            kb.inline_keyboard.extend([[InlineKeyboardButton(text='🔑 Розблокувати', callback_data=f'access_{user_id}_unblock')]])
            await message.answer(text='🚫 Користувач заблокований.', reply_markup=kb)
        else:
            kb.inline_keyboard.extend([[InlineKeyboardButton(text='🚫 Заблокувати', callback_data=f'access_{user_id}_block')]])
            await message.answer(text='✅ Користувач розблокований.', reply_markup=kb)
    except:
        await message.answer(text='❌ Користувача з таким id не існує.\n'
                                  'Спробуйте ще раз:')


async def set_access(call: types.CallbackQuery, state: FSMContext):
    data = call.data.split('_')
    user_id = data[1]
    action = data[2]
    if action == 'block':
        text = (f'✅ Користувача з id: {user_id} заблоковано.\n'
                f'Надішліть <b>id</b> користувача для надання або скасування прав:')
        await update_user_sql(user_id, is_blocked=1)

    else:
        text = (f'✅ Користувача з id: {user_id} розблоковано.\n'
                f'Надішліть <b>id</b> користувача для надання або скасування прав:')
        await update_user_sql(user_id, is_blocked=0)
    await call.message.edit_text(text=text, parse_mode='html')
    await state.set_state(FSMAdmin.user_id)


async def payment_tumbler(call: types.CallbackQuery, state: FSMContext):
    redis_obj = job_stores.get('default')
    if call.data == 'off_payment':
        redis_obj.redis.set(name='payment', value='off')
    else:
        redis_obj.redis.set(name='payment', value='on')
    await admin(call, state)
    return


def register_admin_handlers(r: Router):
    r.message.register(admin, Command('admin'))
    r.callback_query.register(admin, F.data == 'admin')
    r.message.register(user_access, FSMAdmin.user_id)
    r.callback_query.register(set_access, F.data == 'access')
    r.callback_query.register(deny_user_access, F.data == 'deny_user_access')
    r.callback_query.register(payment_tumbler, F.data.endswith('_payment'))

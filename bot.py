"""
Telegram-бот для подбора музыкальных потоков.

Запуск:
1. Получите токен у @BotFather в Telegram
2. Скопируйте .env.example -> .env, впишите BOT_TOKEN
3. pip install -r requirements.txt
4. python bot.py
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

from data import (
    BIZ,
    BIZ_MAP,
    STREAMS,
    TEMPO,
    TEMPO_LABEL_FULL,
    VOCAL,
    VOCAL_LABEL_FULL,
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN не задан. Создайте .env по образцу .env.example")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())


# --- FSM ---
class Wizard(StatesGroup):
    biz = State()
    tempo = State()
    vocal = State()


# --- Keyboards ---
def kb_biz() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for b in BIZ:
        kb.button(text=b["l"], callback_data=f"biz:{b['id']}")
    kb.adjust(2)  # 2 в ряд — названия длинноваты
    return kb.as_markup()


def kb_tempo() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in TEMPO:
        kb.button(text=t["l"], callback_data=f"tempo:{t['id']}")
    kb.button(text="◀️ Назад", callback_data="back:biz")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def kb_vocal() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for v in VOCAL:
        kb.button(text=v["l"], callback_data=f"vocal:{v['id']}")
    kb.button(text="◀️ Назад", callback_data="back:tempo")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def kb_restart() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Подобрать ещё", callback_data="restart")
    return kb.as_markup()


# --- Matching ---
def score_stream(stream: dict, biz: str | None, tempo: str | None, vocal: str | None):
    """Возвращает (score, hits). Возвращает 0 если поток не подходит по бизнесу."""
    sc = 0
    hits = {"biz": False, "tempo": False, "vocal": False}

    if biz and biz != "any":
        if biz in stream["b"]:
            sc += 4
            hits["biz"] = True
        elif "universal" in stream["b"]:
            sc += 1  # универсальный поток как fallback
        else:
            return 0, hits  # жёсткий фильтр

    if tempo and tempo != "any":
        if stream["t"] == tempo:
            sc += 2
            hits["tempo"] = True
        elif stream["t"] == "mixed":
            sc += 1
            hits["tempo"] = True
        else:
            sc -= 1

    if vocal and vocal != "any":
        if stream["v"] == vocal:
            sc += 2
            hits["vocal"] = True
        elif stream["v"] == "mixed":
            sc += 1
            hits["vocal"] = True
        else:
            sc -= 1

    return sc, hits


def format_results(biz: str | None, tempo: str | None, vocal: str | None) -> str:
    scored = []
    for s in STREAMS:
        sc, hits = score_stream(s, biz, tempo, vocal)
        if sc > 0:
            scored.append((sc, s, hits))
    scored.sort(key=lambda x: -x[0])
    top = scored[:10]

    biz_label = BIZ_MAP.get(biz, "—") if biz else "—"
    tempo_label = TEMPO_LABEL_FULL.get(tempo, "—") if tempo else "—"
    vocal_label = VOCAL_LABEL_FULL.get(vocal, "—") if vocal else "—"

    lines = [
        "<b>📋 Ваши параметры</b>",
        f"  • Бизнес: {biz_label}",
        f"  • Темп: {tempo_label}",
        f"  • Вокал: {vocal_label}",
        "",
    ]

    if not top:
        lines.append(
            "😔 Под эти параметры ничего точного не нашлось.\n"
            "Попробуйте смягчить критерии — например, темп или вокал переключить на «Любой»."
        )
        return "\n".join(lines)

    suffix = f" (показываю топ 10)" if len(scored) > 10 else ""
    lines.append(f"<b>🎯 Найдено: {len(scored)}</b>{suffix}")
    lines.append("")

    for idx, (sc, s, hits) in enumerate(top, 1):
        lines.append(f"<b>{idx}. {s['n']}</b>  <code>#{s['id']}</code>")
        lines.append(f"   <i>{s['d']}</i>")
        tags = []
        if hits["biz"]:
            tags.append("✓ бизнес")
        if hits["tempo"]:
            tags.append("✓ темп")
        if hits["vocal"]:
            tags.append("✓ вокал")
        if tags:
            lines.append(f"   {' · '.join(tags)}")
        lines.append("")

    return "\n".join(lines)


# --- Handlers ---
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Wizard.biz)
    await message.answer(
        "👋 Привет! Я помогу подобрать музыкальную волну под ваш бизнес.\n\n"
        "Ответьте на 3 вопроса и получите список подходящих потоков.\n\n"
        "<b>Шаг 1 из 3.</b> Какой у вас бизнес?",
        reply_markup=kb_biz(),
    )


@dp.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    await cmd_start(message, state)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🎵 <b>Подборщик музыкальных потоков</b>\n\n"
        "Я задам 3 вопроса — про тип бизнеса, темп и наличие вокала — "
        "и порекомендую подходящие потоки из каталога.\n\n"
        "<b>Команды:</b>\n"
        "/start — начать подбор\n"
        "/reset — начать заново\n"
        "/help — эта справка"
    )


@dp.callback_query(F.data.startswith("biz:"))
async def on_biz(cb: CallbackQuery, state: FSMContext):
    biz_id = cb.data.split(":", 1)[1]
    await state.update_data(biz=biz_id)
    await state.set_state(Wizard.tempo)
    biz_label = BIZ_MAP.get(biz_id, biz_id)
    await cb.message.edit_text(
        f"✓ Бизнес: <b>{biz_label}</b>\n\n"
        "<b>Шаг 2 из 3.</b> Какой темп музыки нужен?",
        reply_markup=kb_tempo(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("tempo:"))
async def on_tempo(cb: CallbackQuery, state: FSMContext):
    tempo_id = cb.data.split(":", 1)[1]
    await state.update_data(tempo=tempo_id)
    await state.set_state(Wizard.vocal)
    data = await state.get_data()
    biz_label = BIZ_MAP.get(data.get("biz"), "—")
    tempo_label = TEMPO_LABEL_FULL.get(tempo_id, tempo_id)
    await cb.message.edit_text(
        f"✓ Бизнес: <b>{biz_label}</b>\n"
        f"✓ Темп: <b>{tempo_label}</b>\n\n"
        "<b>Шаг 3 из 3.</b> Нужен вокал или инструментал?",
        reply_markup=kb_vocal(),
    )
    await cb.answer()


@dp.callback_query(F.data.startswith("vocal:"))
async def on_vocal(cb: CallbackQuery, state: FSMContext):
    vocal_id = cb.data.split(":", 1)[1]
    await state.update_data(vocal=vocal_id)
    data = await state.get_data()
    text = format_results(data.get("biz"), data.get("tempo"), vocal_id)
    await cb.message.edit_text(text, reply_markup=kb_restart())
    await state.clear()
    await cb.answer()


@dp.callback_query(F.data == "back:biz")
async def on_back_to_biz(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Wizard.biz)
    await cb.message.edit_text(
        "<b>Шаг 1 из 3.</b> Какой у вас бизнес?",
        reply_markup=kb_biz(),
    )
    await cb.answer()


@dp.callback_query(F.data == "back:tempo")
async def on_back_to_tempo(cb: CallbackQuery, state: FSMContext):
    await state.set_state(Wizard.tempo)
    data = await state.get_data()
    biz_label = BIZ_MAP.get(data.get("biz"), "—")
    await cb.message.edit_text(
        f"✓ Бизнес: <b>{biz_label}</b>\n\n"
        "<b>Шаг 2 из 3.</b> Какой темп музыки нужен?",
        reply_markup=kb_tempo(),
    )
    await cb.answer()


@dp.callback_query(F.data == "restart")
async def on_restart(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Wizard.biz)
    await cb.message.edit_text(
        "👋 Давайте подберём ещё.\n\n<b>Шаг 1 из 3.</b> Какой у вас бизнес?",
        reply_markup=kb_biz(),
    )
    await cb.answer()


# --- Main ---
async def main():
    log.info("Бот запущен, потоков в базе: %d", len(STREAMS))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

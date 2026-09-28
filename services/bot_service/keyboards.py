from typing import List
from maxbot.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия по 152-ФЗ с поддержкой гостевого режима."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принять (Полный профиль)",
                    callback_data="consent_accept",
                    type="callback"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Отказаться (Гостевой режим)",
                    callback_data="consent_decline",
                    type="callback"
                )
            ]
        ]
    )


def get_interests_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора сферы интересов для построения аналогий."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚽ Футбол", callback_data="interest_Футбол", type="callback"),
                InlineKeyboardButton(text="🎮 Видеоигры", callback_data="interest_Видеоигры", type="callback"),
            ],
            [
                InlineKeyboardButton(text="🎵 Музыка", callback_data="interest_Музыка", type="callback"),
                InlineKeyboardButton(text="🚀 Космос", callback_data="interest_Космос", type="callback"),
            ],
            [
                InlineKeyboardButton(text="🎬 Кино", callback_data="interest_Кино", type="callback"),
                InlineKeyboardButton(text="🌐 Общий", callback_data="interest_Общий", type="callback"),
            ]
        ]
    )


def get_quiz_keyboard(quiz_id: str, options: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура с вариантами ответа на проверочный тест."""
    buttons = []
    # Каждая опция на отдельной строке
    for idx, opt_text in enumerate(options):
        # Ограничиваем длину текста кнопки для красивого рендеринга
        short_text = opt_text if len(opt_text) <= 45 else (opt_text[:42] + "...")
        buttons.append([
            InlineKeyboardButton(
                text=f"{idx + 1}. {short_text}",
                callback_data=f"quiz_{quiz_id}_{idx}",
                type="callback"
            )
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_after_explanation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура после прочтения объяснения."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Пройти проверочный тест", callback_data="action_quiz", type="callback"),
                InlineKeyboardButton(text="👤 Мой профиль", callback_data="action_profile", type="callback")
            ]
        ]
    )

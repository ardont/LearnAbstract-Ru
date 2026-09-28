from typing import List, Optional
from maxbot.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура согласия по 152-ФЗ с поддержкой гостевого режима и описанием проекта."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Согласен (Полный профиль)",
                    callback_data="consent_accept",
                    type="callback"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔒 Гостевой режим (Без сохранения)",
                    callback_data="consent_decline",
                    type="callback"
                )
            ],
            [
                InlineKeyboardButton(
                    text="ℹ️ О проекте",
                    callback_data="about_project",
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
                InlineKeyboardButton(text="🌐 Кругозор", callback_data="interest_Общий", type="callback"),
            ]
        ]
    )


def get_quiz_keyboard(quiz_id: str, options: List[str]) -> InlineKeyboardMarkup:
    """Клавиатура с вариантами ответа на проверочный тест."""
    buttons = []
    for idx, opt_text in enumerate(options):
        short_text = opt_text if len(opt_text) <= 45 else (opt_text[:42] + "...")
        buttons.append([
            InlineKeyboardButton(
                text=f"{idx + 1}. {short_text}",
                callback_data=f"quiz_{quiz_id}_{idx}",
                type="callback"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_after_explanation_keyboard(topic: str = "", quiz_id: str = "") -> InlineKeyboardMarkup:
    """Клавиатура действий после прочтения объяснения: тест, другая метафора, прогресс."""
    buttons = []
    top_row = []
    if quiz_id:
        top_row.append(
            InlineKeyboardButton(text="🎯 Пройти тест", callback_data=f"action_quiz_{quiz_id}", type="callback")
        )
    topic_cb = topic[:30] if topic else "last"
    top_row.append(
        InlineKeyboardButton(text="🔄 Другая метафора", callback_data=f"remetaphor_{topic_cb}", type="callback")
    )
    buttons.append(top_row)
    buttons.append([
        InlineKeyboardButton(text="📊 Мой прогресс", callback_data="action_profile", type="callback")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления профилем."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⚽ Сменить хобби", callback_data="cmd_hobby", type="callback"),
                InlineKeyboardButton(text="🔄 Сбросить профиль", callback_data="cmd_reset", type="callback")
            ]
        ]
    )


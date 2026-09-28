import pytest
import os
import sys

# Подключаем корень репозитория
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from shared.utils.text_formatter import latex_to_unicode, split_for_max


def test_latex_to_unicode_powers():
    # Степени и индексы
    text = "$x^2 + y^2 = r^2$"
    res = latex_to_unicode(text)
    assert "x²" in res
    assert "y²" in res
    assert "r²" in res
    assert "$" not in res


def test_latex_to_unicode_fractions():
    # Дроби
    text = r"$I = \frac{U}{R}$"
    res = latex_to_unicode(text)
    assert "(U / R)" in res
    assert r"\frac" not in res


def test_latex_to_unicode_symbols_and_roots():
    # Корни и спецсимволы
    text = r"c = \sqrt{a^2 + b^2}, \alpha + \beta = 90^\circ"
    res = latex_to_unicode(text)
    assert "√" in res
    assert "α" in res
    assert "β" in res


def test_split_for_max_short():
    # Короткое сообщение не разбивается
    short_text = "Короткое сообщение по теме закона Ома."
    chunks = split_for_max(short_text, limit=4000)
    assert len(chunks) == 1
    assert chunks[0] == short_text


def test_split_for_max_long():
    # Длинный текст аккуратно делится по абзацам без разрыва слов
    p1 = "Абзац 1: " + ("Очень важное объяснение. " * 80)
    p2 = "Абзац 2: " + ("Продолжение мысли по физике. " * 80)
    full_text = f"{p1}\n\n{p2}"

    chunks = split_for_max(full_text, limit=1000)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 1000
    # Общая смысловая целостность
    combined = " ".join(chunks)
    assert "Абзац 1" in combined
    assert "Абзац 2" in combined

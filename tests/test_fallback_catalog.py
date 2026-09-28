import pytest
from services.ml_service.fallback_catalog import FALLBACK_CATALOG, get_catalog_metaphor

REQUIRED_TOPICS = [
    "квадратные уравнения", "теорема пифагора", "производная", "логарифмы", "тригонометрия", "вероятность",
    "закон ома", "сила тяжести", "ускорение", "кинетическая энергия", "закон сохранения импульса",
    "алгоритмы", "сортировка", "бинарный поиск", "рекурсия", "сложность o(n)",
    "фотосинтез", "клетка", "днк", "эволюция"
]

REQUIRED_HOBBIES = ["Футбол", "Баскетбол", "Видеоигры", "Музыка", "Космос"]


def test_catalog_dimensions():
    """Каталог должен содержать минимум 20 тем и 5 хобби (ровно 100 готовых метафор)."""
    assert len(FALLBACK_CATALOG) >= 20, f"Ожидалось >= 20 тем, получено {len(FALLBACK_CATALOG)}"
    
    total_pairs = 0
    for topic in REQUIRED_TOPICS:
        assert topic in FALLBACK_CATALOG, f"Тема «{topic}» отсутствует в FALLBACK_CATALOG"
        hobbies_dict = FALLBACK_CATALOG[topic]
        for hobby in REQUIRED_HOBBIES:
            assert hobby in hobbies_dict, f"Хобби «{hobby}» отсутствует для темы «{topic}»"
            total_pairs += 1

    assert total_pairs == 100, f"Ожидалось ровно 100 пар тем и хобби, получено {total_pairs}"


@pytest.mark.parametrize("topic", REQUIRED_TOPICS)
@pytest.mark.parametrize("hobby", REQUIRED_HOBBIES)
def test_all_100_metaphors_structure(topic, hobby):
    """Каждая из 100 метафор обязана содержать Шаг 1, Шаг 2 (формулу), Шаг 3 и валидный квиз."""
    entry = FALLBACK_CATALOG[topic][hobby]
    text = entry["text"]
    
    # 1. Проверка структуры шагов
    assert "Шаг 1" in text, f"В теме «{topic}» ({hobby}) отсутствует Шаг 1"
    assert "Шаг 2" in text, f"В теме «{topic}» ({hobby}) отсутствует Шаг 2 (формула)"
    assert "Шаг 3" in text, f"В теме «{topic}» ({hobby}) отсутствует Шаг 3"
    assert len(text) > 100, f"Слишком короткий текст метафоры для «{topic}» ({hobby})"

    # 2. Проверка квиза
    quiz = entry["quiz"]
    assert "question" in quiz and len(quiz["question"]) > 10
    assert "options" in quiz and len(quiz["options"]) == 4
    assert 0 <= quiz["correct_option_index"] <= 3
    assert "explanation" in quiz and len(quiz["explanation"]) > 5


def test_get_catalog_metaphor_helper():
    """Хелпер get_catalog_metaphor должен возвращать данные по подстрокам."""
    res = get_catalog_metaphor("Объясни мне квадратные уравнения пожалуйста", "Футбол")
    assert res is not None
    assert "парабол" in res["text"].lower() or "d = b² - 4ac" in res["text"]
    assert res["source"] == "fallback_catalog"

    res_basket = get_catalog_metaphor("закон ома в физике", "Баскетбол")
    assert res_basket is not None
    assert "I = U / R" in res_basket["text"]

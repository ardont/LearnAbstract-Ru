import os
import sys
from pathlib import Path

# Принудительная установка UTF-8 для вывода в консоль Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def create_minimal_pdf(output_path: Path):
    """
    Генерирует валидный компактный PDF файл с академическим текстом по школьной алгебре
    для автономного тестирования RAG-пайплайна.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text_content = (
        "УЧЕБНИК ПО АЛГЕБРЕ ДЛЯ 7-8 КЛАССОВ\n"
        "ГЛАВА 1: КВАДРАТНЫЕ УРАВНЕНИЯ\n"
        "Определение: Квадратным уравнением называется уравнение вида ax^2 + bx + c = 0, "
        "где a, b, c — действительные числа, причем a не равно 0.\n"
        "ДИСКРИМИНАНТ И ЕГО СВОЙСТВА\n"
        "Выражение D = b^2 - 4ac называется дискриминантом квадратного уравнения.\n"
        "1. Если D > 0, уравнение имеет два различных действительных корня: x1,2 = (-b +- sqrt(D)) / (2a).\n"
        "2. Если D = 0, уравнение имеет один корень (два совпадающих): x = -b / (2a).\n"
        "3. Если D < 0, уравнение не имеет действительных корней.\n"
        "ТЕОРЕМА ВИЕТА\n"
        "Для приведенного квадратного уравнения x^2 + px + q = 0 сумма корней равна -p, "
        "а произведение корней равно q: x1 + x2 = -p, x1 * x2 = q.\n"
        "ГЕОМЕТРИЧЕСКИЙ СМЫСЛ И ПАРАБОЛА\n"
        "Графиком квадратичной функции y = ax^2 + bx + c является парабола. "
        "Вершина параболы имеет координаты x_0 = -b / (2a). Если a > 0, ветви параболы направлены вверх."
    )

    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        font_name = "Helvetica"
        # Проверяем шрифты с поддержкой кириллицы
        candidate_fonts = [
            ("Arial", "C:/Windows/Fonts/arial.ttf"),
            ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf")
        ]
        for name, path in candidate_fonts:
            if os.path.exists(path):
                pdfmetrics.registerFont(TTFont(name, path))
                font_name = name
                break

        c = canvas.Canvas(str(output_path), pagesize=letter)
        c.setFont(font_name, 11)
        y = 740
        for line in text_content.split("\n"):
            # Если строка слишком длинная — переносим
            while len(line) > 85:
                part = line[:85]
                split_idx = part.rfind(" ")
                if split_idx == -1:
                    split_idx = 85
                c.drawString(50, y, line[:split_idx])
                line = line[split_idx:].strip()
                y -= 16
            c.drawString(50, y, line)
            y -= 20
        c.save()
        print(f"✅ Учебник успешно создан с шрифтом {font_name}: {output_path}")
        return
    except Exception as e:
        print(f"Ошибка ReportLab: {e}")


if __name__ == "__main__":
    target = Path("tests/fixtures/sample_textbook.pdf")
    create_minimal_pdf(target)

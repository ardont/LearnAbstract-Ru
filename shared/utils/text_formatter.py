import re
from typing import List

# Таблицы подстрочных и надстрочных символов Unicode
SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'n': 'ⁿ', 'i': 'ⁱ', 'x': 'ˣ', 'y': 'ʸ'
}

SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ', 'i': 'ᵢ', 'j': 'ⱼ'
}

GREEK_SYMBOLS = {
    r'\alpha': 'α', r'\beta': 'β', r'\gamma': 'γ', r'\delta': 'δ',
    r'\Delta': 'Δ', r'\epsilon': 'ε', r'\zeta': 'ζ', r'\eta': 'η',
    r'\theta': 'θ', r'\Theta': 'Θ', r'\iota': 'ι', r'\kappa': 'κ',
    r'\lambda': 'λ', r'\Lambda': 'Λ', r'\mu': 'μ', r'\nu': 'ν',
    r'\xi': 'ξ', r'\pi': 'π', r'\Pi': 'Π', r'\rho': 'ρ',
    r'\sigma': 'σ', r'\Sigma': 'Σ', r'\tau': 'τ', r'\phi': 'φ',
    r'\Phi': 'Φ', r'\chi': 'χ', r'\psi': 'ψ', r'\omega': 'ω',
    r'\Omega': 'Ω'
}

MATH_OPERATORS = {
    r'\times': '×', r'\cdot': '·', r'\pm': '±', r'\mp': '∓',
    r'\leq': '≤', r'\le': '≤', r'\geq': '≥', r'\ge': '≥',
    r'\neq': '≠', r'\ne': '≠', r'\approx': '≈', r'\equiv': '≡',
    r'\infty': '∞', r'\to': '→', r'\rightarrow': '→',
    r'\Rightarrow': '⇒', r'\Leftarrow': '⇐', r'\sum': '∑',
    r'\prod': '∏', r'\int': '∫', r'\partial': '∂', r'\nabla': '∇',
    r'\in': '∈', r'\notin': '∉', r'\subset': '⊂', r'\cup': '∪', r'\cap': '∩'
}


def _replace_super(match: re.Match) -> str:
    content = match.group(1) or match.group(2)
    return ''.join(SUPERSCRIPTS.get(ch, ch) for ch in content)


def _replace_sub(match: re.Match) -> str:
    content = match.group(1) or match.group(2)
    return ''.join(SUBSCRIPTS.get(ch, ch) for ch in content)


def latex_to_unicode(text: str) -> str:
    """
    Преобразует математические выражения в LaTeX в читаемый Unicode для мессенджера MAX.
    Примеры:
      $x^2 + y^2 = r^2$ -> x² + y² = r²
      \\frac{a}{b} -> (a / b)
      \\sqrt{x} -> √(x)
    """
    if not text:
        return ""

    out = text

    # Замена дробей \frac{числитель}{знаменатель}
    frac_pattern = re.compile(r'\\frac\{([^{}]+)\}\{([^{}]+)\}')
    while frac_pattern.search(out):
        out = frac_pattern.sub(r'(\1 / \2)', out)

    # Замена квадратных корней \sqrt{x} и \sqrt[n]{x}
    out = re.sub(r'\\sqrt\[([^\[\]]+)\]\{([^{}]+)\}', r'(\1)√(\2)', out)
    out = re.sub(r'\\sqrt\{([^{}]+)\}', r'√(\1)', out)

    # Греческие буквы и операторы
    for tex, uni in {**GREEK_SYMBOLS, **MATH_OPERATORS}.items():
        out = re.sub(re.escape(tex) + r'(?![a-zA-Z])', uni, out)

    # Ссылки на степени x^{12} или x^2
    out = re.sub(r'\^\{([^{}]+)\}', _replace_super, out)
    out = re.sub(r'\^([0-9a-zA-Z+-])', _replace_super, out)

    # Индексы x_{12} или x_1
    out = re.sub(r'_\{([^{}]+)\}', _replace_sub, out)
    out = re.sub(r'_([0-9a-zA-Z+-])', _replace_sub, out)

    # Удаление знаков доллара $...$ и $$...$$
    out = re.sub(r'\$\$([^\$]+)\$\$', r'\1', out)
    out = re.sub(r'\$([^\$]+)\$', r'\1', out)

    # Очистка оставшихся обратных слэшей в TeX-шрифтах
    out = re.sub(r'\\text\{([^{}]+)\}', r'\1', out)
    out = re.sub(r'\\mathbf\{([^{}]+)\}', r'\1', out)

    return out.strip()


def split_for_max(text: str, limit: int = 4000) -> List[str]:
    """
    Безопасное разбиение длинного сообщения на чанки до limit символов (по умолчанию 4000 под MAX).
    Разбивает сначала по параграфам, затем по строкам или предложениям, не обрывая слова.
    """
    if not text:
        return []

    text = text.strip()
    if len(text) <= limit:
        return [text]

    chunks = []
    remaining = text

    while len(remaining) > limit:
        # Ищем идеальную точку разбиения внутри лимита
        split_point = -1

        # 1. По двойному переводу строки (абзац)
        pos = remaining.rfind("\n\n", 0, limit)
        if pos != -1 and pos > limit // 4:
            split_point = pos + 2
        else:
            # 2. По одинарному переводу строки
            pos = remaining.rfind("\n", 0, limit)
            if pos != -1 and pos > limit // 4:
                split_point = pos + 1
            else:
                # 3. По концу предложения (. или ! или ?)
                for punct in [". ", "! ", "? "]:
                    pos = remaining.rfind(punct, 0, limit)
                    if pos != -1 and pos > limit // 4:
                        split_point = max(split_point, pos + len(punct))

                # 4. По пробелу
                if split_point == -1:
                    pos = remaining.rfind(" ", 0, limit)
                    if pos != -1 and pos > limit // 4:
                        split_point = pos + 1

        # Если не нашли адекватного разделителя — режем строго по лимиту
        if split_point == -1:
            split_point = limit

        chunk = remaining[:split_point].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_point:].strip()

    if remaining:
        chunks.append(remaining)

    return chunks

from app import math_logic
def test_arithmetic(): assert math_logic.calculate("12 * 7")["answer"] == 84
def test_precedence(): assert math_logic.calculate("(2 + 3) * 4")["answer"] == 20
def test_percentage(): assert math_logic.calculate("25% of 200")["answer"] == 50
def test_linear_equation(): assert math_logic.calculate("2x + 4 = 10")["answer"] == 3
def test_non_math_is_ignored(): assert math_logic.calculate("what is Grok AI") is None
def test_logic_mode(): assert "constraints" in math_logic.logic_context("Logically deduce this puzzle")

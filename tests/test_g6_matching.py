"""Written-answer matching rules (transcription -> score)."""
from app.grading import key_parts, match_written


def test_key_parts():
    assert key_parts("3/8") == [["3/8"]]
    assert key_parts("pyramids / pyramid") == [["pyramids", "pyramid"]]
    assert key_parts("Mercury; Venus") == [["Mercury"], ["Venus"]]


def test_exact_and_fuzzy():
    assert match_written("Chlorophyl", "chlorophyll", 1, 0.95)[:2] == (1, True)
    assert match_written("glucose", "chlorophyll", 1, 0.95)[:2] == (0, False)
    assert match_written("3/8", "3/8", 1, 0.9)[:2] == (1, True)


def test_two_parts_any_order_partial_credit():
    assert match_written("Venus, Mercury", "Mercury; Venus", 2, 0.9)[:2] == (2, True)
    assert match_written("Mercury, Mars", "Mercury; Venus", 2, 0.9)[:2] == (1, False)
    assert match_written("19451939", "1939; 1945", 2, 0.9)[:2] == (2, True)


def test_blank_scores_zero():
    assert match_written("", "lava", 1, 0.0)[:2] == (0, False)

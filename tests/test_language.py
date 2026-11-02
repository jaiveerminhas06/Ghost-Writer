import json

import pytest

from api.language import english_check
from api import settings

CASES = {
    "French": "Les voitures sans conducteur sont une idée qui fait peur à beaucoup de gens, mais il faut que nous pensions à ce que cela veut dire pour les villes et pour les enfants qui vivent dans ces villes.",
    "Spanish": "Los coches sin conductor son una idea que no es nueva, pero que cada día es más real para las personas que viven en las ciudades y para los que trabajan con ellos.",
    "German": "Ich glaube, dass autonome Autos eine gute Idee sind, aber es ist nicht einfach, die Sicherheit für alle Menschen auf der Straße zu garantieren und die Kosten zu senken.",
}


def test_the_built_in_examples_are_english():
    assert all(english_check(t) is None for t in json.loads(settings.SAMPLES_JSON.read_text()).values())


@pytest.mark.parametrize("language", CASES)
def test_other_latin_script_languages_are_named(language):
    code, message = english_check(CASES[language])
    assert code == "not_english" and language in message


@pytest.mark.parametrize("text,script", [("Беспилотные автомобили — это страшная идея для многих людей, но со временем они станут обычными на дорогах.", "Cyrillic"),
                                         ("无人驾驶汽车对许多人来说是一个可怕的想法，但随着时间的推移，它们将成为世界各地城市道路上的常见景象。", "Chinese")])
def test_other_scripts_are_named(text, script):
    assert script in english_check(text)[1]


def test_text_with_no_letters_is_refused():
    assert english_check("1234 5678 !!!!")[0] == "not_english"


def test_plain_english_with_names_and_numbers_passes():
    assert english_check("In 2016 Hillary Clinton won the popular vote by almost three million votes, yet Donald Trump became president, and that is why many people want to change how the electors are chosen.") is None

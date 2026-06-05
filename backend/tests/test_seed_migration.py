"""Vazifa 21.1 — seed migratsiya tarkibi smoke testi.

`e5aebbb33974_seed_roles_competencies_recommendations.py` dagi boshlang'ich
ma'lumotlar (rollar/kompetensiyalar/tavsiyalar) kutilgan tarkibga ega ekanini
tekshiradi.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_seed_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "e5aebbb33974_seed_roles_competencies_recommendations.py"
    )
    spec = importlib.util.spec_from_file_location("seed_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_mvp_demo_seed_module():
    path = (
        Path(__file__).resolve().parents[1]
        / "migrations"
        / "versions"
        / "f2b7a91c4d3e_seed_mvp_demo_content.py"
    )
    spec = importlib.util.spec_from_file_location("mvp_demo_seed_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_seed_migration_contains_expected_roles_competencies_and_recommendations() -> None:
    """Seed ma'lumotlar MVP kutilmalariga mos bo'ladi."""
    seed = _load_seed_module()

    assert tuple(seed.SEED_ROLES) == ("Rahbar", "Ekspert", "Administrator")

    competency_names = [name for name, _ in seed.SEED_COMPETENCIES]
    assert len(competency_names) >= 6
    assert "Boshqaruv madaniyati" in competency_names
    assert "Strategik rejalashtirish" in competency_names

    general_levels = {level for level, _ in seed.SEED_GENERAL_RECOMMENDATIONS}
    assert general_levels == {"Past", "O'rta", "Yaxshi", "Yuqori"}

    assert len(seed.SEED_COMPETENCY_RECOMMENDATIONS) > 0
    referenced_competencies = {
        comp_name for comp_name, _, _ in seed.SEED_COMPETENCY_RECOMMENDATIONS
    }
    assert referenced_competencies.issubset(set(competency_names))


def test_mvp_demo_seed_contains_user_and_complete_demo_test() -> None:
    """MVP topshirish uchun demo login va faol test seed qilinadi."""
    seed = _load_mvp_demo_seed_module()

    assert seed.DEMO_PHONE == "+998901112236"
    assert seed.DEMO_PASSWORD == "secret123"
    assert seed.DEMO_TEST_TITLE

    questions = tuple(seed.DEMO_QUESTIONS)
    assert len(questions) >= 6
    assert any(item["type"] == "likert" for item in questions)
    assert any(item["answers"] for item in questions)

    orders = [item["order"] for item in questions]
    assert orders == sorted(orders)

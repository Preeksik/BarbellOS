"""Profil i plan żywieniowy: zapotrzebowanie kaloryczne i cele makroskładników.

To szacunek z ogólnych wzorów, punkt startowy, a nie pomiar. Docelowo zapotrzebowanie
będzie korygowane trendem wagi i spożyciem (`core/energy.py`, dokumentacja 6.4).

Źródła:
- przemiana materii (BMR): Mifflin i in., Am J Clin Nutr 1990 (wzór Mifflin-St Jeor),
- mnożniki aktywności: standardowe współczynniki PAL 1,2–1,9,
- 1 kg masy ciała ≈ 7700 kcal (jak w `core/energy.py`),
- białko: ISSN Position Stand 2017 (1,4–2,0 g/kg; przy deficycie u trenujących siłowo
  więcej, do 2,3–3,1 g/kg),
- tłuszcz: 20–35% energii (National Academies, AMDR); domyślnie 25%,
- tłuszcze nasycone: poniżej 10% energii, sól: poniżej 5 g (WHO, Healthy diet),
- błonnik: 14 g na 1000 kcal (Dietary Guidelines for Americans), nie mniej niż 25 g (WHO).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Sex = Literal["male", "female"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]
Goal = Literal["lose", "maintain", "gain"]

KCAL_PER_KG = 7700.0

ACTIVITY_FACTORS: dict[str, float] = {
    "sedentary": 1.2,  # praca siedząca, bez treningów
    "light": 1.375,  # 1–3 treningi w tygodniu
    "moderate": 1.55,  # 3–5 treningów w tygodniu
    "active": 1.725,  # 6–7 treningów w tygodniu
    "very_active": 1.9,  # praca fizyczna i codzienne treningi
}

# Dozwolone tempo zmiany masy ciała (kg na tydzień), osobno dla redukcji i masy.
PACES: dict[str, tuple[float, ...]] = {
    "lose": (0.25, 0.5, 0.75, 1.0),
    "maintain": (0.0,),
    "gain": (0.1, 0.25, 0.5),
}
MAX_LOSS_SHARE_PER_WEEK = 0.01  # redukcja szybsza niż 1% masy ciała na tydzień kosztuje mięśnie

# Domyślne białko (g na kg masy ciała) dla celu; użytkownik może je zmienić.
DEFAULT_PROTEIN_PER_KG: dict[str, float] = {"lose": 2.2, "maintain": 1.8, "gain": 1.8}
PROTEIN_PER_KG_RANGE = (1.2, 3.1)

FAT_SHARE = 0.25
MIN_FAT_SHARE = 0.20
SAT_FAT_MAX_SHARE = 0.10
FIBER_PER_1000_KCAL = 14.0
MIN_FIBER_G = 25.0
SALT_MAX_G = 5.0

KCAL_PER_G = {"protein": 4.0, "carbs": 4.0, "fat": 9.0}


@dataclass(frozen=True)
class Profile:
    sex: Sex
    birth_date: date
    height_cm: float
    weight_kg: float
    activity: Activity
    goal: Goal
    pace_kg_week: float
    protein_g_per_kg: float | None = None  # None = domyślne dla celu


@dataclass(frozen=True)
class Plan:
    age: int
    bmr: float  # przemiana materii w spoczynku
    tdee: float  # całkowite zapotrzebowanie przy podanej aktywności
    kcal: float  # cel kaloryczny dnia
    adjustment: float  # różnica względem TDEE: ujemna = deficyt, dodatnia = nadwyżka
    pace_kg_week: float  # tempo po ograniczeniach (może być wolniejsze niż wybrane)
    protein_g_per_kg: float
    goals: dict[str, float | None]  # cele dzienne w kluczach `daily_target`
    notes: list[str] = field(default_factory=list)  # skąd się wzięła każda liczba
    warnings: list[str] = field(default_factory=list)


def age_on(birth_date: date, day: date) -> int:
    """Wiek w pełnych latach w danym dniu."""
    before_birthday = (day.month, day.day) < (birth_date.month, birth_date.day)
    return day.year - birth_date.year - before_birthday


def profile_errors(profile: Profile, today: date) -> list[str]:
    """Błędy, z którymi profilu nie zapisujemy."""
    errors = []
    age = age_on(profile.birth_date, today)
    if not 14 <= age <= 100:
        errors.append("Wiek musi wynosić od 14 do 100 lat (sprawdź datę urodzenia).")
    if not 120 <= profile.height_cm <= 230:
        errors.append("Wzrost musi wynosić od 120 do 230 cm.")
    if not 30 <= profile.weight_kg <= 300:
        errors.append("Masa ciała musi wynosić od 30 do 300 kg.")
    if profile.pace_kg_week not in PACES[profile.goal]:
        allowed = ", ".join(_pl(p) for p in PACES[profile.goal])
        errors.append(f"Tempo dla tego celu: {allowed} kg na tydzień.")
    low, high = PROTEIN_PER_KG_RANGE
    if profile.protein_g_per_kg is not None and not low <= profile.protein_g_per_kg <= high:
        errors.append(f"Białko musi wynosić od {_pl(low)} do {_pl(high)} g na kg masy ciała.")
    return errors


def bmr_mifflin(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Przemiana materii w spoczynku (kcal/dzień), wzór Mifflin-St Jeor."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex == "male" else -161)


def _pl(value: float) -> str:
    """Liczba w opisie po polsku: przecinek dziesiętny, bez zbędnych zer."""
    return f"{value:g}".replace(".", ",")


def _round(value: float, step: float) -> float:
    return round(value / step) * step


def plan_for(profile: Profile, today: date) -> Plan:
    """Cel kaloryczny i cele dzienne z profilu. Każda liczba ma opis w `notes`."""
    age = age_on(profile.birth_date, today)
    w = profile.weight_kg
    bmr = bmr_mifflin(profile.sex, w, profile.height_cm, age)
    factor = ACTIVITY_FACTORS[profile.activity]
    tdee = bmr * factor
    notes = [
        f"Przemiana materii w spoczynku: {bmr:.0f} kcal (wzór Mifflin-St Jeor: płeć, wiek {age}, "
        f"{_pl(profile.height_cm)} cm, {_pl(w)} kg).",
        f"Zapotrzebowanie przy Twojej aktywności: {bmr:.0f} × {_pl(factor)} = {tdee:.0f} kcal.",
    ]
    warnings: list[str] = []

    pace = profile.pace_kg_week
    safe_pace = w * MAX_LOSS_SHARE_PER_WEEK
    if profile.goal == "lose" and pace > safe_pace:
        pace = max((p for p in PACES["lose"] if p <= safe_pace), default=PACES["lose"][0])
        warnings.append(
            f"Tempo {_pl(profile.pace_kg_week)} kg/tydz. to ponad 1% masy ciała. "
            f"Plan liczy {_pl(pace)} kg/tydz., żeby nie tracić mięśni."
        )
    daily = pace * KCAL_PER_KG / 7
    adjustment = {"lose": -daily, "maintain": 0.0, "gain": daily}[profile.goal]
    kcal = tdee + adjustment
    if profile.goal == "lose" and kcal < bmr:
        # Jedzenie poniżej przemiany spoczynkowej przy treningu siłowym to za mało.
        kcal = bmr
        adjustment = bmr - tdee
        pace = -adjustment * 7 / KCAL_PER_KG
        warnings.append(
            "Wybrane tempo wymagałoby jedzenia poniżej przemiany spoczynkowej. "
            f"Plan zatrzymuje się na {bmr:.0f} kcal, co daje ok. {_pl(round(pace, 2))} kg/tydz."
        )
    kcal = _round(kcal, 10)
    adjustment = kcal - tdee
    if profile.goal == "lose":
        notes.append(
            f"Deficyt {-adjustment:.0f} kcal dziennie ≈ {_pl(pace)} kg na tydzień "
            f"(1 kg tkanki ≈ {KCAL_PER_KG:.0f} kcal)."
        )
    elif profile.goal == "gain":
        notes.append(f"Nadwyżka {adjustment:.0f} kcal dziennie ≈ {_pl(pace)} kg na tydzień.")
    notes.append(f"Cel kaloryczny: {kcal:.0f} kcal.")

    protein_per_kg = profile.protein_g_per_kg or DEFAULT_PROTEIN_PER_KG[profile.goal]
    protein = _round(protein_per_kg * w, 5)
    fat = _round(kcal * FAT_SHARE / KCAL_PER_G["fat"], 5)
    carbs_kcal = kcal - protein * KCAL_PER_G["protein"] - fat * KCAL_PER_G["fat"]
    if carbs_kcal < 0:
        fat = _round(kcal * MIN_FAT_SHARE / KCAL_PER_G["fat"], 5)
        carbs_kcal = max(0.0, kcal - protein * KCAL_PER_G["protein"] - fat * KCAL_PER_G["fat"])
        warnings.append("Białko zajmuje prawie całą kaloryczność: obniż białko na kg.")
    carbs = _round(carbs_kcal / KCAL_PER_G["carbs"], 5)
    notes += [
        f"Białko: {_pl(protein_per_kg)} g × {_pl(w)} kg = {protein:.0f} g (co najmniej). "
        "ISSN zaleca 1,4–2,0 g/kg, przy redukcji u trenujących siłowo więcej.",
        f"Tłuszcz: {FAT_SHARE:.0%} kalorii = {fat:.0f} g.",
        f"Węglowodany: reszta kalorii = {carbs:.0f} g.",
    ]

    fiber = _round(max(MIN_FIBER_G, kcal / 1000 * FIBER_PER_1000_KCAL), 1)
    sat_fat = _round(kcal * SAT_FAT_MAX_SHARE / KCAL_PER_G["fat"], 1)
    notes += [
        f"Błonnik: {FIBER_PER_1000_KCAL:g} g na 1000 kcal, nie mniej niż {MIN_FIBER_G:g} g "
        f"= {fiber:.0f} g (co najmniej).",
        f"Tłuszcze nasycone: poniżej 10% kalorii = najwyżej {sat_fat:.0f} g (WHO).",
        f"Sól: najwyżej {SALT_MAX_G:g} g (WHO).",
        "Cukry: bez limitu. Zalecenie WHO dotyczy cukrów dodanych, a etykieta podaje "
        "wszystkie cukry, także z owoców i nabiału.",
    ]

    goals = {
        "kcal": kcal,
        "protein_g": protein,
        "fat_g": fat,
        "carbs_g": carbs,
        "fiber_g": fiber,
        "sat_fat_g": sat_fat,
        "sugars_g": None,
        "salt_g": SALT_MAX_G,
    }
    return Plan(
        age=age,
        bmr=round(bmr),
        tdee=round(tdee),
        kcal=kcal,
        adjustment=round(adjustment),
        pace_kg_week=round(pace, 2),
        protein_g_per_kg=protein_per_kg,
        goals=goals,
        notes=notes,
        warnings=warnings,
    )

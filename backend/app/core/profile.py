"""Profil i plan żywieniowy: zapotrzebowanie kaloryczne i cele makroskładników.

To szacunek z ogólnych wzorów, punkt startowy, a nie pomiar. Docelowo zapotrzebowanie
będzie korygowane trendem wagi i spożyciem (`core/energy.py`, dokumentacja 6.4).

Źródła:
- przemiana materii (BMR): Mifflin i in., Am J Clin Nutr 1990 (wzór Mifflin-St Jeor),
- zapotrzebowanie metodą składników: BMR + tryb życia (bez chodzenia) + kroki + treningi,
  plus trawienie (efekt termiczny pożywienia ≈ 10% całości),
- kroki: długość kroku 0,415 × wzrost (mężczyźni) / 0,413 × wzrost (kobiety); koszt chodzenia
  ponad spoczynek z równania ACSM: 0,1 ml O₂ na kg na metr ≈ 0,5 kcal na kg na km,
- treningi: Compendium of Physical Activities 2024 (przysiad, martwy ciąg: 5,0 MET; cardio
  umiarkowane: 7,0 MET); liczone ponad spoczynek, czyli (MET − 1) × kg × godziny,
- 1 kg masy ciała ≈ 7700 kcal (jak w `core/energy.py`),
- białko: ISSN Position Stand 2017 (1,4–2,0 g/kg; przy deficycie u trenujących siłowo
  więcej, do 2,3–3,1 g/kg),
- tłuszcz: 20–35% energii (National Academies, AMDR); domyślnie 25%,
- tłuszcze nasycone: poniżej 10% energii, sól: poniżej 5 g (WHO, Healthy diet),
- błonnik: 14 g na 1000 kcal (Dietary Guidelines for Americans), nie mniej niż 25 g (WHO).
"""

from dataclasses import dataclass, field, replace
from datetime import date
from typing import Literal

Sex = Literal["male", "female"]
Lifestyle = Literal["sitting", "mixed", "standing", "physical"]
Goal = Literal["lose", "maintain", "gain"]

KCAL_PER_KG = 7700.0

# Tryb życia BEZ chodzenia i treningów: siedzenie, stanie, drobne czynności, praca.
# Chodzenie liczą kroki, treningi osobne pola, więc nic nie jest liczone dwa razy.
# Dodatek jako ułamek BMR. [ZAŁOŻENIE] Dobrane tak, żeby całość (z krokami i treningami)
# mieściła się w zakresach PAL FAO/WHO/UNU 2004: siedzący 1,40–1,69, aktywny 1,70–1,99,
# bardzo aktywny 2,00–2,40.
LIFESTYLES: dict[str, float] = {
    "sitting": 0.15,  # nauka, biuro, dojazd autem: większość dnia siedząc
    "mixed": 0.25,  # część dnia na nogach: nauczyciel, laborant, praca w domu i ogrodzie
    "standing": 0.40,  # praca na stojąco: sklep, kuchnia, fryzjer, magazyn bez dźwigania
    "physical": 0.70,  # ciężka praca fizyczna: budowa, przeprowadzki, rolnictwo
}
LIFESTYLE_LABELS: dict[str, str] = {
    "sitting": "siedzący (nauka, biuro, dojazd autem)",
    "mixed": "mieszany (część dnia na nogach)",
    "standing": "praca na stojąco",
    "physical": "ciężka praca fizyczna",
}
TEF_SHARE = 0.10  # trawienie: ok. 10% całkowitego zapotrzebowania
STRIDE_PER_CM = {"male": 0.415, "female": 0.413}  # długość kroku jako ułamek wzrostu
WALK_NET_KCAL_PER_KG_KM = 0.5  # ACSM: 0,1 ml O₂/kg/m × ok. 5 kcal na litr O₂
STRENGTH_MET = 5.0  # przysiad, martwy ciąg, wyciskanie z przerwami między seriami
CARDIO_MET = 7.0  # rower, trucht, orbitrek w umiarkowanym tempie

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
    lifestyle: Lifestyle
    steps_per_day: int  # średnia; w etapie 3 z Apple Zdrowie
    strength_sessions_week: int
    strength_minutes: int  # długość jednej sesji
    cardio_minutes_week: int
    goal: Goal
    pace_kg_week: float
    protein_g_per_kg: float | None = None  # None = domyślne dla celu


@dataclass(frozen=True)
class EnergyPart:
    """Jeden składnik zapotrzebowania, do tabeli „Na co idą kalorie"."""

    key: str  # bmr | lifestyle | steps | strength | cardio | tef
    label: str
    kcal: float
    detail: str


@dataclass(frozen=True)
class Plan:
    age: int
    bmr: float  # przemiana materii w spoczynku
    tdee: float  # całkowite zapotrzebowanie: suma składników
    parts: list[EnergyPart]  # z czego składa się zapotrzebowanie
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
    if not 0 <= profile.steps_per_day <= 40_000:
        errors.append("Średnia kroków musi wynosić od 0 do 40 000 dziennie.")
    if not 0 <= profile.strength_sessions_week <= 14:
        errors.append("Treningów siłowych może być od 0 do 14 w tygodniu.")
    if profile.strength_sessions_week and not 15 <= profile.strength_minutes <= 240:
        errors.append("Trening siłowy musi trwać od 15 do 240 minut.")
    if not 0 <= profile.cardio_minutes_week <= 1500:
        errors.append("Cardio: od 0 do 1500 minut w tygodniu.")
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


def _thousands(value: int) -> str:
    """5000 -> „5 000" (spacja jako separator tysięcy, jak po polsku)."""
    return f"{value:,}".replace(",", " ")


def _round(value: float, step: float) -> float:
    return round(value / step) * step


def steps_kcal(steps: float, sex: Sex, height_cm: float, weight_kg: float) -> tuple[float, float]:
    """Kalorie z chodzenia ponad spoczynek i przebyty dystans w km."""
    km = steps * STRIDE_PER_CM[sex] * height_cm / 100_000
    return km * weight_kg * WALK_NET_KCAL_PER_KG_KM, km


def exercise_kcal_per_day(met: float, minutes_per_week: float, weight_kg: float) -> float:
    """Średnio na dzień, ponad spoczynek: (MET − 1) × kg × godziny ÷ 7."""
    return (met - 1) * weight_kg * minutes_per_week / 60 / 7


def energy_parts(profile: Profile, bmr: float) -> list[EnergyPart]:
    """Zapotrzebowanie metodą składników. Trawienie to 10% sumy, więc dzielimy przez 0,9."""
    w = profile.weight_kg
    lifestyle = bmr * LIFESTYLES[profile.lifestyle]
    walk, km = steps_kcal(profile.steps_per_day, profile.sex, profile.height_cm, w)
    strength_minutes = profile.strength_sessions_week * profile.strength_minutes
    strength = exercise_kcal_per_day(STRENGTH_MET, strength_minutes, w)
    cardio = exercise_kcal_per_day(CARDIO_MET, profile.cardio_minutes_week, w)
    subtotal = bmr + lifestyle + walk + strength + cardio
    tef = subtotal / (1 - TEF_SHARE) - subtotal
    return [
        EnergyPart("bmr", "Przemiana spoczynkowa", bmr, "oddychanie, serce, mózg, temperatura"),
        EnergyPart(
            "lifestyle",
            "Tryb życia",
            lifestyle,
            f"{LIFESTYLE_LABELS[profile.lifestyle]}: +{LIFESTYLES[profile.lifestyle]:.0%} "
            "przemiany spoczynkowej (bez chodzenia)",
        ),
        EnergyPart(
            "steps",
            "Kroki",
            walk,
            f"{_thousands(profile.steps_per_day)} kroków ≈ {_pl(round(km, 1))} km",
        ),
        EnergyPart(
            "strength",
            "Trening siłowy",
            strength,
            f"{profile.strength_sessions_week} × {profile.strength_minutes} min w tygodniu, "
            "średnio na dzień"
            if profile.strength_sessions_week
            else "brak",
        ),
        EnergyPart(
            "cardio",
            "Cardio",
            cardio,
            f"{profile.cardio_minutes_week} min w tygodniu, średnio na dzień"
            if profile.cardio_minutes_week
            else "brak",
        ),
        EnergyPart("tef", "Trawienie", tef, "ok. 10% całego zapotrzebowania"),
    ]


def plan_for(profile: Profile, today: date) -> Plan:
    """Cel kaloryczny i cele dzienne z profilu. Każda liczba ma opis w `notes`."""
    age = age_on(profile.birth_date, today)
    w = profile.weight_kg
    bmr = bmr_mifflin(profile.sex, w, profile.height_cm, age)
    parts = energy_parts(profile, bmr)
    tdee = sum(part.kcal for part in parts)
    walk = next(part for part in parts if part.key == "steps")
    notes = [
        f"Przemiana materii w spoczynku: {bmr:.0f} kcal (wzór Mifflin-St Jeor: płeć, wiek {age}, "
        f"{_pl(profile.height_cm)} cm, {_pl(w)} kg).",
        f"Kroki: {walk.detail}; chodzenie kosztuje ok. {_pl(WALK_NET_KCAL_PER_KG_KM)} kcal "
        f"na kg na km ponad spoczynek (równanie ACSM) = {walk.kcal:.0f} kcal.",
        f"Trening siłowy liczony jako {_pl(STRENGTH_MET)} MET, cardio jako {_pl(CARDIO_MET)} MET "
        "(Compendium of Physical Activities 2024), tylko ponad spoczynek.",
        f"Zapotrzebowanie: suma składników = {tdee:.0f} kcal "
        f"(to {_pl(round(tdee / bmr, 2))} × przemiana spoczynkowa).",
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
        parts=[replace(part, kcal=round(part.kcal)) for part in parts],
        kcal=kcal,
        adjustment=round(adjustment),
        pace_kg_week=round(pace, 2),
        protein_g_per_kg=protein_per_kg,
        goals=goals,
        notes=notes,
        warnings=warnings,
    )

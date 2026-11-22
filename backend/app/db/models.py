"""Model danych (dokumentacja, rozdział 8).

Zasady:
- osiem wartości z etykiety UE to kolumny w `food`; mikroskładniki są w `food_nutrient`,
- `meal_entry` przechowuje wartości zamrożone w chwili zapisu (historia nie zmienia się wstecz),
- `health_sample` ma klucz naturalny (type, starts_at, source), więc import jest idempotentny.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator

JsonType = JSON().with_variant(JSONB(), "postgresql")


class UtcDateTime(TypeDecorator):
    """Znacznik czasu zawsze w UTC i zawsze ze strefą.

    Postgres przechowuje `timestamptz`. SQLite (testy, szybki start bez Dockera) gubi
    strefę, więc przy odczycie jest ona dopisywana. Daty bez strefy są odrzucane, żeby
    czas lokalny nie trafił do bazy przez pomyłkę.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Data bez strefy czasowej: najpierw ustal strefę.")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


TZDateTime = UtcDateTime()


def utcnow() -> datetime:
    """Bieżący czas dla znaczników nadawanych przez aplikację.

    Znaczniki czasu wpisuje aplikacja, a nie baza: wartość domyślna `now()` z migracji
    działa tylko na Postgresie, SQLite nie zna tej funkcji i zapis kończył się błędem.
    """
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class MacroColumns:
    """Wartości z etykiety UE. W `food` na 100 g, w `meal_entry` dla zapisanej porcji."""

    kcal: Mapped[float | None]
    protein_g: Mapped[float | None]
    fat_g: Mapped[float | None]
    sat_fat_g: Mapped[float | None]
    carbs_g: Mapped[float | None]
    sugars_g: Mapped[float | None]
    fiber_g: Mapped[float | None]
    salt_g: Mapped[float | None]


# ---------- Dieta ----------


class Nutrient(Base):
    """Słownik mikroskładników (seed/nutrients.json)."""

    __tablename__ = "nutrient"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name_pl: Mapped[str] = mapped_column(String(64))
    unit: Mapped[str] = mapped_column(String(8))
    grp: Mapped[str] = mapped_column(String(16))  # vitamin | mineral
    rda: Mapped[float | None]


class Food(MacroColumns, Base):
    __tablename__ = "food"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # packaged | generic | recipe
    barcode: Mapped[str | None] = mapped_column(String(14), unique=True)
    name: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(64))
    serving_g: Mapped[float | None]
    # Jednostka odniesienia: wartości są na 100 g albo (napoje) na 100 ml.
    unit: Mapped[str] = mapped_column(String(2), default="g", server_default="g")
    origin: Mapped[str] = mapped_column(String(16))  # off | fdc | user | ai_label | ai
    # Skąd pochodzą aktualne wartości: label | reference | estimated | user
    macro_source: Mapped[str] = mapped_column(String(16))
    # Kiedy dane ostatnio zmieniono w źródle (np. w Open Food Facts).
    source_updated_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    # Kiedy użytkownik potwierdził zgodność z etykietą. NULL = niezweryfikowany.
    verified_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    generic_parent_id: Mapped[int | None] = mapped_column(ForeignKey("food.id"))
    fetched_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    raw: Mapped[dict | None] = mapped_column(JsonType)
    # Kiedy produkt trafił do ulubionych. NULL = nie jest ulubiony.
    favorite_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    # Produkt bez kodu kreskowego: identyfikator nadany na telefonie (idempotentny zapis).
    client_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, unique=True)
    # Rekord USDA FoodData Central, z którego pochodzą mikroskładniki (etap 6).
    fdc_id: Mapped[int | None]
    fdc_description: Mapped[str | None] = mapped_column(String(255))
    # Kiedy produkt był sprawdzany w tabeli USDA (automatycznie albo ręcznie). Produkt bez
    # pewnego dopasowania nie jest wyszukiwany ponownie przy każdym wpisie.
    fdc_checked_at: Mapped[datetime | None] = mapped_column(TZDateTime)


class FoodAlias(Base):
    __tablename__ = "food_alias"

    food_id: Mapped[int] = mapped_column(
        ForeignKey("food.id", ondelete="CASCADE"), primary_key=True
    )
    alias: Mapped[str] = mapped_column(String(255), primary_key=True)


class FoodNutrient(Base):
    __tablename__ = "food_nutrient"

    food_id: Mapped[int] = mapped_column(
        ForeignKey("food.id", ondelete="CASCADE"), primary_key=True
    )
    nutrient_id: Mapped[str] = mapped_column(ForeignKey("nutrient.id"), primary_key=True)
    amount_per_100g: Mapped[float]
    source: Mapped[str] = mapped_column(String(16))  # label | reference | estimated


class MealEntry(MacroColumns, Base):
    __tablename__ = "meal_entry"

    # UUID nadaje telefon: powtórzona wysyłka z kolejki offline nie tworzy duplikatu.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_slot: Mapped[str] = mapped_column(String(16))
    food_id: Mapped[int | None] = mapped_column(ForeignKey("food.id"))
    food_name: Mapped[str] = mapped_column(String(255))
    # Ilość w gramach albo mililitrach (`unit`), skopiowana z produktu w chwili dodania.
    amount: Mapped[float]
    unit: Mapped[str] = mapped_column(String(2), default="g", server_default="g")
    micros: Mapped[dict | None] = mapped_column(JsonType)
    # Skąd są wartości porcji: źródło produktu (label | user | reference) albo `estimated`,
    # gdy składnika ze zdjęcia lub opisu nie było w bazie i liczy się szacunek modelu.
    macro_source: Mapped[str | None] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(16))  # scan | search | photo | text | manual | meal
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_run.id"))
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, server_default=func.now()
    )


class DailyTarget(Base):
    """Cel dzienny obowiązujący od `date_from` do następnej zmiany celów.

    Zmiana celów zapisuje komplet wierszy z nową datą, więc dni sprzed zmiany
    zachowują stare cele. Wiersz z pustymi `min` i `max` oznacza „bez celu".
    """

    __tablename__ = "daily_target"

    date_from: Mapped[date] = mapped_column(Date, primary_key=True)
    # Identyfikator mikroskładnika albo nazwa kolumny makro (np. "kcal", "protein_g").
    nutrient_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    min: Mapped[float | None]
    max: Mapped[float | None]


class UserProfile(Base):
    """Dane do szacowania zapotrzebowania. Aplikacja ma jednego użytkownika: jeden wiersz."""

    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True)  # zawsze 1
    sex: Mapped[str] = mapped_column(String(8))  # male | female
    birth_date: Mapped[date] = mapped_column(Date)
    height_cm: Mapped[float]
    weight_kg: Mapped[float]
    lifestyle: Mapped[str] = mapped_column(String(16))  # klucz z core.profile.LIFESTYLES
    steps_per_day: Mapped[int]  # średnia; w etapie 3 z Apple Zdrowie
    strength_sessions_week: Mapped[int]
    strength_minutes: Mapped[int]  # długość jednej sesji
    cardio_minutes_week: Mapped[int]
    goal: Mapped[str] = mapped_column(String(8))  # lose | maintain | gain
    pace_kg_week: Mapped[float]
    protein_g_per_kg: Mapped[float | None]  # None = domyślne dla celu
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class MealTemplate(Base):
    """Zapisany posiłek: zestaw produktów z ilościami, dodawany do dnia jednym stuknięciem.

    Zestaw przechowuje produkty i ilości, nie wartości. Wartości liczy wpis dziennika
    w chwili dodania (i tam są zamrażane), więc poprawka produktu działa w przód.
    """

    __tablename__ = "meal_template"

    # UUID nadaje telefon: zapis zestawu może czekać w kolejce offline.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)


class MealTemplateItem(Base):
    __tablename__ = "meal_template_item"

    meal_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meal_template.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(primary_key=True)
    food_id: Mapped[int] = mapped_column(ForeignKey("food.id"))
    amount: Mapped[float]  # g albo ml, jak w produkcie


# ---------- Trening ----------


class Plan(Base):
    __tablename__ = "plan"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    data: Mapped[dict] = mapped_column(JsonType)  # zawartość seed/plan_amp_2027.json


class PlanSettings(Base):
    __tablename__ = "plan_settings"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), primary_key=True
    )
    tm: Mapped[dict] = mapped_column(JsonType, default=dict)  # {"<faza>": {"S":..,"B":..,"D":..}}
    meet_date: Mapped[date | None] = mapped_column(Date)
    adj: Mapped[dict] = mapped_column(JsonType, default=dict)  # {"ins": [...], "rem": [...]}
    collars: Mapped[bool] = mapped_column(default=False)


class SessionLog(Base):
    __tablename__ = "session_log"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), primary_key=True
    )
    session_key: Mapped[str] = mapped_column(String(16), primary_key=True)  # np. "t03-D2"
    gym: Mapped[str | None] = mapped_column(String(64))
    bodyweight: Mapped[float | None]
    note: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, server_default=func.now(), onupdate=utcnow
    )


class SetLog(Base):
    __tablename__ = "set_log"

    plan_id: Mapped[int] = mapped_column(
        ForeignKey("plan.id", ondelete="CASCADE"), primary_key=True
    )
    session_key: Mapped[str] = mapped_column(String(16), primary_key=True)
    ex_index: Mapped[int] = mapped_column(primary_key=True)
    kg: Mapped[float | None]
    reps: Mapped[float | None]
    rpe: Mapped[float | None]
    done: Mapped[bool] = mapped_column(default=False)
    ok: Mapped[str | None] = mapped_column(String(1))  # podejścia: "y" | "n"


# ---------- Zdrowie ----------


class HealthSample(Base):
    """Surowe próbki z Apple Health (wysyła je automatyzacja Skrótów)."""

    __tablename__ = "health_sample"

    type: Mapped[str] = mapped_column(String(24), primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(TZDateTime, primary_key=True)
    source: Mapped[str] = mapped_column(String(64), primary_key=True)
    ends_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    value: Mapped[float | None]
    label: Mapped[str | None] = mapped_column(String(32))  # np. faza snu
    unit: Mapped[str | None] = mapped_column(String(16))
    received_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, server_default=func.now()
    )


class HealthDaily(Base):
    __tablename__ = "health_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    sleep_min: Mapped[float | None]
    sleep_deep_min: Mapped[float | None]
    sleep_rem_min: Mapped[float | None]
    hrv_ms: Mapped[float | None]
    resting_hr: Mapped[float | None]
    weight_kg: Mapped[float | None]
    steps: Mapped[float | None]
    active_kcal: Mapped[float | None]
    readiness: Mapped[str | None] = mapped_column(String(16))
    factors: Mapped[list | None] = mapped_column(JsonType)


# ---------- AI ----------


class AiRun(Base):
    """Każde wywołanie modelu: podstawa licznika kosztów."""

    __tablename__ = "ai_run"

    id: Mapped[int] = mapped_column(primary_key=True)
    task: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(16))
    model: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    cost_usd: Mapped[float | None]
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, server_default=func.now()
    )


class CoachNote(Base):
    __tablename__ = "coach_note"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    scope: Mapped[str] = mapped_column(String(8))  # day | week
    text: Mapped[str] = mapped_column(Text)
    ai_run_id: Mapped[int | None] = mapped_column(ForeignKey("ai_run.id"))


# ---------- Etap 0 ----------


class OfflineProbe(Base):
    """Próba D: zapis wykonany offline, który ma przetrwać zamknięcie aplikacji."""

    __tablename__ = "offline_probe"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    client_created_at: Mapped[datetime] = mapped_column(TZDateTime)
    note: Mapped[str | None] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(
        TZDateTime, default=utcnow, server_default=func.now()
    )

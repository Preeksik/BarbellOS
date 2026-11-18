"""Przenosi dane z jednej bazy do drugiej, np. z lokalnego SQLite do Postgresa w Neon.

Użycie (w katalogu backend, z aktywnym środowiskiem):

    python -m app.tools.copy_db --from "sqlite:///./barbellos.db" --to "postgresql://..."

Najpierw tylko pokazuje, co przeniesie. Kopiuje dopiero z flagą --wykonaj.

Zasady:
- baza docelowa musi mieć ten sam stan migracji co źródłowa (serwer robi `alembic upgrade
  head` przy starcie, lokalnie zrób to samo przed kopiowaniem),
- baza docelowa nie może mieć jeszcze własnych danych (wpisów, produktów): narzędzie nie
  łączy dwóch historii, więc nie powstaną duplikaty,
- słownik mikroskładników i plan treningowy wgrywa serwer sam (`app.tools.seed`), więc
  te tabele są pomijane, jeśli w bazie docelowej już coś mają.
"""

import argparse
import sys

from sqlalchemy import Engine, MetaData, Table, create_engine, func, insert, select, text

from app.db.models import Base

# Tabele wypełniane przy starcie serwera: kopiowane tylko do pustej tabeli docelowej.
SEEDED = {"nutrient", "plan", "plan_settings"}
# Własne dane użytkownika: baza docelowa musi je mieć puste.
MUST_BE_EMPTY = {"food", "meal_entry", "daily_target", "user_profile", "meal_template"}


def _url(raw: str) -> str:
    """Hosting podaje `postgres://` lub `postgresql://`; wymuszamy sterownik psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if raw.startswith(prefix):
            return "postgresql+psycopg://" + raw[len(prefix) :]
    return raw


def _revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        try:
            return connection.execute(text("select version_num from alembic_version")).scalar()
        except Exception:  # noqa: BLE001 - brak tabeli = baza bez migracji
            return None


def _count(engine: Engine, table: Table) -> int:
    with engine.connect() as connection:
        return connection.execute(select(func.count()).select_from(table)).scalar_one()


def plan_copy(source: Engine, target: Engine, metadata: MetaData = Base.metadata) -> list[tuple]:
    """Lista (tabela, wierszy w źródle, decyzja). Rzuca SystemExit, gdy kopiować nie wolno."""
    src_rev, dst_rev = _revision(source), _revision(target)
    if src_rev != dst_rev:
        raise SystemExit(
            f"Różne wersje migracji: źródło {src_rev}, cel {dst_rev}. "
            "Uruchom `alembic upgrade head` na obu bazach (serwer robi to sam przy starcie)."
        )
    plan = []
    for table in metadata.sorted_tables:
        rows = _count(source, table)
        existing = _count(target, table)
        if table.name in MUST_BE_EMPTY and existing:
            raise SystemExit(
                f"Baza docelowa ma już dane w tabeli {table.name} ({existing} wierszy). "
                "Narzędzie kopiuje tylko do pustej bazy, żeby nie zdublować historii."
            )
        if table.name in SEEDED and existing:
            plan.append((table.name, rows, "pominięta: serwer wgrywa ją sam"))
        elif existing:
            plan.append((table.name, rows, f"pominięta: cel ma już {existing} wierszy"))
        else:
            plan.append((table.name, rows, "kopiuj" if rows else "pusta"))
    return plan


def copy(source: Engine, target: Engine, metadata: MetaData = Base.metadata) -> dict[str, int]:
    """Kopiuje tabele według planu w jednej transakcji. Zwraca liczbę skopiowanych wierszy."""
    decisions = {name: decision for name, _, decision in plan_copy(source, target, metadata)}
    copied: dict[str, int] = {}
    with source.connect() as src, target.begin() as dst:
        for table in metadata.sorted_tables:
            if decisions[table.name] != "kopiuj":
                continue
            rows = [dict(row._mapping) for row in src.execute(select(table))]
            dst.execute(insert(table), rows)
            copied[table.name] = len(rows)
        if target.dialect.name == "postgresql":
            _reset_sequences(dst, metadata, copied)
    return copied


def _reset_sequences(connection, metadata: MetaData, copied: dict[str, int]) -> None:
    """Po wstawieniu wierszy z własnymi id licznik Postgresa musi zacząć od kolejnego numeru."""
    for name in copied:
        table = metadata.tables[name]
        id_column = table.columns.get("id")
        if (
            id_column is None
            or not id_column.autoincrement
            or id_column.type.python_type is not int
        ):
            continue
        connection.execute(
            text(
                f"select setval(pg_get_serial_sequence('{name}', 'id'), "
                f"coalesce((select max(id) from {name}), 0) + 1, false)"
            )
        )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Przenosi dane między bazami BarbellOS.")
    parser.add_argument("--from", dest="source", required=True, help="adres bazy źródłowej")
    parser.add_argument("--to", dest="target", required=True, help="adres bazy docelowej")
    parser.add_argument("--wykonaj", action="store_true", help="naprawdę skopiuj dane")
    args = parser.parse_args(argv)

    source, target = create_engine(_url(args.source)), create_engine(_url(args.target))
    for name, rows, decision in plan_copy(source, target):
        print(f"  {name:22} {rows:6}  {decision}")
    if not args.wykonaj:
        print("\nNic nie skopiowano. Żeby skopiować, dodaj --wykonaj.")
        return
    copied = copy(source, target)
    print(f"\nSkopiowano: {sum(copied.values())} wierszy w {len(copied)} tabelach.")


if __name__ == "__main__":
    main(sys.argv[1:])

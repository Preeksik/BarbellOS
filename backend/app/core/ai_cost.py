"""Licznik kosztów AI (etap 2): koszt wywołania według cennika i podsumowanie miesiąca.

Cennik zmienia się często. Wartości poniżej sprawdzono 17.11.2026 (Gemini:
aistudio.google.com/docs/pricing; Claude: dokumentacja projektu, rozdział 7).
Na darmowym poziomie Gemini płacisz 0: licznik pokazuje, ile kosztowałoby to samo
na płatnym poziomie, żeby było wiadomo, czego się spodziewać po zmianie planu.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

# model -> (USD za milion tokenów wejścia, USD za milion tokenów wyjścia)
PRICES: dict[str, tuple[float, float]] = {
    "gemini-3.5-flash-lite": (0.30, 2.50),
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-3.8-flash": (0.75, 3.75),  # do 31.12.2026; od 2027: 1,50 / 7,50
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-4-hydrogen": (1.50, 7.50),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-opus-5-5": (4.00, 20.00),
}


def call_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    """Koszt w USD albo None, gdy modelu nie ma w cenniku lub brak liczby tokenów."""
    price = PRICES.get(model)
    if price is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens * price[0] + output_tokens * price[1]) / 1_000_000


@dataclass(frozen=True)
class TaskUsage:
    task: str
    runs: int
    failed: int
    input_tokens: int
    output_tokens: int
    cost_usd: float


def usage_summary(runs: Iterable[Mapping]) -> tuple[list[TaskUsage], int]:
    """Zużycie według zadania i liczba wywołań bez wyceny (model spoza cennika).

    Wywołanie ma klucze: task, status, input_tokens, output_tokens, cost_usd.
    """
    by_task: dict[str, dict] = {}
    unpriced = 0
    for run in runs:
        t = by_task.setdefault(
            run["task"], {"runs": 0, "failed": 0, "input": 0, "output": 0, "cost": 0.0}
        )
        t["runs"] += 1
        if run["status"] != "ok":
            t["failed"] += 1
        t["input"] += run["input_tokens"] or 0
        t["output"] += run["output_tokens"] or 0
        if run["cost_usd"] is None:
            unpriced += run["status"] == "ok"
        else:
            t["cost"] += run["cost_usd"]
    summary = [
        TaskUsage(task, t["runs"], t["failed"], t["input"], t["output"], round(t["cost"], 6))
        for task, t in sorted(by_task.items())
    ]
    return summary, unpriced

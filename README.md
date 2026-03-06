# SymOffice – symulator pracy zespołów biurowych

Projekt zawiera prosty symulator, który porównuje realizację projektów w trzech podejściach:

- `delivery` (ciągły przepływ i dostarczanie),
- `scrum` (iteracje sprintowe),
- `waterfall` (fazowe dostarczanie).

Symulator modeluje:

- zespoły podzielone na **boxy**,
- różną pojemność zespołów (liczba osób i poziom skupienia),
- zakłócenia dnia pracy (spotkania, ad-hoc, absencje),
- odmienny profil realizacji zadań wg metodyki.

## Uruchomienie

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python simulator.py --days 120 --projects 9 --tasks-per-project 40
```

## Parametry

```bash
python simulator.py --help
```

Najważniejsze opcje:

- `--days` – liczba dni symulacji,
- `--projects` – liczba projektów,
- `--tasks-per-project` – liczba zadań na projekt,
- `--seed` – losowość (powtarzalność wyników),
- `--output` – katalog na wykresy.

## Wizualizacja (propozycja)

Skrypt generuje 3 wykresy:

1. **throughput dzienny** (`throughput.svg`) – ile zadań dziennie domknięto w każdej metodyce,
2. **histogram czasu ukończenia** (`cycle_time_hist.svg`) – rozkład dni finalizacji zadań,
3. **boxplot ukończenia projektów** (`project_completion_boxplot.svg`) – kiedy średnio kończą się projekty.

To daje szybki pogląd jak środowisko reaguje na zmianę danych wejściowych.

## Jak eksperymentować

Przykładowe scenariusze:

- zwiększ `--projects` i `--tasks-per-project`, aby zasymulować przeciążenie,
- uruchamiaj z różnymi `--seed`, aby porównać wrażliwość na losowe zakłócenia,
- porównuj throughput i dzień domknięcia projektów pomiędzy metodykami.

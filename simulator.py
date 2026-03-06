from __future__ import annotations

import argparse
import random
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Dict, List

METHODOLOGIES = ("delivery", "scrum", "waterfall")
COLORS = {"delivery": "#2E86DE", "scrum": "#28B463", "waterfall": "#CB4335"}


@dataclass
class Task:
    id: int
    effort: float
    stage: str = "todo"
    done: bool = False


@dataclass
class Team:
    name: str
    box: str
    members: int
    focus: float

    def capacity_per_day(self) -> float:
        return self.members * self.focus


@dataclass
class Project:
    name: str
    methodology: str
    tasks: List[Task]
    completed_day: int | None = None

    def is_done(self) -> bool:
        return all(t.done for t in self.tasks)


@dataclass
class SimulationConfig:
    days: int = 90
    seed: int = 7
    boxes: int = 3
    teams_per_box: int = 2
    min_members: int = 4
    max_members: int = 8
    projects: int = 6
    tasks_per_project: int = 30
    min_effort: float = 1.0
    max_effort: float = 5.0


@dataclass
class SimulationResult:
    daily_completed: Dict[str, List[int]] = field(default_factory=dict)
    cycle_time: Dict[str, List[int]] = field(default_factory=dict)
    completion_day: Dict[str, List[int]] = field(default_factory=dict)


class OfficeSimulator:
    def __init__(self, cfg: SimulationConfig):
        self.cfg = cfg
        random.seed(cfg.seed)
        self.teams = self._build_teams()
        self.projects = self._build_projects()

    def _build_teams(self) -> List[Team]:
        teams: List[Team] = []
        for b in range(1, self.cfg.boxes + 1):
            for t in range(1, self.cfg.teams_per_box + 1):
                teams.append(
                    Team(
                        name=f"team_{b}_{t}",
                        box=f"box_{b}",
                        members=random.randint(self.cfg.min_members, self.cfg.max_members),
                        focus=round(random.uniform(0.65, 1.2), 2),
                    )
                )
        return teams

    def _build_projects(self) -> List[Project]:
        projects: List[Project] = []
        for p in range(1, self.cfg.projects + 1):
            methodology = METHODOLOGIES[(p - 1) % len(METHODOLOGIES)]
            tasks = [
                Task(
                    id=i,
                    effort=round(random.uniform(self.cfg.min_effort, self.cfg.max_effort), 2),
                )
                for i in range(1, self.cfg.tasks_per_project + 1)
            ]
            projects.append(Project(name=f"project_{p}", methodology=methodology, tasks=tasks))
        return projects

    def run(self) -> SimulationResult:
        result = SimulationResult(
            daily_completed={m: [0] * self.cfg.days for m in METHODOLOGIES},
            cycle_time={m: [] for m in METHODOLOGIES},
            completion_day={m: [] for m in METHODOLOGIES},
        )

        for day in range(self.cfg.days):
            for project in self.projects:
                if project.is_done():
                    continue

                capacity = self._sample_capacity(project.methodology, day)
                finished_today = self._work_on_project(project, capacity, day, result)
                result.daily_completed[project.methodology][day] += finished_today

                if project.is_done() and project.completed_day is None:
                    project.completed_day = day + 1
                    result.completion_day[project.methodology].append(project.completed_day)

        return result

    def _sample_capacity(self, methodology: str, day: int) -> float:
        team = random.choice(self.teams)
        base = team.capacity_per_day()
        noise = random.uniform(0.75, 1.15)

        if methodology == "scrum":
            sprint_day = day % 10
            if sprint_day in (0, 1):
                noise *= 0.85
            elif sprint_day in (8, 9):
                noise *= 0.9
            else:
                noise *= 1.08
        elif methodology == "waterfall":
            noise *= 0.92
        elif methodology == "delivery":
            noise *= 1.05

        return max(0.2, base * noise)

    def _work_on_project(
        self, project: Project, capacity: float, day: int, result: SimulationResult
    ) -> int:
        finished = 0

        if project.methodology == "waterfall":
            done_fraction = sum(t.done for t in project.tasks) / len(project.tasks)
            if done_fraction < 0.2:
                capacity *= 0.55
            elif done_fraction < 0.6:
                capacity *= 1.0
            elif done_fraction < 0.9:
                capacity *= 0.8
            else:
                capacity *= 0.65

        release_window = True
        if project.methodology == "scrum":
            release_window = (day % 10) in (8, 9)

        for task in project.tasks:
            if task.done:
                continue
            if capacity <= 0:
                break

            work = min(task.effort, capacity)
            task.effort -= work
            capacity -= work

            if task.effort <= 0.01:
                if project.methodology == "scrum" and not release_window:
                    task.effort = 0
                    task.stage = "done_waiting"
                else:
                    task.done = True
                    task.stage = "done"
                    finished += 1
                    result.cycle_time[project.methodology].append(day + 1)

        if project.methodology == "scrum" and release_window:
            for task in project.tasks:
                if task.stage == "done_waiting":
                    task.done = True
                    task.stage = "done"
                    finished += 1
                    result.cycle_time[project.methodology].append(day + 1)

        return finished


def _svg_header(width: int, height: int, title: str) -> str:
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' fill='white'/>"
        f"<text x='20' y='30' font-size='20' font-family='Arial'>{title}</text>"
    )


def _write_svg(path: Path, body: str) -> None:
    path.write_text(body + "</svg>\n", encoding="utf-8")


def _line_chart_svg(series: Dict[str, List[int]], path: Path, title: str) -> None:
    width, height = 1000, 450
    left, top, chart_w, chart_h = 70, 60, 880, 320
    max_y = max(max(v) for v in series.values()) if series else 1
    max_y = max(max_y, 1)
    days = len(next(iter(series.values()))) if series else 1

    body = [_svg_header(width, height, title)]
    body.append(f"<rect x='{left}' y='{top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#999'/>" )

    for i in range(6):
        y_val = max_y * i / 5
        y = top + chart_h - (chart_h * i / 5)
        body.append(f"<line x1='{left}' y1='{y:.1f}' x2='{left + chart_w}' y2='{y:.1f}' stroke='#eee'/>" )
        body.append(f"<text x='10' y='{y + 4:.1f}' font-size='12'>{y_val:.0f}</text>")

    for m, values in series.items():
        points = []
        for i, value in enumerate(values):
            x = left + (chart_w * (i / max(days - 1, 1)))
            y = top + chart_h - (chart_h * (value / max_y))
            points.append(f"{x:.2f},{y:.2f}")
        body.append(
            f"<polyline fill='none' stroke='{COLORS[m]}' stroke-width='2' points='{' '.join(points)}'/>"
        )

    lx = left
    for m in series:
        body.append(f"<rect x='{lx}' y='{top + chart_h + 20}' width='15' height='15' fill='{COLORS[m]}'/>" )
        body.append(f"<text x='{lx + 20}' y='{top + chart_h + 32}' font-size='13'>{m}</text>")
        lx += 140

    _write_svg(path, "".join(body))


def _hist_chart_svg(series: Dict[str, List[int]], path: Path, title: str) -> None:
    width, height = 1000, 450
    left, top, chart_w, chart_h = 70, 60, 880, 320
    all_vals = [v for arr in series.values() for v in arr] or [1]
    max_x = max(all_vals)
    bins = 20

    counts = {m: [0] * bins for m in series}
    for m, arr in series.items():
        for v in arr:
            idx = min(bins - 1, int((v / max(max_x, 1)) * bins))
            counts[m][idx] += 1

    max_count = max(max(v) for v in counts.values()) if counts else 1
    max_count = max(max_count, 1)

    body = [_svg_header(width, height, title)]
    body.append(f"<rect x='{left}' y='{top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#999'/>" )

    group_w = chart_w / bins
    bar_w = group_w / max(len(series), 1)

    for i in range(bins):
        for j, m in enumerate(series.keys()):
            val = counts[m][i]
            h = chart_h * (val / max_count)
            x = left + i * group_w + j * bar_w
            y = top + chart_h - h
            body.append(
                f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w - 1:.1f}' height='{h:.1f}' fill='{COLORS[m]}' opacity='0.65'/>"
            )

    lx = left
    for m in series:
        body.append(f"<rect x='{lx}' y='{top + chart_h + 20}' width='15' height='15' fill='{COLORS[m]}'/>" )
        body.append(f"<text x='{lx + 20}' y='{top + chart_h + 32}' font-size='13'>{m}</text>")
        lx += 140

    _write_svg(path, "".join(body))


def _boxplot_svg(series: Dict[str, List[int]], path: Path, title: str) -> None:
    width, height = 900, 450
    left, top, chart_w, chart_h = 80, 60, 760, 320
    data = {k: sorted(v) for k, v in series.items() if v}
    all_vals = [x for arr in data.values() for x in arr] or [1]
    max_y = max(all_vals)

    body = [_svg_header(width, height, title)]
    body.append(f"<rect x='{left}' y='{top}' width='{chart_w}' height='{chart_h}' fill='none' stroke='#999'/>" )

    def y(v: float) -> float:
        return top + chart_h - chart_h * (v / max(max_y, 1))

    keys = list(data.keys())
    spacing = chart_w / max(len(keys), 1)

    for i, k in enumerate(keys):
        arr = data[k]
        q1 = arr[len(arr) // 4]
        med = median(arr)
        q3 = arr[(3 * len(arr)) // 4]
        low = arr[0]
        high = arr[-1]
        x = left + spacing * i + spacing / 2

        body.append(f"<line x1='{x:.1f}' y1='{y(low):.1f}' x2='{x:.1f}' y2='{y(high):.1f}' stroke='#666'/>" )
        body.append(
            f"<rect x='{x - 28:.1f}' y='{y(q3):.1f}' width='56' height='{max(1, y(q1)-y(q3)):.1f}' fill='{COLORS[k]}' opacity='0.35' stroke='{COLORS[k]}'/>"
        )
        body.append(f"<line x1='{x - 28:.1f}' y1='{y(med):.1f}' x2='{x + 28:.1f}' y2='{y(med):.1f}' stroke='#000'/>" )
        body.append(f"<text x='{x - 28:.1f}' y='{top + chart_h + 25}' font-size='13'>{k}</text>")

    _write_svg(path, "".join(body))


def plot_results(result: SimulationResult, output_dir: Path) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    p1 = output_dir / "throughput.svg"
    p2 = output_dir / "cycle_time_hist.svg"
    p3 = output_dir / "project_completion_boxplot.svg"

    _line_chart_svg(result.daily_completed, p1, "Dzienny throughput (ukończone zadania)")
    _hist_chart_svg(result.cycle_time, p2, "Rozkład czasu ukończenia zadań")
    _boxplot_svg(result.completion_day, p3, "Dzień ukończenia projektu wg metodyki")
    return [p1, p2, p3]


def summary_table(result: SimulationResult) -> str:
    lines = ["\n=== PODSUMOWANIE ==="]
    for methodology in METHODOLOGIES:
        throughput = sum(result.daily_completed[methodology])
        cycle = result.cycle_time[methodology]
        mean_cycle = sum(cycle) / len(cycle) if cycle else 0
        projects = result.completion_day[methodology]
        mean_project_day = sum(projects) / len(projects) if projects else 0
        lines.append(
            f"{methodology:10} | tasks={throughput:4d} | avg_finish_day={mean_cycle:6.2f} | avg_project_done_day={mean_project_day:6.2f}"
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Symulator pracy zespołów biurowych: Delivery, Scrum, Waterfall"
    )
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--projects", type=int, default=6)
    parser.add_argument("--tasks-per-project", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path, default=Path("artifacts"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = SimulationConfig(
        days=args.days,
        projects=args.projects,
        tasks_per_project=args.tasks_per_project,
        seed=args.seed,
    )
    sim = OfficeSimulator(cfg)
    result = sim.run()
    images = plot_results(result, args.output)

    print(summary_table(result))
    print("\nWygenerowane wizualizacje (SVG):")
    for img in images:
        print(f"- {img}")


if __name__ == "__main__":
    main()

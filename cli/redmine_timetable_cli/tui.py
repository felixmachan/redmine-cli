from __future__ import annotations

from datetime import date

import time
import questionary
from rich import box
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .ascii_art import BANNER
from .models import RedmineActivity, RedmineIssue, RedmineProject, RedmineTracker, TimetableRunResult
from .services.timetable_service import list_recent_months

USE_CURRENT_ISSUE = "__use_current_issue__"
CREATE_AT_PROJECT_ROOT = "__create_at_project_root__"
ACCENT = "bright_cyan"
WARM = "bright_magenta"
SUCCESS = "bright_green"
WARNING = "bright_yellow"
MUTED = "grey62"
MONTH_COLORS = [
    "bright_cyan",
    "bright_magenta",
    "bright_green",
    "bright_yellow",
    "bright_blue",
    "bright_red",
    "cyan",
    "magenta",
    "green",
    "yellow",
    "blue",
    "red",
]


def make_table(title: str, border_style: str = ACCENT) -> Table:
    table = Table(
        title=f"[bold {border_style}]{title}[/bold {border_style}]",
        border_style=border_style,
        header_style=f"bold {border_style}",
        box=box.ROUNDED,
        pad_edge=True,
    )
    table.row_styles = ["none", "dim"]
    return table


def make_panel(content, title: str, border_style: str = ACCENT, subtitle: str | None = None) -> Panel:
    return Panel(
        content,
        title=f"[bold {border_style}]{title}[/bold {border_style}]",
        subtitle=subtitle,
        border_style=border_style,
        box=box.ROUNDED,
        padding=(0, 1),
    )


def render_banner(console: Console) -> None:
    text = Text(BANNER, style="bold red")
    console.print(text)
    console.rule("[bold red]redmine-cli[/bold red]", style="red")


def render_help(console: Console) -> None:
    table = make_table("Available Commands", WARM)
    table.add_column("Command", style="bold")
    table.add_column("Description")
    table.add_row("redmine", "Open the interactive command hub.")
    table.add_row("redmine timetable", "Generate Excel and PDF from Redmine time entries.")
    table.add_row("redmine upload", "Upload Notion Done tasks to Redmine issues and spent time.")
    table.add_row("redmine config doctor", "Show config and workspace diagnostics.")
    console.print(table)


def render_settings_intro(console: Console) -> None:
    intro = Table.grid(expand=True)
    intro.add_column(ratio=1)
    intro.add_column(ratio=1)
    intro.add_column(ratio=1)
    intro.add_row(
        f"[bold {WARM}]Redmine[/bold {WARM}]\n[dim]URL, API key, user, activity defaults[/dim]",
        f"[bold {ACCENT}]Notion[/bold {ACCENT}]\n[dim]token, databases, sync filters[/dim]",
        f"[bold {SUCCESS}]Salary[/bold {SUCCESS}]\n[dim]hourly rate and currency[/dim]",
    )
    console.print(make_panel(intro, "Settings", WARM, "Manage local configuration"))


def main_menu(show_notion: bool = True) -> str:
    choices = [
        questionary.Choice("Get monthly working hours", "hours"),
        questionary.Choice("Log time manually", "log"),
        questionary.Choice("Create new issue", "issue_new"),
        questionary.Choice("Statistics", "stats"),
        questionary.Choice("Timetable export", "timetable"),
    ]

    if show_notion:
        choices.append(questionary.Choice("Upload Notion Done tasks", "upload"))

    choices.extend([
        questionary.Choice("Settings", "settings"),
        questionary.Choice("Exit", "exit"),
    ])

    return questionary.select(
        "Choose a command",
        choices=choices,
    ).ask() or "exit"


def choose_setting_to_edit() -> str:
    return questionary.select(
        "Which setting would you like to change?",
        choices=[
            questionary.Separator("=== REDMINE ==="),
            questionary.Choice("Redmine Base URL", "REDMINE_BASE_URL"),
            questionary.Choice("Redmine API Key", "REDMINE_API_KEY"),
            questionary.Choice("Redmine User ID (e.g. 'me' or ID)", "REDMINE_USER_ID"),
            questionary.Choice("Default Redmine Activity", "DEFAULT_REDMINE_ACTIVITY_ID"),
            questionary.Separator("=== NOTION ==="),
            questionary.Choice("Notion Integration Enabled", "NOTION_ENABLED"),
            questionary.Choice("Notion API Token", "NOTION_API_TOKEN"),
            questionary.Choice("Notion Tasks Database ID", "NOTION_TASKS_DATABASE_ID"),
            questionary.Choice("Notion Projects Database ID", "NOTION_PROJECTS_DATABASE_ID"),
            questionary.Choice("Notion Project Names (comma-separated)", "NOTION_PROJECT_NAMES"),
            questionary.Choice("Notion Done Status Name", "NOTION_DONE_STATUS_NAME"),
            questionary.Separator("=== SALARY ==="),
            questionary.Choice("Salary per hour", "SALARY_PER_HOUR"),
            questionary.Choice("Salary currency", "SALARY_CURRENCY"),
            questionary.Separator(""),
            questionary.Choice("Back to main menu", "back"),
        ]
    ).ask() or "back"


def show_project_distribution(console: Console, year: int, month: int, project_data: list[tuple[str, float]]) -> None:
    import math

    project_data = sorted(project_data, key=lambda item: item[1], reverse=True)
    total_hours = sum(hours for _, hours in project_data)
    if total_hours == 0:
        console.print(f"[{WARNING}]No data to display.[/{WARNING}]")
        return

    colors = ["magenta", "cyan", "yellow", "green", "red", "blue", "white"]

    def generate_pie(step: float) -> Panel:
        legend = Table(title=f"[bold {ACCENT}]Projects[/bold {ACCENT}]", box=None, pad_edge=False, expand=True)
        legend.add_column("#", justify="right", style=MUTED, width=2)
        legend.add_column("Project", style=f"bold {ACCENT}")
        legend.add_column("Hours", justify="right", width=8)
        legend.add_column("%", justify="right", width=7)
        legend.add_column("Share", width=18)

        current_angle = 0.0
        project_angles: list[tuple[float, float, str]] = []
        for index, (name, hours) in enumerate(project_data, start=1):
            share = hours / total_hours
            color = colors[(index - 1) % len(colors)]
            project_angles.append((current_angle, current_angle + share, color))
            current_angle += share

            bar_width = max(1, int(round(share * 14)))
            share_bar = Text("\u25A0" * bar_width, style=color)
            share_bar.append("\u00B7" * max(0, 14 - bar_width), style=MUTED)

            legend.add_row(
                f"[{color}]{index}[/{color}]",
                f"[{color}]{name}[/{color}]",
                f"[{color}]{hours:.2f}[/{color}]",
                f"[{color}]{share * 100:.1f}%[/{color}]",
                share_bar,
            )

        donut_lines: list[Text] = []
        outer_radius = 4.6
        inner_radius = 2.0
        canvas_width = 16
        half_width = canvas_width // 2

        for y in range(-4, 5):
            line = Text()
            for x in range(-half_width, half_width):
                x_scaled = x / 1.2
                distance = math.sqrt((x_scaled * x_scaled) + (y * y))
                if inner_radius <= distance <= outer_radius:
                    angle = (math.atan2(y, x_scaled) / (2 * math.pi)) + 0.5
                    animated_angle = angle * step
                    char = "\u00B7"
                    segment_style = MUTED
                    for start, end, color in project_angles:
                        if start <= animated_angle < end:
                            char = "\u25A0"
                            segment_style = color
                            break
                    line.append(char, style=segment_style)
                else:
                    line.append(" ")
            donut_lines.append(line)

        donut = Text("\n").join(donut_lines)

        layout_grid = Table.grid(expand=True)
        layout_grid.add_column(width=18)
        layout_grid.add_column(ratio=1)
        layout_grid.add_row(donut, legend)

        return make_panel(
            layout_grid,
            f"Project Distribution {year}-{month:02d}",
            WARM,
            f"{len(project_data)} projects, {total_hours:.2f}h total",
        )

    with Live(generate_pie(0), refresh_per_second=12) as live:
        for i in range(1, 11):
            live.update(generate_pie(i / 10))
            time.sleep(0.04)


def show_historical_trends(console: Console, stats: list[dict], currency: str) -> None:
    filtered_stats = [s for s in stats if s["hours"] > 0]

    if not filtered_stats:
        console.print(f"[{WARNING}]No working hours found in the requested period.[/{WARNING}]")
        return

    max_hours = max((s["hours"] for s in filtered_stats), default=1)

    def generate_table(step: float) -> Table:
        table = make_table("Historical Trends", WARNING)
        table.add_column("Month", style="bold")
        table.add_column("Hours", justify="right")
        table.add_column("Earnings", justify="right")
        table.add_column("Trend")

        for index, s in enumerate(filtered_stats):
            current_hours = s["hours"] * step
            current_earnings = s["earnings"] * step
            bar_len = int((s["hours"] * step) / max_hours * 20)
            color = MONTH_COLORS[index % len(MONTH_COLORS)]
            graph = Text("\u25A0" * bar_len, style=color)
            table.add_row(
                f"[{color}]{s['label']}[/{color}]",
                f"[{color}]{current_hours:.2f}[/{color}]",
                f"[{color}]{current_earnings:,.0f} {currency}[/{color}]",
                graph,
            )

        avg_hours = sum(s["hours"] for s in filtered_stats) / len(filtered_stats) * step
        avg_earnings = sum(s["earnings"] for s in filtered_stats) / len(filtered_stats) * step

        table.add_section()
        table.add_row(
            f"[bold {ACCENT}]Average[/bold {ACCENT}]",
            f"[bold {ACCENT}]{avg_hours:.2f}[/bold {ACCENT}]",
            f"[bold {ACCENT}]{avg_earnings:,.0f} {currency}[/bold {ACCENT}]",
            "",
        )
        return table

    with Live(generate_table(0), refresh_per_second=10) as live:
        for i in range(11):
            live.update(generate_table(i / 10))
            time.sleep(0.05)


def choose_issue_from_list(issues: list[RedmineIssue]) -> RedmineIssue:
    sorted_issues = sorted(issues, key=lambda issue: issue.id, reverse=True)
    choices = [
        questionary.Choice(
            title=f"#{issue.id} {issue.subject} [{issue.status_name or 'unknown'}]",
            value=issue,
        )
        for issue in sorted_issues
    ]
    return questionary.select("Choose the Redmine issue", choices=choices).ask()


def show_hours_summary(
    console: Console,
    year: int,
    month: int,
    days: list[tuple[str, float]],
    salary_per_hour: float | None = None,
    currency: str = "HUF",
) -> None:
    total_hours = sum(h for _, h in days)

    table = make_table(f"Working Hours {year}-{month:02d}", ACCENT)
    table.add_column("Day", style="bold")
    table.add_column("Hours", justify="right")

    for day_str, hours in days:
        table.add_row(day_str, f"{hours:.2f}")

    table.add_section()
    table.add_row(f"[bold {SUCCESS}]Total[/bold {SUCCESS}]", f"[bold {SUCCESS}]{total_hours:.2f}[/bold {SUCCESS}]")

    console.print(table)

    summary_text = f"Total worked: [bold {SUCCESS}]{total_hours:.2f} hours[/bold {SUCCESS}]"
    if salary_per_hour:
        total_salary = total_hours * salary_per_hour
        summary_text += (
            f"\nEstimated salary: [bold {WARNING}]{total_salary:,.0f} {currency}[/bold {WARNING}] "
            f"([dim]{salary_per_hour:,.0f} {currency}/h[/dim])"
        )

    console.print(make_panel(summary_text, "Summary", SUCCESS))


def select_month(today: date) -> tuple[int, int]:
    choices = [
        questionary.Choice(title=label, value=(year, month))
        for label, year, month in list_recent_months(today)
    ]
    return questionary.select("Which month should be exported?", choices=choices).ask()


def ask_path(prompt: str, default: str) -> str:
    return questionary.text(prompt, default=default).ask() or default


def ask_text(prompt: str, default: str = "") -> str:
    return questionary.text(prompt, default=default).ask() or default


def ask_secret(prompt: str) -> str:
    return questionary.password(prompt).ask() or ""


def ask_confirm(prompt: str, default: bool = True) -> bool:
    return bool(questionary.confirm(prompt, default=default).ask())


def choose_redmine_project(projects: list[RedmineProject]) -> RedmineProject:
    choices = [
        questionary.Choice(title=f"{project.name} (#{project.id})", value=project)
        for project in projects
    ]
    return questionary.select("Choose the Redmine project", choices=choices).ask()


def choose_redmine_activity(
    activities: list[RedmineActivity],
    default_activity_id: int | None = None,
) -> RedmineActivity:
    default_choice = None
    choices = []
    for activity in activities:
        choices.append(
            questionary.Choice(
                title=f"{activity.name} (#{activity.id})",
                value=activity,
            )
        )
        if default_activity_id == activity.id:
            default_choice = activity
        elif default_choice is None and activity.is_default:
            default_choice = activity

    return questionary.select(
        "Choose the Redmine activity",
        choices=choices,
        default=default_choice,
    ).ask()


def choose_issue_creation_target() -> str:
    return questionary.select(
        "Where should the new Redmine issue be created?",
        choices=[
            questionary.Choice("Directly under the selected project", CREATE_AT_PROJECT_ROOT),
            questionary.Choice("As a subtask under an existing issue", "subtask"),
        ],
    ).ask()


def choose_redmine_tracker(trackers: list[RedmineTracker], default_names: tuple[str, ...] = ("Feature", "Bug")) -> RedmineTracker:
    default_choice = None
    choices = []
    for tracker in trackers:
        choices.append(questionary.Choice(title=f"{tracker.name} (#{tracker.id})", value=tracker))
        if default_choice is None and tracker.name in default_names:
            default_choice = tracker

    return questionary.select(
        "Choose the issue type",
        choices=choices,
        default=default_choice,
    ).ask()


def choose_work_private_scope(default_value: str | None) -> str | None:
    choices = [
        questionary.Choice("Any", None),
        questionary.Choice("Work", "Work"),
        questionary.Choice("Private", "Private"),
    ]
    default_choice = default_value if default_value in {"Work", "Private"} else None
    return questionary.select("Which Work / Private scope should be queried?", choices=choices, default=default_choice).ask()


def choose_notion_project_name(project_names: list[str], default_value: str | None = None) -> str | None:
    choices = [questionary.Choice("Any project", None)]
    choices.extend(questionary.Choice(name, name) for name in project_names)
    return questionary.select(
        "Which Notion project's Done tasks should be checked?",
        choices=choices,
        default=default_value if default_value in project_names else None,
    ).ask()


def choose_issue_or_descend(current_issue: RedmineIssue, children: list[RedmineIssue]) -> RedmineIssue | None:
    sorted_children = sorted(children, key=lambda issue: issue.id)
    choices = [
        questionary.Choice(
            title=f"Use this issue: #{current_issue.id} {current_issue.subject}",
            value=USE_CURRENT_ISSUE,
        )
    ]
    choices.extend(
        questionary.Choice(
            f"Go into subtask: #{child.id} {child.subject} [{child.status_name or 'unknown'}]",
            child,
        )
        for child in sorted_children
    )
    selection = questionary.select(
        f"Current issue #{current_issue.id}. Press Enter to log here or choose a subtask.",
        choices=choices,
    ).ask()
    if selection == USE_CURRENT_ISSUE:
        return None
    return selection


def choose_top_level_issue(issues: list[RedmineIssue]) -> RedmineIssue:
    sorted_issues = sorted(issues, key=lambda issue: issue.id)
    choices = [
        questionary.Choice(
            title=f"#{issue.id} {issue.subject} [{issue.status_name or 'unknown'}]",
            value=issue,
        )
        for issue in sorted_issues
    ]
    return questionary.select("Choose the root Redmine issue", choices=choices).ask()


def ask_minutes(prompt: str, default: str = "0") -> int:
    value = questionary.text(prompt, default=default).ask() or default
    minutes = int(value)
    if minutes < 0 or minutes > 59:
        raise ValueError("Minutes must be between 0 and 59.")
    return minutes


def ask_percent_done(prompt: str, default: str = "100%") -> int:
    value = (questionary.text(prompt, default=default).ask() or default).strip()
    if value.endswith("%"):
        value = value[:-1].strip()
    percent = int(value)
    if percent < 0 or percent > 100:
        raise ValueError("Percent done must be between 0 and 100.")
    return percent


def show_timetable_result(console: Console, result: TimetableRunResult) -> None:
    table = make_table("Timetable Export Finished", SUCCESS)
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Excel", f"[{ACCENT}]{result.excel_path}[/{ACCENT}]")
    table.add_row("PDF", f"[{ACCENT}]{result.pdf_path}[/{ACCENT}]")
    table.add_row("PDF engine", result.pdf_engine)
    table.add_row("Range", f"{result.date_from} -> {result.date_to}")
    table.add_row("Print area", result.print_area)
    table.add_row("Fetched entries", str(result.fetched_entries))
    table.add_row("Filled workdays", str(result.filled_workdays))
    console.print(table)


def show_doctor(console: Console, rows: list[tuple[str, str]]) -> None:
    table = make_table("Config Doctor", ACCENT)
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in rows:
        value_style = SUCCESS if value == "set" else WARNING if value == "missing" else MUTED if value in {"not set", ""} else None
        rendered_value = f"[{value_style}]{value}[/{value_style}]" if value_style else value
        table.add_row(key, rendered_value)
    console.print(table)


def show_upload_summary(console: Console, rows: list[tuple[str, str, str]]) -> None:
    table = make_table("Upload Summary", SUCCESS)
    table.add_column("Task", style=f"bold {WARM}")
    table.add_column("Issue", style=ACCENT)
    table.add_column("Time", style=WARNING)
    for task_title, issue_label, time_label in rows:
        table.add_row(task_title, issue_label, time_label)
    console.print(table)

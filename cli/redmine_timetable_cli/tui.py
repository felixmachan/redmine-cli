from __future__ import annotations

from datetime import date

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .ascii_art import BANNER
from .models import RedmineActivity, RedmineIssue, RedmineProject, RedmineTracker, TimetableRunResult
from .services.timetable_service import list_recent_months

USE_CURRENT_ISSUE = "__use_current_issue__"
CREATE_AT_PROJECT_ROOT = "__create_at_project_root__"


def render_banner(console: Console) -> None:
    text = Text(BANNER, style="bold red")
    console.print(text)
    console.rule("[bold red]REDMINE CLI / TUI v2[/bold red]")


def render_help(console: Console) -> None:
    table = Table(title="Available commands", border_style="red")
    table.add_column("Command", style="bold")
    table.add_column("Description")
    table.add_row("redmine", "Open the interactive command hub.")
    table.add_row("redmine timetable", "Generate Excel and PDF from Redmine time entries.")
    table.add_row("redmine upload", "Upload Notion Done tasks to Redmine issues and spent time.")
    table.add_row("redmine config doctor", "Show config and workspace diagnostics.")
    console.print(table)


def main_menu() -> str:
    return questionary.select(
        "Choose a command",
        choices=[
            questionary.Choice("Get monthly working hours", "hours"),
            questionary.Choice("Timetable export", "timetable"),
            questionary.Choice("Upload Notion Done tasks", "upload"),
            questionary.Choice("Exit", "exit"),
        ],
    ).ask() or "exit"


def show_hours_summary(
    console: Console,
    year: int,
    month: int,
    days: list[tuple[str, float]],
    salary_per_hour: float | None = None,
    currency: str = "HUF",
) -> None:
    total_hours = sum(h for _, h in days)
    
    table = Table(title=f"Working hours for {year}-{month:02d}", border_style="cyan")
    table.add_column("Day", style="bold")
    table.add_column("Hours", justify="right")
    
    for day_str, hours in days:
        table.add_row(day_str, f"{hours:.2f}")
    
    table.add_section()
    table.add_row("[bold]Total[/bold]", f"[bold green]{total_hours:.2f}[/bold green]")
    
    console.print(table)
    
    summary_text = f"Total worked: [bold green]{total_hours:.2f} hours[/bold green]"
    if salary_per_hour:
        total_salary = total_hours * salary_per_hour
        summary_text += f"\nEstimated salary: [bold yellow]{total_salary:,.0f} {currency}[/bold yellow] ([dim]{salary_per_hour:,.0f} {currency}/h[/dim])"
    
    console.print(Panel(summary_text, border_style="green"))


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
    table = Table(title="Timetable export finished", border_style="green")
    table.add_column("Field", style="bold")
    table.add_column("Value")
    table.add_row("Excel", result.excel_path)
    table.add_row("PDF", result.pdf_path)
    table.add_row("PDF engine", result.pdf_engine)
    table.add_row("Range", f"{result.date_from} -> {result.date_to}")
    table.add_row("Print area", result.print_area)
    table.add_row("Fetched entries", str(result.fetched_entries))
    table.add_row("Filled workdays", str(result.filled_workdays))
    console.print(table)


def show_doctor(console: Console, rows: list[tuple[str, str]]) -> None:
    table = Table(title="Config doctor", border_style="cyan")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    for key, value in rows:
        table.add_row(key, value)
    console.print(table)


def show_upload_summary(console: Console, rows: list[tuple[str, str, str]]) -> None:
    table = Table(title="Upload summary", border_style="green")
    table.add_column("Task", style="bold")
    table.add_column("Issue")
    table.add_column("Time")
    for task_title, issue_label, time_label in rows:
        table.add_row(task_title, issue_label, time_label)
    console.print(table)

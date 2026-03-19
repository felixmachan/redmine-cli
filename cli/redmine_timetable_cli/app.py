from __future__ import annotations

import sys
from datetime import date

import questionary
from rich.console import Console
from rich.panel import Panel

from .config import load_config, persist_env_value
from .services.notion_api import NotionClient
from .services.redmine_api import RedmineClient
from .services.timetable_service import (
    aggregate_hours_by_day,
    aggregate_hours_by_project,
    get_historical_stats,
    get_time_entries,
    month_to_date_range,
    run_timetable,
)
from .tui import (
    ask_confirm,
    ask_percent_done,
    ask_minutes,
    ask_path,
    ask_secret,
    ask_text,
    CREATE_AT_PROJECT_ROOT,
    choose_issue_creation_target,
    choose_issue_from_list,
    choose_redmine_activity,
    choose_redmine_tracker,
    choose_issue_or_descend,
    choose_notion_project_name,
    choose_redmine_project,
    choose_setting_to_edit,
    choose_top_level_issue,
    choose_work_private_scope,
    main_menu,
    render_banner,
    render_help,
    render_settings_intro,
    select_month,
    show_doctor,
    show_historical_trends,
    show_hours_summary,
    show_project_distribution,
    show_timetable_result,
    show_upload_summary,
)
from .workspace import discover_current_dir, discover_workspace_root


class CliApp:
    def __init__(self) -> None:
        self.console = Console()
        self.current_dir = discover_current_dir()
        self.workspace_root = discover_workspace_root()
        self.config = load_config(self.workspace_root, self.current_dir)
        self._banner_rendered = False

    def run(self, argv: list[str]) -> int:
        command = "hub" if not argv else " ".join(argv[:2]) if argv[:2] == ["config", "doctor"] else argv[0]

        try:
            if command == "hub":
                return self.run_hub()
            if command == "help":
                return self.run_help()
            if command == "hours":
                return self.run_hours_command()
            if command == "log":
                return self.run_log_command()
            if command == "issue" and argv[1:2] == ["new"]:
                return self.run_issue_new_command()
            if command == "stats":
                return self.run_stats_command()
            if command == "timetable":
                return self.run_timetable_command()
            if command == "upload":
                return self.run_upload_command()
            if command == "settings":
                return self.run_settings_command()
            if command == "config doctor":
                return self.run_doctor()

            self.console.print(f"[red]Unknown command:[/red] {' '.join(argv)}")
            return self.run_help()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Cancelled.[/yellow]")
            return 130
        except Exception as exc:
            self.console.print(Panel(str(exc), title="Error", border_style="red"))
            return 1

    def run_hub(self) -> int:
        self._render_banner_once()
        while True:
            selection = main_menu(show_notion=self.config.notion_enabled)
            if selection == "exit":
                return 0
            if selection == "hours":
                self.run_hours_command()
                continue
            if selection == "log":
                self.run_log_command()
                continue
            if selection == "issue_new":
                self.run_issue_new_command()
                continue
            if selection == "stats":
                self.run_stats_command()
                continue
            if selection == "timetable":
                self.run_timetable_command()
                continue
            if selection == "upload":
                self.run_upload_command()
                continue
            if selection == "settings":
                self.run_settings_command()
                continue
            return 0

    def run_help(self) -> int:
        self._render_banner_once()
        render_help(self.console)
        return 0

    def run_stats_command(self) -> int:
        self._render_banner_once()
        sub = questionary.select(
            "What kind of statistics would you like to see?",
            choices=[
                questionary.Choice("Project distribution (monthly)", "project"),
                questionary.Choice("Historical trends (earnings & hours)", "history"),
            ]
        ).ask()
        
        if not sub:
            return 0
            
        if sub == "project":
            year, month = select_month(date.today())
            date_from, date_to = month_to_date_range(year, month)
            self.console.print(f"[cyan]Fetching entries for {year}-{month:02d}...[/cyan]")
            entries = get_time_entries(
                self.config.redmine.base_url or "",
                self.config.redmine.api_key or "",
                self.config.redmine.user_id or "me",
                date_from,
                date_to,
            )
            dist = aggregate_hours_by_project(entries)
            show_project_distribution(self.console, year, month, dist)
        
        elif sub == "history":
            months_back_str = ask_text("How many months back should I look?", default="6")
            try:
                months_back = int(months_back_str)
            except ValueError:
                months_back = 6
                
            self.console.print(f"[cyan]Fetching data for the last {months_back} months (this might take a while)...[/cyan]")
            stats = get_historical_stats(self.config, months_back)
            show_historical_trends(self.console, stats, self.config.salary_currency)
            
        return 0

    def run_settings_command(self) -> int:
        self._render_banner_once()
        render_settings_intro(self.console)
        while True:
            key = choose_setting_to_edit()
            if key == "back":
                return 0
            
            # Show current value
            current_value = ""
            display_hint = ""
            
            if key == "NOTION_ENABLED":
                current_value = "True" if self.config.notion_enabled else "False"
                self.console.print(f"Current status for [bold]{key}[/bold]: [cyan]{current_value}[/cyan]")
                new_bool = ask_confirm(f"Enable Notion integration?", default=self.config.notion_enabled)
                new_value = "1" if new_bool else "0"
                
                if new_bool == self.config.notion_enabled:
                    self.console.print("[yellow]No change made.[/yellow]")
                    continue
            elif key == "REDMINE_BASE_URL": 
                current_value = self.config.redmine.base_url or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "REDMINE_API_KEY": 
                current_value = self.config.redmine.api_key or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "REDMINE_USER_ID": 
                current_value = self.config.redmine.user_id or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "DEFAULT_REDMINE_ACTIVITY_ID": 
                current_value = str(self.config.default_redmine_activity_id or "")
                if self.config.default_redmine_activity_id:
                    try:
                        redmine = RedmineClient(
                            base_url=self.config.redmine.base_url or "",
                            api_key=self.config.redmine.api_key or "",
                        )
                        acts = redmine.list_time_entry_activities()
                        matching = next((a for a in acts if a.id == self.config.default_redmine_activity_id), None)
                        if matching:
                            display_hint = f" ({matching.name})"
                    except Exception:
                        pass
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                self.console.print("[dim]Tip: You can find Activity IDs in Redmine Enumerations or by running 'redmine log' and seeing the IDs in the list.[/dim]")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "NOTION_API_TOKEN":
                current_value = self.config.notion.api_token or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "NOTION_TASKS_DATABASE_ID":
                current_value = self.config.notion.tasks_database_id or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "NOTION_PROJECTS_DATABASE_ID":
                current_value = self.config.notion.projects_database_id or ""
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "NOTION_PROJECT_NAMES":
                current_value = ",".join(self.config.notion.project_names)
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "NOTION_DONE_STATUS_NAME":
                current_value = self.config.notion.done_status_name
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "SALARY_PER_HOUR": 
                current_value = str(self.config.salary_per_hour or "")
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            elif key == "SALARY_CURRENCY": 
                current_value = self.config.salary_currency
                self.console.print(f"Current value for [bold]{key}[/bold]: {current_value}{display_hint}")
                new_value = ask_text(f"Enter new value for {key}", default=current_value)
            
            if new_value == current_value:
                self.console.print("[yellow]No change made.[/yellow]")
                continue
                
            persist_env_value(self.workspace_root / ".env", key, new_value)
            self.console.print(f"[green]Saved {key}={new_value} to .env[/green]")
            
            # Reload config in memory
            self.config = load_config(self.workspace_root, self.current_dir)
            
        return 0

    def run_hours_command(self) -> int:
        self._render_banner_once()
        year, month = select_month(date.today())
        date_from, date_to = month_to_date_range(year, month)
        
        self.console.print(f"[cyan]Fetching hours for {year}-{month:02d}...[/cyan]")
        entries = get_time_entries(
            self.config.redmine.base_url or "",
            self.config.redmine.api_key or "",
            self.config.redmine.user_id or "me",
            date_from,
            date_to,
        )
        days = aggregate_hours_by_day(entries)
        show_hours_summary(
            self.console,
            year,
            month,
            days,
            salary_per_hour=self.config.salary_per_hour,
            currency=self.config.salary_currency,
        )
        return 0

    def run_log_command(self) -> int:
        self._render_banner_once()
        redmine = RedmineClient(
            base_url=self.config.redmine.base_url or "",
            api_key=self.config.redmine.api_key or "",
            user_agent=self.config.redmine.http_user_agent,
        )
        projects = redmine.list_projects()
        project = choose_redmine_project(projects)
        
        self.console.print(f"[cyan]Loading issues for project {project.name}...[/cyan]")
        all_issues = redmine.list_issues(project.id)
        if not all_issues:
            raise RuntimeError(f"No issues found in project {project.name}.")
        
        issue = choose_issue_from_list(all_issues)
        activities = redmine.list_time_entry_activities()
        
        hours = int(ask_text("Hours", default="0"))
        minutes = ask_minutes("Minutes", default="0")
        activity = choose_redmine_activity(activities, self.config.default_redmine_activity_id)
        comments = ask_text("Comment", default="")
        spent_on = ask_text("Spent date (YYYY-MM-DD)", default=date.today().isoformat())
        
        total_hours = round(hours + (minutes / 60), 2)
        
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"Issue:  #{issue.id} {issue.subject}")
        self.console.print(f"Time:   {total_hours:.2f}h on {spent_on}")
        self.console.print(f"Type:   {activity.name}")
        self.console.print(f"Note:   {comments}")
        
        if not ask_confirm("Create this time entry?", default=True):
            self.console.print("[yellow]Cancelled.[/yellow]")
            return 0
            
        created = redmine.create_time_entry(
            issue_id=issue.id,
            hours=total_hours,
            spent_on=spent_on,
            activity_id=activity.id,
            comments=comments,
        )
        self.console.print(f"[green]Success! Created time entry #{created['id']}.[/green]")
        return 0

    def run_issue_new_command(self) -> int:
        self._render_banner_once()
        redmine = RedmineClient(
            base_url=self.config.redmine.base_url or "",
            api_key=self.config.redmine.api_key or "",
            user_agent=self.config.redmine.http_user_agent,
        )
        projects = redmine.list_projects()
        project = choose_redmine_project(projects)
        
        target = choose_issue_creation_target()
        parent_issue = None
        if target != CREATE_AT_PROJECT_ROOT:
            self.console.print(f"[cyan]Loading issues for project {project.name}...[/cyan]")
            all_issues = redmine.list_issues(project.id)
            top_level = [i for i in all_issues if i.parent_id is None]
            parent_issue = self._descend_issue_tree(top_level, all_issues)
            
        trackers = redmine.list_trackers()
        tracker = choose_redmine_tracker(trackers)
        subject = ask_text("Issue name / Subject")
        if not subject:
            self.console.print("[red]Subject cannot be empty.[/red]")
            return 1
            
        created_issue = redmine.create_issue(
            project_id=project.id,
            subject=subject,
            description=subject,
            tracker_id=tracker.id,
            parent_issue_id=parent_issue.id if parent_issue else None,
        )
        self.console.print(f"[green]Success! Created issue #{created_issue.id}: {created_issue.subject}[/green]")
        
        if ask_confirm("Would you like to log time to this new issue immediately?", default=True):
            activities = redmine.list_time_entry_activities()
            hours = int(ask_text("Hours", default="0"))
            minutes = ask_minutes("Minutes", default="0")
            activity = choose_redmine_activity(activities, self.config.default_redmine_activity_id)
            comments = ask_text("Comment", default="")
            spent_on = ask_text("Spent date (YYYY-MM-DD)", default=date.today().isoformat())
            total_hours = round(hours + (minutes / 60), 2)
            
            created_entry = redmine.create_time_entry(
                issue_id=created_issue.id,
                hours=total_hours,
                spent_on=spent_on,
                activity_id=activity.id,
                comments=comments,
            )
            self.console.print(f"[green]Success! Created time entry #{created_entry['id']}.[/green]")
            
        return 0

    def run_doctor(self) -> int:
        rows = [
            ("Workspace root", str(self.workspace_root)),
            ("REDMINE_BASE_URL", "set" if self.config.redmine.base_url else "missing"),
            ("REDMINE_API_KEY", "set" if self.config.redmine.api_key else "missing"),
            ("REDMINE_USER_ID", "set" if self.config.redmine.user_id else "missing"),
            ("NOTION_API_TOKEN", "set" if self.config.notion.api_token else "missing"),
            ("NOTION_TASKS_DATABASE_ID", self.config.notion.tasks_database_id or "missing"),
            ("NOTION_PROJECTS_DATABASE_ID", self.config.notion.projects_database_id or "missing"),
            (
                "NOTION_PROJECT_NAMES",
                ", ".join(self.config.notion.project_names) if self.config.notion.project_names else "not set",
            ),
            ("NOTION_WORK_PRIVATE_SCOPE", self.config.notion.work_private_scope or "not set"),
            ("Excel input", self.config.timetable.excel_in),
            ("Excel output", self.config.timetable.excel_out),
            ("PDF output", self.config.timetable.pdf_out),
        ]
        self._render_banner_once()
        show_doctor(self.console, rows)
        return 0

    def run_timetable_command(self) -> int:
        self._render_banner_once()
        year, month = select_month(date.today())
        date_from, date_to = month_to_date_range(year, month)
        pdf_out = ask_path("PDF output file", f"filled-{year:04d}-{month:02d}.pdf")
        excel_out = ask_path("Excel output file", f"filled-{year:04d}-{month:02d}.xlsx")
        result = run_timetable(self.config, date_from=date_from, date_to=date_to, pdf_out=pdf_out, excel_out=excel_out)
        show_timetable_result(self.console, result)
        return 0

    def run_upload_command(self) -> int:
        self._render_banner_once()
        self._ensure_notion_token()
        self._ensure_upload_config()

        notion = NotionClient(
            api_token=self.config.notion.api_token or "",
            tasks_database_id=self.config.notion.tasks_database_id or "",
            projects_database_id=self.config.notion.projects_database_id,
        )

        work_private_scope = choose_work_private_scope(self.config.notion.work_private_scope)
        available_notion_projects = notion.list_project_names(work_private_scope=work_private_scope)
        preferred_project = self.config.notion.project_names[0] if self.config.notion.project_names else None
        chosen_notion_project = choose_notion_project_name(available_notion_projects, default_value=preferred_project)

        redmine = RedmineClient(
            base_url=self.config.redmine.base_url or "",
            api_key=self.config.redmine.api_key or "",
            user_agent=self.config.redmine.http_user_agent,
        )
        projects = redmine.list_projects()
        activities = redmine.list_time_entry_activities()
        trackers = redmine.list_trackers()
        if not activities:
            raise RuntimeError("No Redmine time-entry activities were found.")
        if not trackers:
            raise RuntimeError("No Redmine trackers were found.")
        redmine_project = choose_redmine_project(projects)
        issue_creation_target = choose_issue_creation_target()
        selected_parent_issue = None
        if issue_creation_target != CREATE_AT_PROJECT_ROOT:
            all_issues = redmine.list_issues(redmine_project.id)
            top_level_issues = [issue for issue in all_issues if issue.parent_id is None]
            if not top_level_issues:
                raise RuntimeError("No Redmine issues were found for the selected project.")
            selected_parent_issue = self._descend_issue_tree(top_level_issues, all_issues)

        self.console.print("[cyan]Loading tasks from Notion...[/cyan]")
        tasks = notion.list_done_tasks(
            done_status_name=self.config.notion.done_status_name,
            project_names=[chosen_notion_project] if chosen_notion_project else [],
            work_private_scope=work_private_scope,
        )
        if not tasks:
            self.console.print(
                Panel(
                    "No matching Done tasks were found in Notion.\n"
                    "Check project filters, Work / Private scope, or Done status naming.",
                    title="Nothing to upload",
                    border_style="yellow",
                )
            )
            return 0

        planned_entries: list[dict] = []
        default_spent_on = date.today().isoformat()

        for task in tasks:
            self.console.print(f"[bold]Done task:[/bold] {task.title}")
            if not ask_confirm("Create a Redmine issue and log time from this task?", default=True):
                continue

            tracker = choose_redmine_tracker(trackers)
            percent_done = ask_percent_done("Percent done", default="100%")
            hours = int(ask_text("Hours", default="0"))
            minutes = ask_minutes("Minutes", default="0")
            activity = choose_redmine_activity(activities, self.config.default_redmine_activity_id)
            comments = ask_text("Comment", default="")
            spent_on = ask_text("Spent date (YYYY-MM-DD)", default=default_spent_on)
            total_hours = round(hours + (minutes / 60), 2)
            planned_entries.append(
                {
                    "task": task,
                    "tracker": tracker,
                    "parent_issue": selected_parent_issue,
                    "percent_done": percent_done,
                    "hours": total_hours,
                    "activity": activity,
                    "spent_on": spent_on,
                    "comments": comments,
                }
            )

        if not planned_entries:
            self.console.print("[yellow]No time entries were selected.[/yellow]")
            return 0

        show_upload_summary(
            self.console,
            [
                (
                    entry["task"].title,
                    (
                        f"new {entry['tracker'].name} ({entry['percent_done']}%) under #{entry['parent_issue'].id} {entry['parent_issue'].subject}"
                        if entry["parent_issue"] is not None
                        else f"new {entry['tracker'].name} ({entry['percent_done']}%) in project {redmine_project.name}"
                    ),
                    f"{entry['hours']:.2f}h on {entry['spent_on']} [{entry['activity'].name}]",
                )
                for entry in planned_entries
            ],
        )
        if not ask_confirm("Create these Redmine time entries?", default=True):
            self.console.print("[yellow]Upload cancelled before writing anything.[/yellow]")
            return 0

        for entry_plan in planned_entries:
            created_issue = redmine.create_issue(
                project_id=redmine_project.id,
                subject=entry_plan["task"].title,
                description=entry_plan["task"].title,
                tracker_id=entry_plan["tracker"].id,
                parent_issue_id=entry_plan["parent_issue"].id if entry_plan["parent_issue"] is not None else None,
                done_ratio=entry_plan["percent_done"],
            )
            created_entry = redmine.create_time_entry(
                issue_id=created_issue.id,
                hours=entry_plan["hours"],
                spent_on=entry_plan["spent_on"],
                activity_id=entry_plan["activity"].id,
                comments=entry_plan["comments"],
            )
            notion.archive_task(entry_plan["task"].id)
            self.console.print(
                Panel(
                    f"Created Redmine issue #{created_issue.id}: {created_issue.subject}\n"
                    f"Created Redmine time entry #{created_entry['id']} on issue #{created_issue.id}\n"
                    f"Archived Notion task: {entry_plan['task'].title}\n"
                    f"Task: {entry_plan['task'].title}\n"
                    f"Hours: {entry_plan['hours']:.2f}\n"
                    f"Activity: {entry_plan['activity'].name}",
                    title="Upload success",
                    border_style="green",
                )
            )

        return 0

    def _descend_issue_tree(self, top_level_issues, all_issues):
        current_issue = choose_top_level_issue(top_level_issues)
        while True:
            children = [issue for issue in all_issues if issue.parent_id == current_issue.id]
            if not children:
                return current_issue
            next_issue = choose_issue_or_descend(current_issue, children)
            if next_issue is None:
                return current_issue
            current_issue = next_issue

    def _ensure_upload_config(self) -> None:
        missing = []
        if not self.config.redmine.base_url:
            missing.append("REDMINE_BASE_URL")
        if not self.config.redmine.api_key:
            missing.append("REDMINE_API_KEY")
        if not self.config.notion.tasks_database_id:
            missing.append("NOTION_TASKS_DATABASE_ID")
        if not self.config.notion.projects_database_id:
            missing.append("NOTION_PROJECTS_DATABASE_ID")
        if missing:
            raise RuntimeError("Missing upload config: " + ", ".join(missing))

    def _render_banner_once(self) -> None:
        if self._banner_rendered:
            return
        render_banner(self.console)
        self._banner_rendered = True

    def _ensure_notion_token(self) -> None:
        if self.config.notion.api_token:
            return

        self.console.print(
            Panel(
                "A Notion uploadhoz meg kell adni egy official Notion integration tokent.\n"
                "Most be tudod irni interaktivan, es el is tudom menteni a helyi .env-be.",
                title="Notion token required",
                border_style="yellow",
            )
        )
        token = ask_secret("Notion API token")
        if not token:
            raise RuntimeError("Missing NOTION_API_TOKEN.")

        if ask_confirm("Save this token into the local .env for later runs?", default=True):
            persist_env_value(self.workspace_root / ".env", "NOTION_API_TOKEN", token)
        self.config.notion.api_token = token


def main(argv: list[str] | None = None) -> int:
    app = CliApp()
    return app.run(list(sys.argv[1:] if argv is None else argv))

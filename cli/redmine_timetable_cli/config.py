from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def csv_env(name: str) -> list[str]:
    value = os.getenv(name, "").strip()
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name, "")
    if not value:
        return default
    return value.strip().lower() not in {"0", "false", "no"}


@dataclass(slots=True)
class RedmineConfig:
    base_url: str | None
    api_key: str | None
    user_id: str | None
    http_user_agent: str
    use_curl: bool


@dataclass(slots=True)
class TimetableConfig:
    excel_in: str
    excel_out: str
    sheet_name: str
    arrival_time: str
    pdf_out: str
    print_area: str
    allow_libreoffice_fallback_on_windows: bool


@dataclass(slots=True)
class NotionConfig:
    api_token: str | None
    tasks_database_id: str | None
    projects_database_id: str | None
    done_status_name: str
    project_names: list[str]
    work_private_scope: str | None
    uploaded_flag_property: str | None
    redmine_issue_property: str | None


@dataclass(slots=True)
class AppConfig:
    workspace_root: Path
    current_dir: Path
    redmine: RedmineConfig
    timetable: TimetableConfig
    notion: NotionConfig
    default_redmine_activity_id: int | None
    salary_per_hour: float | None
    salary_currency: str


def set_env_value(name: str, value: str) -> None:
    os.environ[name] = value


def persist_env_value(env_path: Path, name: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated = False
    new_lines: list[str] = []

    for line in lines:
        if line.strip().startswith(f"{name}="):
            new_lines.append(f"{name}={value}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        if new_lines and new_lines[-1].strip():
            new_lines.append("")
        new_lines.append(f"{name}={value}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    os.environ[name] = value


def load_config(workspace_root: Path, current_dir: Path) -> AppConfig:
    load_env_file(workspace_root / ".env")

    default_activity = optional_env("DEFAULT_REDMINE_ACTIVITY_ID")
    activity_id = int(default_activity) if default_activity else None

    salary_per_hour_raw = optional_env("SALARY_PER_HOUR")
    salary_per_hour = float(salary_per_hour_raw) if salary_per_hour_raw else None

    return AppConfig(
        workspace_root=workspace_root,
        current_dir=current_dir,
        redmine=RedmineConfig(
            base_url=optional_env("REDMINE_BASE_URL"),
            api_key=optional_env("REDMINE_API_KEY"),
            user_id=optional_env("REDMINE_USER_ID"),
            http_user_agent=os.getenv("HTTP_USER_AGENT", "redmine-timetable-cli/2.0"),
            use_curl=bool_env("USE_CURL", True),
        ),
        timetable=TimetableConfig(
            excel_in=os.getenv("EXCEL_IN", "unfilled.xlsx"),
            excel_out=os.getenv("EXCEL_OUT", "filled.xlsx"),
            sheet_name=os.getenv("SHEET_NAME", "Munka1"),
            arrival_time=os.getenv("ARRIVAL_TIME", "09:00"),
            pdf_out=os.getenv("PDF_OUT", "filled.pdf"),
            print_area=os.getenv("PRINT_AREA", "A1:F47"),
            allow_libreoffice_fallback_on_windows=bool_env(
                "ALLOW_LIBREOFFICE_FALLBACK_ON_WINDOWS", False
            ),
        ),
        notion=NotionConfig(
            api_token=optional_env("NOTION_API_TOKEN"),
            tasks_database_id=optional_env("NOTION_TASKS_DATABASE_ID"),
            projects_database_id=optional_env("NOTION_PROJECTS_DATABASE_ID"),
            done_status_name=os.getenv("NOTION_DONE_STATUS_NAME", "Done"),
            project_names=csv_env("NOTION_PROJECT_NAMES"),
            work_private_scope=optional_env("NOTION_WORK_PRIVATE_SCOPE"),
            uploaded_flag_property=optional_env("NOTION_UPLOADED_FLAG_PROPERTY"),
            redmine_issue_property=optional_env("NOTION_REDMINE_ISSUE_PROPERTY"),
        ),
        default_redmine_activity_id=activity_id,
        salary_per_hour=salary_per_hour,
        salary_currency=os.getenv("SALARY_CURRENCY", "HUF"),
    )

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TimetableRunResult:
    excel_path: str
    pdf_path: str
    pdf_engine: str
    date_from: str
    date_to: str
    print_area: str
    fetched_entries: int
    filled_workdays: int


@dataclass(slots=True)
class NotionTask:
    id: str
    title: str
    status: str
    project_names: list[str]
    work_private: str | None
    body: str


@dataclass(slots=True)
class RedmineProject:
    id: int
    name: str
    identifier: str | None


@dataclass(slots=True)
class RedmineTracker:
    id: int
    name: str


@dataclass(slots=True)
class RedmineActivity:
    id: int
    name: str
    is_default: bool = False


@dataclass(slots=True)
class RedmineIssue:
    id: int
    subject: str
    status_name: str | None
    parent_id: int | None = None

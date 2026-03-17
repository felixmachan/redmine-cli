from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import requests

from ..models import NotionTask

NOTION_VERSION = "2022-06-28"


def _rich_text_to_plain(items: list[dict]) -> str:
    return "".join(item.get("plain_text", "") for item in items or [])


def _property_to_plain(prop: dict) -> str:
    prop_type = prop.get("type")
    if prop_type == "title":
        return _rich_text_to_plain(prop.get("title", []))
    if prop_type == "rich_text":
        return _rich_text_to_plain(prop.get("rich_text", []))
    if prop_type == "status":
        status = prop.get("status")
        return status.get("name", "") if status else ""
    if prop_type == "select":
        option = prop.get("select")
        return option.get("name", "") if option else ""
    return ""


@dataclass(slots=True)
class NotionClient:
    api_token: str
    tasks_database_id: str
    projects_database_id: str | None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def _post(self, path: str, payload: dict) -> dict:
        response = requests.post(
            f"https://api.notion.com/v1{path}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, path: str) -> dict:
        response = requests.get(f"https://api.notion.com/v1{path}", headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def _patch(self, path: str, payload: dict) -> dict:
        response = requests.patch(
            f"https://api.notion.com/v1{path}",
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def resolve_project_ids(self, project_names: list[str]) -> dict[str, str]:
        if not project_names or not self.projects_database_id:
            return {}

        payload = {"page_size": 100}
        results = self._post(f"/databases/{self.projects_database_id}/query", payload).get("results", [])
        mapping: dict[str, str] = {}
        for item in results:
            name = _property_to_plain(item.get("properties", {}).get("Name", {})).strip()
            if name:
                mapping[name.lower()] = item["id"]

        resolved: dict[str, str] = {}
        for name in project_names:
            page_id = mapping.get(name.lower())
            if page_id:
                resolved[name] = page_id
        return resolved

    def list_project_names(self, work_private_scope: str | None = None) -> list[str]:
        if not self.projects_database_id:
            return []

        payload: dict = {"page_size": 100}
        normalized_scope = (work_private_scope or "").strip()
        if normalized_scope:
            payload["filter"] = {"property": "Work/Private", "select": {"equals": normalized_scope}}

        results = self._post(f"/databases/{self.projects_database_id}/query", payload).get("results", [])
        names = []
        for item in results:
            name = _property_to_plain(item.get("properties", {}).get("Name", {})).strip()
            if name:
                names.append(name)
        return sorted(set(names), key=str.lower)

    def list_done_tasks(
        self,
        done_status_name: str,
        project_names: list[str],
        work_private_scope: str | None,
    ) -> list[NotionTask]:
        filters: list[dict] = [{"property": "Status", "status": {"equals": done_status_name}}]
        normalized_scope = (work_private_scope or "").strip()
        if normalized_scope:
            filters.append({"property": "Work / Private", "select": {"equals": normalized_scope}})

        project_ids = self.resolve_project_ids(project_names)
        if project_ids:
            filters.append(
                {
                    "or": [
                        {"property": "Project", "relation": {"contains": project_id}}
                        for project_id in project_ids.values()
                    ]
                }
            )

        query_payload: dict = {"page_size": 100}
        if len(filters) == 1:
            query_payload["filter"] = filters[0]
        else:
            query_payload["filter"] = {"and": filters}

        results = self._post(f"/databases/{self.tasks_database_id}/query", query_payload).get("results", [])
        tasks: list[NotionTask] = []
        for item in results:
            properties = item.get("properties", {})
            title = _property_to_plain(properties.get("Project name", {})).strip() or "Untitled task"
            status = _property_to_plain(properties.get("Status", {})).strip()
            work_private = _property_to_plain(properties.get("Work / Private", {})).strip() or None
            relation_pages = properties.get("Project", {}).get("relation", [])
            relation_ids = {page["id"] for page in relation_pages}
            matched_names = [name for name, page_id in project_ids.items() if page_id in relation_ids]
            body = self.get_page_body(item["id"])
            tasks.append(
                NotionTask(
                    id=item["id"],
                    title=title,
                    status=status,
                    project_names=matched_names,
                    work_private=work_private,
                    body=body,
                )
            )
        return tasks

    def get_page_body(self, page_id: str) -> str:
        lines: list[str] = []
        self._collect_block_lines(page_id, lines, depth=0)
        return "\n".join(lines).strip()

    def archive_task(self, page_id: str) -> None:
        self._patch(
            f"/pages/{page_id}",
            {
                "properties": {
                    "Status": {"status": {"name": "Archived"}},
                    "Done at": {"date": {"start": date.today().isoformat()}},
                }
            },
        )

    def _collect_block_lines(self, block_id: str, lines: list[str], depth: int) -> None:
        cursor = None
        while True:
            suffix = f"?page_size=100&start_cursor={cursor}" if cursor else "?page_size=100"
            payload = self._get(f"/blocks/{block_id}/children{suffix}")
            for block in payload.get("results", []):
                block_type = block.get("type")
                content = block.get(block_type, {})
                plain = _rich_text_to_plain(content.get("rich_text", [])).strip()
                prefix = "  " * depth
                if block_type in {"heading_1", "heading_2", "heading_3"} and plain:
                    lines.append(f"{prefix}{plain}")
                elif block_type in {"paragraph", "bulleted_list_item", "numbered_list_item", "to_do"} and plain:
                    marker = "- " if block_type in {"bulleted_list_item", "to_do"} else ""
                    lines.append(f"{prefix}{marker}{plain}")
                if block.get("has_children"):
                    self._collect_block_lines(block["id"], lines, depth + 1)
            if not payload.get("has_more"):
                break
            cursor = payload.get("next_cursor")

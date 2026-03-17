from __future__ import annotations

from dataclasses import dataclass

import requests
from requests import HTTPError

from ..models import RedmineActivity, RedmineIssue, RedmineProject, RedmineTracker


@dataclass(slots=True)
class RedmineClient:
    base_url: str
    api_key: str
    user_agent: str

    def _headers(self) -> dict[str, str]:
        return {
            "X-Redmine-API-Key": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": self.user_agent,
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def list_projects(self) -> list[RedmineProject]:
        response = requests.get(self._url("/projects.json"), headers=self._headers(), timeout=30)
        response.raise_for_status()
        projects = response.json().get("projects", [])
        return [
            RedmineProject(id=int(item["id"]), name=item["name"], identifier=item.get("identifier"))
            for item in projects
        ]

    def list_time_entry_activities(self) -> list[RedmineActivity]:
        response = requests.get(self._url("/enumerations/time_entry_activities.json"), headers=self._headers(), timeout=30)
        response.raise_for_status()
        activities = response.json().get("time_entry_activities", [])
        return [
            RedmineActivity(
                id=int(item["id"]),
                name=item["name"],
                is_default=bool(item.get("is_default", False)),
            )
            for item in activities
            if item.get("active", True)
        ]

    def list_trackers(self) -> list[RedmineTracker]:
        response = requests.get(self._url("/trackers.json"), headers=self._headers(), timeout=30)
        response.raise_for_status()
        trackers = response.json().get("trackers", [])
        return [RedmineTracker(id=int(item["id"]), name=item["name"]) for item in trackers]

    def list_issues(self, project_id: int, limit: int = 100) -> list[RedmineIssue]:
        issues: list[RedmineIssue] = []
        offset = 0

        while True:
            batch_response = requests.get(
                self._url("/issues.json"),
                headers=self._headers(),
                params={"project_id": project_id, "limit": limit, "offset": offset, "sort": "updated_on:desc"},
                timeout=30,
            )
            batch_response.raise_for_status()
            payload = batch_response.json()
            batch = payload.get("issues", [])
            for item in batch:
                parent = item.get("parent") or {}
                issues.append(
                    RedmineIssue(
                        id=int(item["id"]),
                        subject=item["subject"],
                        status_name=(item.get("status") or {}).get("name"),
                        parent_id=int(parent["id"]) if parent.get("id") is not None else None,
                    )
                )
            offset += len(batch)
            total_count = int(payload.get("total_count", len(issues)))
            if not batch or offset >= total_count:
                break

        return issues

    def create_issue(
        self,
        project_id: int,
        subject: str,
        description: str,
        tracker_id: int | None = None,
        parent_issue_id: int | None = None,
        done_ratio: int | None = None,
    ) -> RedmineIssue:
        payload = {"issue": {"project_id": project_id, "subject": subject, "description": description}}
        if tracker_id is not None:
            payload["issue"]["tracker_id"] = tracker_id
        if parent_issue_id is not None:
            payload["issue"]["parent_issue_id"] = parent_issue_id
        if done_ratio is not None:
            payload["issue"]["done_ratio"] = done_ratio
        response = requests.post(self._url("/issues.json"), headers=self._headers(), json=payload, timeout=30)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            body = response.text.strip()
            raise RuntimeError(
                "Redmine rejected the issue creation.\n"
                f"HTTP {response.status_code}: {body or '<no response body>'}\n"
                f"Payload: {payload}"
            ) from exc
        issue = response.json()["issue"]
        return RedmineIssue(
            id=int(issue["id"]),
            subject=issue["subject"],
            status_name=(issue.get("status") or {}).get("name"),
        )

    def create_time_entry(
        self,
        issue_id: int,
        hours: float,
        spent_on: str,
        activity_id: int | None,
        comments: str,
    ) -> dict:
        payload = {
            "time_entry": {
                "issue_id": issue_id,
                "hours": hours,
                "spent_on": spent_on,
                "comments": comments,
            }
        }
        if activity_id is not None:
            payload["time_entry"]["activity_id"] = activity_id
        response = requests.post(self._url("/time_entries.json"), headers=self._headers(), json=payload, timeout=30)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            body = response.text.strip()
            raise RuntimeError(
                "Redmine rejected the time entry.\n"
                f"HTTP {response.status_code}: {body or '<no response body>'}\n"
                f"Payload: {payload}"
            ) from exc
        return response.json()["time_entry"]

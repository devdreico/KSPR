"""KSPR Autonomous Cognitive OS: Task Graph & To-Do Engine."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class TaskEngine:
    def __init__(self, workspace_path: Path | None = None):
        self.workspace_path = workspace_path or Path.cwd()
        self.tasks_file = self.workspace_path / ".kspr_tasks.json"
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> list[dict[str, Any]]:
        if self.tasks_file.is_file():
            try:
                return json.loads(self.tasks_file.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def save_tasks(self) -> None:
        try:
            self.tasks_file.parent.mkdir(parents=True, exist_ok=True)
            self.tasks_file.write_text(json.dumps(self.tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[!] Error guardando tareas: {e}")

    def add_task(self, title: str, priority: str = "medium") -> dict[str, Any]:
        task = {
            "id": f"task_{int(time.time() * 1000)}",
            "title": title,
            "status": "pending", # pending, in_progress, completed
            "priority": priority
        }
        self.tasks.append(task)
        self.save_tasks()
        return task

    def update_status(self, task_id: str, status: str) -> bool:
        for t in self.tasks:
            if t["id"] == task_id or t["title"].lower() == task_id.lower():
                t["status"] = status
                self.save_tasks()
                return True
        return False

    def list_tasks(self) -> list[dict[str, Any]]:
        return self.tasks

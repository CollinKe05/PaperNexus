from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Literal

from backend.models import AnalysisResult, AnalysisTaskStatusResponse


TaskStatus = Literal["queued", "running", "completed", "failed"]


@dataclass
class AnalysisTaskRecord:
    task_id: str
    status: TaskStatus = "queued"
    stage: str = "queued"
    progress: float = 0.0
    message: str = "Task queued."
    quick_mode: bool = False
    result: AnalysisResult | None = None
    error: str | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def to_response(self) -> AnalysisTaskStatusResponse:
        return AnalysisTaskStatusResponse(
            taskId=self.task_id,
            status=self.status,
            stage=self.stage,
            progress=self.progress,
            message=self.message,
            quickMode=self.quick_mode,
            result=self.result,
            error=self.error,
        )


class AnalysisTaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, AnalysisTaskRecord] = {}

    def create(self, quick_mode: bool) -> AnalysisTaskRecord:
        task = AnalysisTaskRecord(task_id=uuid.uuid4().hex, quick_mode=quick_mode)
        self._tasks[task.task_id] = task
        return task

    def get(self, task_id: str) -> AnalysisTaskRecord | None:
        return self._tasks.get(task_id)

    async def update(
        self,
        task_id: str,
        *,
        status: TaskStatus | None = None,
        stage: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        result: AnalysisResult | None = None,
        error: str | None = None,
    ) -> AnalysisTaskRecord:
        task = self._tasks[task_id]
        async with task.lock:
            if status is not None:
                task.status = status
            if stage is not None:
                task.stage = stage
            if progress is not None:
                task.progress = max(0.0, min(1.0, progress))
            if message is not None:
                task.message = message
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
        return task

"""
IT Tasks Integration (Mock)

IT task/ticketing system for provisioning, equipment, access management.
"""

import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ITTask:
    task_id: str
    title: str
    description: str
    assignee: str
    due_date: str | None
    status: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ITTaskResponse:
    success: bool
    task: ITTask | None = None
    error: str | None = None


class ITTasksError(Exception):
    """Raised when IT Tasks operation fails."""
    pass


class ITTasksClient:
    """
    Mock IT Tasks client.
    
    Args:
        failure_rate: Probability of random failure (0.0 to 1.0)
    """
    
    def __init__(self, failure_rate: float = 0.0):
        self.failure_rate = failure_rate
        self._tasks: dict[str, ITTask] = {}
    
    def _maybe_fail(self):
        if random.random() < self.failure_rate:
            raise ITTasksError("IT Tasks service temporarily unavailable")
    
    def create_task(
        self,
        title: str,
        description: str,
        assignee: str = "it-team@company.com",
        due_date: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ITTaskResponse:
        """
        Create a new IT task.
        
        Args:
            title: Task title
            description: Task description
            assignee: Who should handle this (default: IT team)
            due_date: Due date as string (e.g., "2025-01-25")
            metadata: Additional data to attach to the task
            
        Returns:
            ITTaskResponse with created task
        """
        self._maybe_fail()
        
        if not title:
            return ITTaskResponse(success=False, error="Title is required")
        
        task_id = f"IT-{uuid.uuid4().hex[:6].upper()}"
        
        task = ITTask(
            task_id=task_id,
            title=title,
            description=description,
            assignee=assignee,
            due_date=due_date,
            status="open",
            created_at=datetime.utcnow().isoformat(),
            metadata=metadata or {},
        )
        
        self._tasks[task_id] = task
        return ITTaskResponse(success=True, task=task)
    
    def get_task(self, task_id: str) -> ITTaskResponse:
        """Get a task by ID."""
        self._maybe_fail()
        
        task = self._tasks.get(task_id)
        if task:
            return ITTaskResponse(success=True, task=task)
        return ITTaskResponse(success=False, error=f"Task not found: {task_id}")
    
    def update_task(self, task_id: str, updates: dict[str, Any]) -> ITTaskResponse:
        """Update a task."""
        self._maybe_fail()
        
        if task_id not in self._tasks:
            return ITTaskResponse(success=False, error=f"Task not found: {task_id}")
        
        task = self._tasks[task_id]
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        return ITTaskResponse(success=True, task=task)
    
    def find_tasks(self, **filters) -> list[ITTask]:
        """
        Find tasks matching filters.
        
        Example: find_tasks(assignee="it-team@company.com", status="open")
        """
        self._maybe_fail()
        
        results = []
        for task in self._tasks.values():
            match = True
            for key, value in filters.items():
                if getattr(task, key, None) != value:
                    match = False
                    break
            if match:
                results.append(task)
        
        return results
    
    def find_task_by_metadata(self, key: str, value: Any) -> ITTask | None:
        """Find a task by metadata field (useful for idempotency checks)."""
        self._maybe_fail()
        
        for task in self._tasks.values():
            if task.metadata.get(key) == value:
                return task
        return None

"""Tests for Task data model."""

import pytest
from pydantic import ValidationError

from qbench.task import Task


def test_task_creation():
    """Test basic task creation."""
    task = Task(
        id="task1",
        arrival_time=0,
        priority="urgent",
        deadline=10,
    )
    assert task.id == "task1"
    assert task.arrival_time == 0
    assert task.priority == "urgent"
    assert task.deadline == 10
    assert task.status == "pending"
    assert task.scheduled_slot is None
    assert task.completed_time is None


def test_task_with_all_fields():
    """Test task with all fields populated."""
    task = Task(
        id="task2",
        arrival_time=5,
        priority="routine",
        deadline=20,
        status="completed",
        scheduled_slot=15,
        completed_time=15,
    )
    assert task.status == "completed"
    assert task.scheduled_slot == 15
    assert task.completed_time == 15


def test_task_priority_validation():
    """Test that priority must be 'urgent' or 'routine'."""
    with pytest.raises(ValidationError):
        Task(
            id="task3",
            arrival_time=0,
            priority="high",  # Invalid priority
            deadline=10,
        )


def test_task_status_validation():
    """Test that status must be one of allowed values."""
    with pytest.raises(ValidationError):
        Task(
            id="task4",
            arrival_time=0,
            priority="urgent",
            deadline=10,
            status="invalid_status",
        )


def test_task_negative_time_validation():
    """Test that negative times are rejected."""
    with pytest.raises(ValidationError):
        Task(
            id="task5",
            arrival_time=-1,
            priority="urgent",
            deadline=10,
        )


def test_task_string_representation():
    """Test task string representation."""
    task = Task(
        id="task6",
        arrival_time=0,
        priority="urgent",
        deadline=10,
    )
    str_repr = str(task)
    assert "task6" in str_repr
    assert "urgent" in str_repr
    assert "deadline=10" in str_repr

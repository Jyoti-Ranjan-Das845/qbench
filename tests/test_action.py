"""Tests for Action data model."""

import pytest
from pydantic import ValidationError

from qbench.action import Action


def test_schedule_action():
    """Test schedule action creation."""
    action = Action(type="schedule", task_id="task1", step=5, slot_index=0)
    assert action.type == "schedule"
    assert action.task_id == "task1"
    assert action.step == 5
    assert action.slot_index == 0


def test_reschedule_action():
    """Test reschedule action creation."""
    action = Action(type="reschedule", task_id="task2", step=10)
    assert action.type == "reschedule"
    assert action.task_id == "task2"
    assert action.step == 10


def test_reject_action():
    """Test reject action creation."""
    action = Action(type="reject", task_id="task3")
    assert action.type == "reject"
    assert action.task_id == "task3"
    assert action.step is None


def test_cancel_action():
    """Test cancel action creation."""
    action = Action(type="cancel", task_id="task4")
    assert action.type == "cancel"
    assert action.task_id == "task4"


def test_noop_action():
    """Test noop action creation."""
    action = Action(type="noop")
    assert action.type == "noop"
    assert action.task_id is None
    assert action.step is None


def test_invalid_action_type():
    """Test that invalid action type is rejected."""
    with pytest.raises(ValidationError):
        Action(type="invalid")


def test_negative_step_validation():
    """Test that negative step is rejected."""
    with pytest.raises(ValidationError):
        Action(type="schedule", task_id="task5", step=-1)


def test_action_string_representation():
    """Test action string representations."""
    noop = Action(type="noop")
    assert "noop" in str(noop)

    schedule = Action(type="schedule", task_id="task1", step=5)
    assert "schedule" in str(schedule)
    assert "task1" in str(schedule)
    assert "5" in str(schedule)

    reject = Action(type="reject", task_id="task2")
    assert "reject" in str(reject)
    assert "task2" in str(reject)

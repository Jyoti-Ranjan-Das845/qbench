"""Tests for QueueEnv."""

import pytest

from qbench.data_models.action import Action
from qbench.environment.env import QueueEnv
from qbench.environment.loader import SeedConfig


@pytest.fixture
def simple_config():
    """Create a simple seed config for testing."""
    return SeedConfig(
        horizon=10,
        capacity_per_step=2,
        events={
            "0": [
                {
                    "type": "arrival",
                    "task": {
                        "id": "u1",
                        "arrival_time": 0,
                        "priority": "urgent",
                        "deadline": 5,
                    },
                },
                {
                    "type": "arrival",
                    "task": {
                        "id": "r1",
                        "arrival_time": 0,
                        "priority": "routine",
                        "deadline": 8,
                    },
                },
            ],
            "2": [
                {
                    "type": "arrival",
                    "task": {
                        "id": "u2",
                        "arrival_time": 2,
                        "priority": "urgent",
                        "deadline": 6,
                    },
                }
            ],
        },
    )


def test_env_initialization(simple_config):
    """Test environment initialization."""
    env = QueueEnv(simple_config)
    assert env.horizon == 10
    assert env.capacity_per_step == 2
    assert env.time == 0


def test_env_reset(simple_config):
    """Test environment reset."""
    env = QueueEnv(simple_config)
    obs = env.reset()

    assert obs.time == 0
    assert obs.horizon == 10
    assert obs.capacity_per_step == 2
    assert len(obs.arrivals) == 2  # Two tasks arrive at step 0
    assert len(obs.pending) == 2


def test_env_step_with_noop(simple_config):
    """Test environment step with no-op action."""
    env = QueueEnv(simple_config)
    env.reset()

    # Step with noop
    obs, done = env.act([Action(type="noop")])

    assert env.time == 1
    assert not done
    assert len(obs.pending) == 2  # Still pending


def test_env_schedule_task(simple_config):
    """Test scheduling a task."""
    env = QueueEnv(simple_config)
    env.reset()

    # Schedule u1 for step 2
    action = Action(type="schedule", task_id="u1", step=2)
    obs, done = env.act([action])

    uid = env.get_uid("u1")
    assert uid is not None
    assert uid in env.scheduled
    assert uid not in env.pending
    assert env.tasks[uid].status == "scheduled"
    assert env.tasks[uid].scheduled_slot == 2


def test_env_task_completion(simple_config):
    """Test task completion."""
    env = QueueEnv(simple_config)
    env.reset()

    # Schedule u1 for step 1
    env.act([Action(type="schedule", task_id="u1", step=1)])

    # Step to time 1 - task should complete
    obs, done = env.act([Action(type="noop")])

    uid = env.get_uid("u1")
    assert uid is not None
    assert uid in env.completed
    assert uid not in env.scheduled
    assert env.tasks[uid].status == "completed"
    assert env.tasks[uid].completed_time == 1
    assert "u1" in obs.completed_this_step


def test_env_reject_task(simple_config):
    """Test rejecting a routine task."""
    env = QueueEnv(simple_config)
    env.reset()

    # Reject r1
    action = Action(type="reject", task_id="r1")
    obs, done = env.act([action])

    uid = env.get_uid("r1")
    assert uid is not None
    assert uid in env.rejected
    assert uid not in env.pending
    assert env.tasks[uid].status == "rejected"


def test_env_reschedule_task(simple_config):
    """Test rescheduling a task."""
    env = QueueEnv(simple_config)
    env.reset()

    # Schedule u1 for step 2
    env.act([Action(type="schedule", task_id="u1", step=2)])

    # Reschedule to step 3
    obs, done = env.act([Action(type="reschedule", task_id="u1", step=3)])

    uid = env.get_uid("u1")
    assert uid is not None
    assert env.tasks[uid].scheduled_slot == 3
    assert uid in env.schedule[3]
    assert uid not in env.schedule.get(2, [])


def test_env_deadline_miss(simple_config):
    """Test deadline miss detection."""
    env = QueueEnv(simple_config)
    env.reset()

    # Don't schedule u1 (deadline at step 5)
    # Step through time until past deadline
    for _ in range(6):
        obs, done = env.act([Action(type="noop")])

    # u1 should be missed
    uid = env.get_uid("u1")
    assert uid is not None
    assert uid in env.missed
    assert uid not in env.pending
    assert env.tasks[uid].status == "missed"


def test_env_cancel_task(simple_config):
    """Test agent-initiated cancellation."""
    env = QueueEnv(simple_config)
    env.reset()

    # Schedule u1
    env.act([Action(type="schedule", task_id="u1", step=2)])

    # Cancel it
    obs, done = env.act([Action(type="cancel", task_id="u1")])

    uid = env.get_uid("u1")
    assert uid is not None
    assert uid in env.cancelled
    assert uid not in env.scheduled
    assert env.tasks[uid].status == "cancelled"


def test_env_episode_completion(simple_config):
    """Test that episode ends at horizon."""
    env = QueueEnv(simple_config)
    env.reset()

    # Step through entire episode
    done = False
    steps = 0
    while not done:
        obs, done = env.act([Action(type="noop")])
        steps += 1
        if steps > 15:  # Safety check
            break

    assert done
    assert env.time == env.horizon


def test_env_multiple_arrivals(simple_config):
    """Test handling multiple arrivals in one step."""
    env = QueueEnv(simple_config)
    obs = env.reset()

    # Step 0 has 2 arrivals
    assert len(obs.arrivals) == 2
    assert len(obs.pending) == 2

    # Step to time 2 where u2 arrives
    env.act([Action(type="noop")])
    obs, done = env.act([Action(type="noop")])

    assert len(obs.arrivals) == 1
    assert obs.arrivals[0].id == "u2"
    assert len(obs.pending) == 3  # All three tasks pending


def test_env_state_summary(simple_config):
    """Test state summary."""
    env = QueueEnv(simple_config)
    env.reset()

    summary = env.get_state_summary()
    assert summary["time"] == 0
    assert summary["pending"] == 2
    assert summary["scheduled"] == 0
    assert summary["completed"] == 0
    assert summary["total_tasks"] == 2

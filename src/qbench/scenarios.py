"""Scenario catalog for QBench."""

from typing import List, Optional
from pathlib import Path

from qbench.config import DEFAULT_SCENARIOS_DIR

# All available QBench scenarios
AVAILABLE_SCENARIOS = [
    "backlog_cap_stability_guard",
    "cancel_then_rearrival_consistency",
    "cancellation_cascade_mass",
    "cold_start_to_surge",
    "conflicting_duplicate_id_robustness",
    "correlated_burst_cluster",
    "deceptive_calm_then_rate_shift",
    "double_peak_bursts",
    "duplicate_arrival_idempotency",
    "early_burst_then_calm",
    "fairness_anti_starvation",
    "gradual_capacity_increase",
    "hard_deadline_cutoff",
    "heavy_tail_random_bursts",
    "infeasible_overload_must_reject",
    "late_burst_slack_trap",
    "late_cancellation_backfill",
    "mixed_deadlines_tight_vs_loose",
    "mixed_priorities_tight_deadlines",
    "no_traffic_health_check",
    "periodic_spikes_wave_load",
    "planned_capacity_drop_window",
    "priority_mix_shift",
    "ramp_down_recovery",
    "ramp_up_load",
    "rolling_deadlines_stream",
    "routine_flood_with_urgent_trickle",
    "routine_spam_adversarial_load",
    "same_deadline_conflict",
    "stale_cancel_out_of_order",
    "steady_low_load_baseline",
    "steady_near_capacity",
    "temporary_capacity_boost_window",
    "unannounced_capacity_drop_shock",
    "urgent_flood_strict_sla",
]


def list_scenarios() -> List[str]:
    """
    Return list of all available scenarios.
    
    Returns:
        List of scenario names
    """
    return AVAILABLE_SCENARIOS.copy()


def get_scenario_names(scenario_filter: Optional[List[str]] = None) -> List[str]:
    """
    Get list of scenarios to run based on filter.
    
    Args:
        scenario_filter: List of specific scenario names, or None for all.
                        Special value ["all"] returns all scenarios.
    
    Returns:
        List of scenario names to run
        
    Raises:
        ValueError: If unknown scenario name in filter
    """
    if scenario_filter is None or "all" in scenario_filter:
        return AVAILABLE_SCENARIOS.copy()
    
    # Validate all requested scenarios exist
    for name in scenario_filter:
        if name not in AVAILABLE_SCENARIOS:
            raise ValueError(
                f"Unknown scenario: '{name}'. "
                f"Available scenarios: {', '.join(AVAILABLE_SCENARIOS[:5])}... "
                f"(total {len(AVAILABLE_SCENARIOS)}). "
                f"Use list_scenarios() to see all."
            )
    
    return scenario_filter


def get_scenario_paths(
    scenario_filter: Optional[List[str]] = None,
    scenarios_dir: str = DEFAULT_SCENARIOS_DIR
) -> List[Path]:
    """
    Get paths to scenario directories.
    
    Args:
        scenario_filter: Specific scenarios or None for all
        scenarios_dir: Base directory containing scenarios
    
    Returns:
        List of Path objects to scenario directories
    """
    scenario_names = get_scenario_names(scenario_filter)
    base_dir = Path(scenarios_dir)
    return [base_dir / name for name in scenario_names]


def get_scenario_count(scenario_filter: Optional[List[str]] = None) -> int:
    """
    Get number of scenarios that will be run.
    
    Args:
        scenario_filter: Specific scenarios or None for all
    
    Returns:
        Number of scenarios
    """
    return len(get_scenario_names(scenario_filter))

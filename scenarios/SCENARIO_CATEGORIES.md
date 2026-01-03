# Scenarios by Category

| Category | Count | Scenarios | Description |
|----------|-------|-----------|-------------|
| **Baseline** | 2 | [`no_traffic_health_check`](./no_traffic_health_check/), [`steady_low_load_baseline`](./steady_low_load_baseline/) | Basic health checks and low-load baseline testing |
| **Load Patterns** | 10 | [`steady_near_capacity`](./steady_near_capacity/), [`ramp_up_load`](./ramp_up_load/), [`ramp_down_recovery`](./ramp_down_recovery/), [`periodic_spikes_wave_load`](./periodic_spikes_wave_load/), [`cold_start_to_surge`](./cold_start_to_surge/), [`early_burst_then_calm`](./early_burst_then_calm/), [`late_burst_slack_trap`](./late_burst_slack_trap/), [`double_peak_bursts`](./double_peak_bursts/), [`heavy_tail_random_bursts`](./heavy_tail_random_bursts/), [`correlated_burst_cluster`](./correlated_burst_cluster/) | Various load patterns from steady to bursts and spikes |
| **Regime Shifts** | 2 | [`deceptive_calm_then_rate_shift`](./deceptive_calm_then_rate_shift/), [`priority_mix_shift`](./priority_mix_shift/) | Non-stationary behavior and composition changes |
| **Priority Handling** | 3 | [`urgent_flood_strict_sla`](./urgent_flood_strict_sla/), [`routine_flood_with_urgent_trickle`](./routine_flood_with_urgent_trickle/), [`mixed_priorities_tight_deadlines`](./mixed_priorities_tight_deadlines/) | Priority-based scheduling and triage under mixed workloads |
| **Deadline Handling** | 4 | [`same_deadline_conflict`](./same_deadline_conflict/), [`mixed_deadlines_tight_vs_loose`](./mixed_deadlines_tight_vs_loose/), [`rolling_deadlines_stream`](./rolling_deadlines_stream/), [`hard_deadline_cutoff`](./hard_deadline_cutoff/) | Deadline-aware scheduling and expiry management |
| **Capacity Stress** | 3 | [`infeasible_overload_must_reject`](./infeasible_overload_must_reject/), [`backlog_cap_stability_guard`](./backlog_cap_stability_guard/), [`fairness_anti_starvation`](./fairness_anti_starvation/) | System limits, overload handling, and fairness constraints |
| **Capacity Dynamics** | 4 | [`planned_capacity_drop_window`](./planned_capacity_drop_window/), [`unannounced_capacity_drop_shock`](./unannounced_capacity_drop_shock/), [`temporary_capacity_boost_window`](./temporary_capacity_boost_window/), [`gradual_capacity_increase`](./gradual_capacity_increase/) | Capacity changes over time (planned and unplanned) |
| **Cancellations** | 4 | [`late_cancellation_backfill`](./late_cancellation_backfill/), [`cancellation_cascade_mass`](./cancellation_cascade_mass/), [`cancel_then_rearrival_consistency`](./cancel_then_rearrival_consistency/), [`stale_cancel_out_of_order`](./stale_cancel_out_of_order/) | Cancellation handling, backfill, and consistency |
| **Env Robustness** | 2 | [`duplicate_arrival_idempotency`](./duplicate_arrival_idempotency/), [`conflicting_duplicate_id_robustness`](./conflicting_duplicate_id_robustness/) | Input validation and idempotency guarantees |
| **Adversarial** | 1 | [`routine_spam_adversarial_load`](./routine_spam_adversarial_load/) | Adversarial load patterns designed to stress the system |

**Total: 35 scenarios**

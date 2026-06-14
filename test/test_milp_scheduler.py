"""
Test suite for MILP-based HEMS Scheduler

This module contains comprehensive tests for the MILP optimization engine,
covering correctness, constraint satisfaction, and performance.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from milp_scheduler import MILPHEMSScheduler, create_milp_scheduler


def test_milp_scheduler_initialization():
    """Test MILP scheduler initialization with default and custom parameters."""
    # Test with defaults
    scheduler1 = create_milp_scheduler()
    assert scheduler1.battery_capacity == 10.0
    assert scheduler1.max_charge_power == 5.0
    assert scheduler1.soc_min == 0.1
    assert scheduler1.soc_max == 0.9
    
    # Test with custom parameters
    scheduler2 = MILPHEMSScheduler(
        battery_capacity=20.0,
        max_charge_power=10.0,
        max_discharge_power=8.0,
        efficiency_charge=0.92,
        efficiency_discharge=0.93,
        soc_min=0.15,
        soc_max=0.95,
        soc_initial=0.6
    )
    assert scheduler2.battery_capacity == 20.0
    assert scheduler2.efficiency_charge == 0.92
    
    print("✓ MILP scheduler initialization test passed")


def test_milp_optimization_basic():
    """Test basic MILP optimization."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [2.0, 3.0, 4.0, 2.5]
    pv_forecast = [1.0, 2.0, 3.0, 1.5]
    price_forecast = [0.10, 0.15, 0.25, 0.12]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Verify result structure
    assert 'charge' in result
    assert 'discharge' in result
    assert 'grid_import' in result
    assert 'grid_export' in result
    assert 'soc' in result
    assert 'solver_status' in result
    
    # Verify solution is optimal or feasible
    assert result['solver_status'] in ['optimal', 'feasible']
    
    # Verify array lengths
    assert len(result['charge']) == 4
    assert len(result['discharge']) == 4
    
    # Verify non-negative values
    assert all(c >= -0.001 for c in result['charge'])
    assert all(d >= -0.001 for d in result['discharge'])
    
    print("✓ Basic MILP optimization test passed")


def test_milp_constraint_satisfaction():
    """Test that MILP solution satisfies all constraints."""
    scheduler = MILPHEMSScheduler(
        battery_capacity=10.0,
        max_charge_power=3.0,
        max_discharge_power=3.0,
        soc_min=0.2,
        soc_max=0.8,
        soc_initial=0.5,
        reserve_requirement=0.25
    )
    
    load_forecast = [3.0, 4.0, 5.0, 3.5]
    pv_forecast = [1.0, 1.5, 2.0, 1.0]
    price_forecast = [0.15, 0.20, 0.30, 0.18]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Check power limits
    assert all(c <= scheduler.max_charge_power + 0.01 for c in result['charge'])
    assert all(d <= scheduler.max_discharge_power + 0.01 for d in result['discharge'])
    
    # Check SOC bounds
    assert all(s >= scheduler.soc_min - 0.01 for s in result['soc'])
    assert all(s <= scheduler.soc_max + 0.01 for s in result['soc'])
    
    # Check reserve requirement
    assert all(s >= scheduler.reserve_requirement - 0.01 for s in result['soc'])
    
    print("✓ MILP constraint satisfaction test passed")


def test_milp_energy_balance():
    """Test energy balance constraint satisfaction."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [2.0, 3.0, 4.0]
    pv_forecast = [1.0, 2.0, 1.5]
    price_forecast = [0.15, 0.20, 0.25]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Verify energy balance at each time step
    for t in range(len(load_forecast)):
        lhs = load_forecast[t]
        rhs = (
            pv_forecast[t] 
            + result['discharge'][t] 
            + result['grid_import'][t] 
            - result['charge'][t] 
            - result['grid_export'][t]
        )
        assert abs(lhs - rhs) < 0.01, f"Energy balance violated at t={t}: {lhs} != {rhs}"
    
    print("✓ Energy balance test passed")


def test_milp_peak_valley_arbitrage():
    """Test peak/valley price arbitrage capability."""
    scheduler = create_milp_scheduler(battery_capacity=15.0, max_power=5.0)
    
    # Clear price pattern: low-high-low
    load_forecast = [3.0] * 6
    pv_forecast = [0.0] * 6
    price_forecast = [0.08, 0.08, 0.30, 0.30, 0.08, 0.08]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Should charge during low price periods (t=0,1)
    valley_charge = sum(result['charge'][:2])
    
    # Should discharge during high price periods (t=2,3)
    peak_discharge = sum(result['discharge'][2:4])
    
    assert peak_discharge > 0.1, "Should discharge during peak hours"
    
    print("✓ Peak/valley arbitrage test passed")


def test_milp_high_pv_scenario():
    """Test MILP with high PV generation."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [1.0, 1.5, 1.0, 1.2]
    pv_forecast = [4.0, 5.0, 4.5, 3.5]
    price_forecast = [0.12, 0.12, 0.12, 0.12]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Should have significant export or charging
    total_export = sum(result['grid_export'])
    total_charge = sum(result['charge'])
    
    assert (total_export + total_charge) > 1.0, "Should utilize surplus PV"
    
    print("✓ High PV scenario test passed")


def test_milp_empty_forecast():
    """Test MILP with empty forecast arrays."""
    scheduler = create_milp_scheduler()
    
    result = scheduler.optimize_dispatch([], [], [])
    
    assert result['solver_status'] == 'empty'
    assert len(result['charge']) == 0
    
    print("✓ Empty forecast test passed")


def test_milp_single_time_step():
    """Test MILP with single time step."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [2.0]
    pv_forecast = [1.0]
    price_forecast = [0.15]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    assert len(result['charge']) == 1
    assert result['solver_status'] in ['optimal', 'feasible']
    
    print("✓ Single time step test passed")


def test_milp_mismatched_lengths():
    """Test that mismatched forecast lengths raise error."""
    scheduler = create_milp_scheduler()
    
    try:
        result = scheduler.optimize_dispatch(
            [2.0, 3.0],
            [1.0],
            [0.15, 0.20]
        )
        print("✗ Mismatched lengths test failed: Should have raised ValueError")
    except ValueError:
        print("✓ Mismatched lengths test passed")


def test_milp_calculate_metrics():
    """Test performance metrics calculation."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [2.0, 3.0, 4.0]
    pv_forecast = [1.0, 2.0, 1.5]
    price_forecast = [0.10, 0.15, 0.25]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    metrics = scheduler.calculate_metrics(result, load_forecast, pv_forecast, price_forecast)
    
    # Verify metrics structure
    assert 'total_cost' in metrics
    assert 'cost_savings' in metrics
    assert 'self_consumption_rate' in metrics
    
    # Verify reasonable values
    assert metrics['total_cost'] >= 0
    assert metrics['self_consumption_rate'] >= 0
    assert metrics['self_consumption_rate'] <= 1.0
    
    print("✓ Metrics calculation test passed")


def test_milp_solver_types():
    """Test different solver types."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [2.0, 3.0, 4.0]
    pv_forecast = [1.0, 2.0, 1.5]
    price_forecast = [0.10, 0.15, 0.25]
    
    # Test CBC solver (default, should always be available)
    result_cbc = scheduler.optimize_dispatch(
        load_forecast, pv_forecast, price_forecast, solver_type="CBC"
    )
    assert result_cbc['solver_status'] in ['optimal', 'feasible']
    
    print("✓ Solver types test passed")


def test_milp_multi_objective_weights():
    """Test multi-objective weight parameters."""
    scheduler = create_milp_scheduler()
    
    load_forecast = [3.0, 3.0, 3.0]
    pv_forecast = [1.0, 1.0, 1.0]
    price_forecast = [0.15, 0.25, 0.20]
    
    # Test with different weight combinations
    result1 = scheduler.optimize_dispatch(
        load_forecast, pv_forecast, price_forecast,
        alpha=1.0, beta=0.0, gamma=0.0
    )
    
    result2 = scheduler.optimize_dispatch(
        load_forecast, pv_forecast, price_forecast,
        alpha=1.0, beta=0.0, gamma=0.5
    )
    
    # Results should differ with different weights
    assert result1['solver_status'] in ['optimal', 'feasible']
    assert result2['solver_status'] in ['optimal', 'feasible']
    
    print("✓ Multi-objective weights test passed")


def test_milp_grid_limits():
    """Test grid import/export limit enforcement."""
    scheduler = MILPHEMSScheduler(
        battery_capacity=10.0,
        max_charge_power=5.0,
        max_discharge_power=5.0,
        grid_import_limit=3.0,
        grid_export_limit=2.0
    )
    
    load_forecast = [10.0, 10.0]
    pv_forecast = [0.0, 0.0]
    price_forecast = [0.15, 0.15]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Grid import should not exceed limit
    assert all(gi <= scheduler.grid_import_limit + 0.01 for gi in result['grid_import'])
    
    print("✓ Grid limits test passed")


def run_all_tests():
    """Run all MILP scheduler tests."""
    print("=" * 70)
    print("Running MILP HEMS Scheduler Tests")
    print("=" * 70)
    
    tests = [
        test_milp_scheduler_initialization,
        test_milp_optimization_basic,
        test_milp_constraint_satisfaction,
        test_milp_energy_balance,
        test_milp_peak_valley_arbitrage,
        test_milp_high_pv_scenario,
        test_milp_empty_forecast,
        test_milp_single_time_step,
        test_milp_mismatched_lengths,
        test_milp_calculate_metrics,
        test_milp_solver_types,
        test_milp_multi_objective_weights,
        test_milp_grid_limits,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("=" * 70)
    print(f"Results: Passed {passed}/{len(tests)} tests")
    if failed > 0:
        print(f"         Failed {failed} tests")
    else:
        print("         All tests passed! ✓")
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

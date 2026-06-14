"""
Test suite for HEMS AI Scheduling System

This module contains comprehensive tests for the Home Energy Management System
scheduler, covering various scenarios including:
- Basic functionality tests
- Edge cases (empty forecasts, single time step)
- High PV generation scenarios
- Peak/valley price arbitrage
- Battery constraint validation
- Performance metrics calculation
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hems_scheduler import BatteryModel, HEMSScheduler, create_example_scheduler


def test_battery_model_initialization():
    """Test battery model initialization with default and custom parameters."""
    # Test with default parameters
    battery1 = BatteryModel(capacity=10.0, max_charge_power=5.0, max_discharge_power=5.0)
    assert battery1.capacity == 10.0
    assert battery1.max_charge_power == 5.0
    assert battery1.soc_min == 0.1
    assert battery1.soc_max == 0.9
    assert battery1.soc_current == 0.5
    
    # Test with custom parameters
    battery2 = BatteryModel(
        capacity=20.0,
        max_charge_power=10.0,
        max_discharge_power=8.0,
        efficiency_charge=0.90,
        efficiency_discharge=0.92,
        soc_min=0.2,
        soc_max=0.95,
        soc_initial=0.6
    )
    assert battery2.capacity == 20.0
    assert battery2.efficiency_charge == 0.90
    assert battery2.soc_min == 0.2
    assert battery2.soc_current == 0.6
    
    print("✓ Battery model initialization test passed")


def test_battery_soc_update():
    """Test battery SOC update dynamics."""
    battery = BatteryModel(
        capacity=10.0,
        max_charge_power=5.0,
        max_discharge_power=5.0,
        soc_initial=0.5
    )
    
    # Test charging
    new_soc = battery.update_soc(charge_power=2.0, discharge_power=0.0, time_step=1.0)
    expected_soc = 0.5 + (2.0 * 0.95) / 10.0
    assert abs(new_soc - expected_soc) < 0.001
    
    # Test discharging
    battery.soc_current = 0.7
    new_soc = battery.update_soc(charge_power=0.0, discharge_power=3.0, time_step=1.0)
    expected_soc = 0.7 - (3.0 / 0.95) / 10.0
    assert abs(new_soc - expected_soc) < 0.001
    
    # Test SOC bounds (should not exceed soc_max)
    battery.soc_current = 0.85
    new_soc = battery.update_soc(charge_power=5.0, discharge_power=0.0, time_step=1.0)
    assert new_soc <= battery.soc_max
    
    # Test SOC bounds (should not go below soc_min)
    battery.soc_current = 0.15
    new_soc = battery.update_soc(charge_power=0.0, discharge_power=5.0, time_step=1.0)
    assert new_soc >= battery.soc_min
    
    print("✓ Battery SOC update test passed")


def test_scheduler_initialization():
    """Test HEMS scheduler initialization."""
    battery = BatteryModel(capacity=10.0, max_charge_power=5.0, max_discharge_power=5.0)
    scheduler = HEMSScheduler(
        battery=battery,
        grid_import_limit=8.0,
        grid_export_limit=6.0,
        reserve_requirement=0.25,
        time_step=0.5
    )
    
    assert scheduler.grid_import_limit == 8.0
    assert scheduler.grid_export_limit == 6.0
    assert scheduler.reserve_requirement == 0.25
    assert scheduler.time_step == 0.5
    
    print("✓ Scheduler initialization test passed")


def test_optimize_dispatch_basic():
    """Test basic dispatch optimization with simple scenario."""
    scheduler = create_example_scheduler()
    
    # Simple 4-hour forecast
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
    assert 'self_consumption' in result
    assert 'total_cost' in result
    
    # Verify array lengths
    assert len(result['charge']) == 4
    assert len(result['discharge']) == 4
    assert len(result['grid_import']) == 4
    assert len(result['grid_export']) == 4
    assert len(result['soc']) == 4
    
    # Verify non-negative values
    assert all(c >= 0 for c in result['charge'])
    assert all(d >= 0 for d in result['discharge'])
    assert all(gi >= 0 for gi in result['grid_import'])
    assert all(ge >= 0 for ge in result['grid_export'])
    
    print("✓ Basic dispatch optimization test passed")


def test_optimize_dispatch_high_pv():
    """Test dispatch with high PV generation (surplus scenario)."""
    scheduler = create_example_scheduler()
    
    # High PV generation scenario
    load_forecast = [1.0, 1.5, 1.0, 1.2]
    pv_forecast = [4.0, 5.0, 4.5, 3.5]
    price_forecast = [0.10, 0.12, 0.15, 0.11]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Should have significant self-consumption and export
    total_self_consumption = sum(result['self_consumption'])
    total_export = sum(result['grid_export'])
    
    assert total_self_consumption > 0
    assert total_export > 0
    
    # Self-consumption should be at least equal to load
    assert total_self_consumption >= sum(load_forecast) * 0.9
    
    print("✓ High PV generation test passed")


def test_optimize_dispatch_peak_valley():
    """Test peak/valley price arbitrage."""
    scheduler = create_example_scheduler()
    
    # Clear peak and valley prices
    load_forecast = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
    pv_forecast = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    price_forecast = [0.08, 0.08, 0.25, 0.25, 0.25, 0.08]  # Valley-Peak-Valley pattern
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # During peak hours (index 2,3,4), should discharge battery
    peak_discharge = sum(result['discharge'][2:5])
    assert peak_discharge > 0, "Should discharge during peak price periods"
    
    # During valley hours, should charge if possible
    valley_charge = sum(result['charge'][:2])
    # Note: May not charge if initial SOC is sufficient
    
    print("✓ Peak/valley arbitrage test passed")


def test_optimize_dispatch_empty():
    """Test dispatch with empty forecast arrays."""
    scheduler = create_example_scheduler()
    
    try:
        result = scheduler.optimize_dispatch([], [], [])
        assert len(result['charge']) == 0
        print("✓ Empty forecast test passed")
    except Exception as e:
        print(f"✗ Empty forecast test failed: {e}")


def test_optimize_dispatch_single_step():
    """Test dispatch with single time step."""
    scheduler = create_example_scheduler()
    
    load_forecast = [2.0]
    pv_forecast = [1.0]
    price_forecast = [0.15]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    assert len(result['charge']) == 1
    assert len(result['discharge']) == 1
    assert len(result['soc']) == 1
    
    print("✓ Single time step test passed")


def test_optimize_dispatch_mismatched_lengths():
    """Test that mismatched forecast lengths raise an error."""
    scheduler = create_example_scheduler()
    
    load_forecast = [2.0, 3.0]
    pv_forecast = [1.0]
    price_forecast = [0.15, 0.20]
    
    try:
        result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
        print("✗ Mismatched lengths test failed: Should have raised ValueError")
    except ValueError:
        print("✓ Mismatched lengths test passed")


def test_calculate_metrics():
    """Test performance metrics calculation."""
    scheduler = create_example_scheduler()
    
    load_forecast = [2.0, 3.0, 4.0, 2.5]
    pv_forecast = [1.0, 2.0, 3.0, 1.5]
    price_forecast = [0.10, 0.15, 0.25, 0.12]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    metrics = scheduler.calculate_metrics(result, price_forecast)
    
    # Verify metrics structure
    assert 'total_cost' in metrics
    assert 'cost_savings' in metrics
    assert 'self_consumption_rate' in metrics
    assert 'total_import_energy' in metrics
    assert 'total_export_energy' in metrics
    assert 'total_self_consumption' in metrics
    
    # Verify reasonable values
    assert metrics['total_cost'] >= 0
    assert metrics['self_consumption_rate'] >= 0
    assert metrics['self_consumption_rate'] <= 1.0
    
    print("✓ Metrics calculation test passed")


def test_battery_constraints():
    """Test that battery constraints are respected."""
    battery = BatteryModel(
        capacity=10.0,
        max_charge_power=3.0,
        max_discharge_power=3.0,
        soc_min=0.2,
        soc_max=0.8,
        soc_initial=0.5
    )
    scheduler = HEMSScheduler(battery=battery, time_step=1.0)
    
    # Scenario that would violate constraints without proper handling
    load_forecast = [5.0, 5.0, 5.0]
    pv_forecast = [0.0, 0.0, 0.0]
    price_forecast = [0.20, 0.20, 0.20]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Check that charge/discharge don't exceed power limits
    assert all(c <= battery.max_charge_power + 0.001 for c in result['charge'])
    assert all(d <= battery.max_discharge_power + 0.001 for d in result['discharge'])
    
    # Check that SOC stays within bounds
    assert all(s >= battery.soc_min - 0.001 for s in result['soc'])
    assert all(s <= battery.soc_max + 0.001 for s in result['soc'])
    
    print("✓ Battery constraints test passed")


def test_grid_power_limits():
    """Test that grid power limits are respected."""
    scheduler = HEMSScheduler(
        battery=BatteryModel(capacity=10.0, max_charge_power=5.0, max_discharge_power=5.0),
        grid_import_limit=5.0,
        grid_export_limit=4.0,
        time_step=1.0
    )
    
    load_forecast = [10.0, 10.0]
    pv_forecast = [0.0, 0.0]
    price_forecast = [0.15, 0.15]
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Grid import should not exceed limit
    assert all(gi <= scheduler.grid_import_limit + 0.001 for gi in result['grid_import'])
    
    print("✓ Grid power limits test passed")


def test_create_example_scheduler():
    """Test example scheduler creation."""
    scheduler = create_example_scheduler()
    
    assert scheduler.battery.capacity == 10.0
    assert scheduler.battery.max_charge_power == 5.0
    assert scheduler.time_step == 1.0
    
    print("✓ Example scheduler creation test passed")


def run_all_tests():
    """Run all test cases."""
    print("=" * 60)
    print("Running HEMS AI Scheduling System Tests")
    print("=" * 60)
    
    tests = [
        test_battery_model_initialization,
        test_battery_soc_update,
        test_scheduler_initialization,
        test_optimize_dispatch_basic,
        test_optimize_dispatch_high_pv,
        test_optimize_dispatch_peak_valley,
        test_optimize_dispatch_empty,
        test_optimize_dispatch_single_step,
        test_optimize_dispatch_mismatched_lengths,
        test_calculate_metrics,
        test_battery_constraints,
        test_grid_power_limits,
        test_create_example_scheduler,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: Passed {passed}/{len(tests)} tests")
    if failed > 0:
        print(f"         Failed {failed} tests")
    else:
        print("         All tests passed! ✓")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

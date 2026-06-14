"""
HEMS AI Scheduling System Demonstration

This script demonstrates the Home Energy Management System scheduler
with realistic scenarios including:
- Daily load and PV generation patterns
- Time-of-use electricity pricing
- Battery optimization for cost savings
- Performance metrics visualization
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hems_scheduler import create_example_scheduler


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def format_number(value, decimals=2):
    """Format number with specified decimal places."""
    return f"{value:.{decimals}f}"


def demonstrate_basic_scheduling():
    """Demonstrate basic scheduling with typical residential scenario."""
    print_section("Scenario 1: Basic Daily Scheduling")
    
    scheduler = create_example_scheduler()
    
    # 24-hour forecast (hourly intervals)
    hours = list(range(24))
    
    # Typical residential load profile (kW)
    load_forecast = [
        0.5, 0.4, 0.4, 0.3, 0.3, 0.5,   # 00:00 - 05:00 (low usage)
        1.0, 1.5, 1.2, 1.0, 1.0, 1.2,   # 06:00 - 11:00 (morning routine)
        1.5, 1.3, 1.2, 1.0, 1.2, 1.8,   # 12:00 - 17:00 (afternoon)
        2.5, 3.0, 2.8, 2.0, 1.5, 1.0    # 18:00 - 23:00 (evening peak)
    ]
    
    # PV generation profile (kW) - sunny day
    pv_forecast = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0,   # Night
        0.0, 0.5, 1.5, 2.5, 3.5, 4.0,   # Morning ramp-up
        4.5, 4.8, 4.5, 4.0, 3.0, 1.5,   # Afternoon peak
        0.5, 0.0, 0.0, 0.0, 0.0, 0.0    # Evening decline
    ]
    
    # Time-of-use pricing ($/kWh)
    price_forecast = [
        0.08, 0.08, 0.08, 0.08, 0.08, 0.08,  # Off-peak (night)
        0.10, 0.10, 0.12, 0.12, 0.12, 0.12,  # Mid-peak (morning)
        0.12, 0.12, 0.15, 0.15, 0.15, 0.15,  # Mid-peak (afternoon)
        0.25, 0.28, 0.28, 0.25, 0.15, 0.10   # Peak (evening)
    ]
    
    print("\nInput Summary:")
    print(f"  Total Load Demand:     {format_number(sum(load_forecast))} kWh")
    print(f"  Total PV Generation:   {format_number(sum(pv_forecast))} kWh")
    print(f"  Average Electricity Price: ${format_number(sum(price_forecast)/len(price_forecast), 3)}/kWh")
    print(f"  Battery Capacity:      {scheduler.battery.capacity} kWh")
    print(f"  Initial SOC:           {scheduler.battery.soc_current * 100}%")
    
    # Run optimization
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    metrics = scheduler.calculate_metrics(result, price_forecast)
    
    # Display results
    print("\nOptimization Results:")
    print(f"  Total Cost:            ${format_number(metrics['total_cost'])}")
    print(f"  Cost Savings:          ${format_number(metrics['cost_savings'])}")
    print(f"  Self-Consumption Rate: {format_number(metrics['self_consumption_rate'] * 100)}%")
    print(f"  Grid Import Energy:    {format_number(metrics['total_import_energy'])} kWh")
    print(f"  Grid Export Energy:    {format_number(metrics['total_export_energy'])} kWh")
    print(f"  Self-Consumed Energy:  {format_number(metrics['total_self_consumption'])} kWh")
    
    # Show hourly dispatch summary
    print("\nHourly Dispatch Schedule:")
    print("-" * 70)
    print(f"{'Hour':<6} {'Load':<8} {'PV':<8} {'Charge':<8} {'Discharge':<10} {'Grid Imp':<9} {'Grid Exp':<9} {'SOC':<8}")
    print("-" * 70)
    
    for t in range(24):
        print(
            f"{t:<6} "
            f"{format_number(load_forecast[t]):<8} "
            f"{format_number(pv_forecast[t]):<8} "
            f"{format_number(result['charge'][t]):<8} "
            f"{format_number(result['discharge'][t]):<10} "
            f"{format_number(result['grid_import'][t]):<9} "
            f"{format_number(result['grid_export'][t]):<9} "
            f"{format_number(result['soc'][t] * 100):<6}%"
        )
    
    print("-" * 70)
    
    return result, metrics


def demonstrate_peak_shaving():
    """Demonstrate peak shaving capability."""
    print_section("Scenario 2: Peak Shaving Optimization")
    
    scheduler = create_example_scheduler()
    
    # Scenario with high evening load
    load_forecast = [1.0] * 12 + [5.0, 6.0, 6.0, 5.0, 4.0, 3.0]
    pv_forecast = [0.0] * 6 + [3.0, 4.0, 4.5, 4.0, 3.0, 2.0] + [0.0] * 6
    price_forecast = [0.08] * 12 + [0.30, 0.35, 0.35, 0.30, 0.15, 0.10]
    
    print("\nScenario: High evening load with peak pricing")
    print(f"  Peak Load:               {max(load_forecast)} kW")
    print(f"  Peak Price:              ${max(price_forecast)}/kWh")
    print(f"  Battery Capacity:        {scheduler.battery.capacity} kWh")
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    metrics = scheduler.calculate_metrics(result, price_forecast)
    
    print("\nResults:")
    print(f"  Total Cost:              ${format_number(metrics['total_cost'])}")
    print(f"  Cost Savings:            ${format_number(metrics['cost_savings'])}")
    print(f"  Peak Hour Discharge:     {format_number(sum(result['discharge'][12:16]))} kWh")
    print(f"  Max Grid Import:         {format_number(max(result['grid_import']))} kW")
    
    # Calculate peak reduction
    max_load_without_battery = max(load_forecast)
    max_grid_with_battery = max(result['grid_import'])
    peak_reduction = max_load_without_battery - max_grid_with_battery
    
    print(f"  Peak Reduction:          {format_number(peak_reduction)} kW ({format_number(peak_reduction/max_load_without_battery*100)}%)")


def demonstrate_high_pv_scenario():
    """Demonstrate high PV self-consumption scenario."""
    print_section("Scenario 3: High PV Self-Consumption")
    
    scheduler = create_example_scheduler()
    
    # Sunny day with moderate load
    load_forecast = [0.8] * 24
    pv_forecast = [
        0.0, 0.0, 0.0, 0.0, 0.0, 0.2,
        1.0, 2.5, 4.0, 5.0, 5.5, 5.8,
        5.5, 5.0, 4.5, 3.5, 2.0, 0.5,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0
    ]
    price_forecast = [0.12] * 24
    
    print("\nScenario: High solar generation day")
    print(f"  Total Load:              {format_number(sum(load_forecast))} kWh")
    print(f"  Total PV Generation:     {format_number(sum(pv_forecast))} kWh")
    print(f"  PV Coverage Ratio:       {format_number(sum(pv_forecast)/sum(load_forecast)*100)}%")
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    metrics = scheduler.calculate_metrics(result, price_forecast)
    
    print("\nResults:")
    print(f"  Self-Consumption Rate:   {format_number(metrics['self_consumption_rate'] * 100)}%")
    print(f"  Total Self-Consumed:     {format_number(metrics['total_self_consumption'])} kWh")
    print(f"  Total Exported:          {format_number(metrics['total_export_energy'])} kWh")
    print(f"  Total Cost:              ${format_number(metrics['total_cost'])}")


def demonstrate_reserve_strategy():
    """Demonstrate reserve power strategy."""
    print_section("Scenario 4: Reserve Power Strategy")
    
    scheduler = create_example_scheduler()
    scheduler.reserve_requirement = 0.3  # 30% reserve requirement
    
    load_forecast = [2.0] * 24
    pv_forecast = [0.0] * 24
    price_forecast = [0.10] * 8 + [0.25] * 8 + [0.10] * 8
    
    print("\nScenario: Conservative operation with 30% reserve requirement")
    print(f"  Reserve Requirement:     {scheduler.reserve_requirement * 100}%")
    print(f"  Battery Capacity:        {scheduler.battery.capacity} kWh")
    print(f"  Reserved Energy:         {format_number(scheduler.battery.capacity * scheduler.reserve_requirement)} kWh")
    
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Check minimum SOC maintained
    min_soc = min(result['soc'])
    print(f"\nResults:")
    print(f"  Minimum SOC Achieved:    {format_number(min_soc * 100)}%")
    print(f"  Reserve Maintained:      {'Yes ✓' if min_soc >= scheduler.reserve_requirement else 'No ✗'}")
    print(f"  Final SOC:               {format_number(result['soc'][-1] * 100)}%")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  HEMS AI SCHEDULING SYSTEM - DEMONSTRATION")
    print("  Home Energy Management System with Intelligent Optimization")
    print("=" * 70)
    
    try:
        # Run demonstrations
        demonstrate_basic_scheduling()
        demonstrate_peak_shaving()
        demonstrate_high_pv_scenario()
        demonstrate_reserve_strategy()
        
        print_section("Summary")
        print("\nThe HEMS AI Scheduling System successfully demonstrates:")
        print("  ✓ Cost optimization through peak/valley arbitrage")
        print("  ✓ PV self-consumption maximization")
        print("  ✓ Battery SOC management within safe bounds")
        print("  ✓ Grid power flow optimization")
        print("  ✓ Reserve power strategy implementation")
        print("  ✓ Rolling horizon MPC-based optimization")
        print("\nFor production deployment, consider integrating with:")
        print("  - Real-time weather forecasting APIs")
        print("  - Smart meter data streams")
        print("  - MILP solvers (Gurobi, CPLEX, CBC) for exact optimization")
        print("  - Cloud-based monitoring and control systems")
        
        print("\n" + "=" * 70)
        print("  Demonstration Complete")
        print("=" * 70 + "\n")
        
    except Exception as e:
        print(f"\nError during demonstration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

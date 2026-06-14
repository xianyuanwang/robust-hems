"""
Quick Start Example for HEMS AI Scheduling System

This script provides a minimal example of how to use the HEMS scheduler
for residential energy storage optimization.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from hems_scheduler import create_example_scheduler


def main():
    """Simple example demonstrating HEMS scheduler usage."""
    
    print("=" * 60)
    print("HEMS Scheduler - Quick Start Example")
    print("=" * 60)
    
    # Step 1: Create scheduler with default parameters
    print("\n1. Creating scheduler...")
    scheduler = create_example_scheduler()
    print(f"   Battery capacity: {scheduler.battery.capacity} kWh")
    print(f"   Initial SOC: {scheduler.battery.soc_current * 100}%")
    
    # Step 2: Define forecast data (4-hour example)
    print("\n2. Defining forecast data...")
    load_forecast = [2.0, 3.0, 4.0, 2.5]  # kW
    pv_forecast = [1.0, 2.0, 3.0, 1.5]    # kW
    price_forecast = [0.10, 0.15, 0.25, 0.12]  # $/kWh
    
    print(f"   Load forecast: {load_forecast}")
    print(f"   PV forecast: {pv_forecast}")
    print(f"   Price forecast: {price_forecast}")
    
    # Step 3: Run optimization
    print("\n3. Running optimization...")
    result = scheduler.optimize_dispatch(load_forecast, pv_forecast, price_forecast)
    
    # Step 4: Display results
    print("\n4. Optimization Results:")
    print("-" * 60)
    print(f"{'Hour':<6} {'Load':<8} {'PV':<8} {'Charge':<8} {'Discharge':<10} {'Grid':<8} {'SOC':<8}")
    print("-" * 60)
    
    for t in range(len(load_forecast)):
        grid_net = result['grid_import'][t] - result['grid_export'][t]
        print(
            f"{t:<6} "
            f"{load_forecast[t]:<8.1f} "
            f"{pv_forecast[t]:<8.1f} "
            f"{result['charge'][t]:<8.2f} "
            f"{result['discharge'][t]:<10.2f} "
            f"{grid_net:<8.2f} "
            f"{result['soc'][t]*100:<6.1f}%"
        )
    
    # Step 5: Calculate and display metrics
    print("\n5. Performance Metrics:")
    print("-" * 60)
    metrics = scheduler.calculate_metrics(result, price_forecast)
    
    print(f"   Total Cost:          ${metrics['total_cost']:.2f}")
    print(f"   Cost Savings:        ${metrics['cost_savings']:.2f}")
    print(f"   Self-Consumption:    {metrics['self_consumption_rate']*100:.1f}%")
    print(f"   Grid Import Energy:  {metrics['total_import_energy']:.2f} kWh")
    print(f"   Grid Export Energy:  {metrics['total_export_energy']:.2f} kWh")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()

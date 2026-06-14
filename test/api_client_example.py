"""
API Client Example for HEMS Scheduling Service

This script demonstrates how to use the HEMS API service
with Python requests library.
"""

import requests
import json
from typing import Dict, Any


class HEMSAPIClient:
    """Client for HEMS API service."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize API client.
        
        Args:
            base_url: Base URL of the API service
        """
        self.base_url = base_url
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def optimize(
        self,
        load_forecast: list,
        pv_forecast: list,
        price_forecast: list,
        algorithm: str = "milp",
        battery_config: Dict[str, float] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Run optimization.
        
        Args:
            load_forecast: Load forecast in kW
            pv_forecast: PV forecast in kW
            price_forecast: Price forecast in $/kWh
            algorithm: Optimization algorithm ("milp" or "heuristic")
            battery_config: Optional custom battery configuration
            **kwargs: Additional optimization parameters
            
        Returns:
            Optimization result with schedule and metrics
        """
        request_data = {
            "forecasts": {
                "load_forecast": load_forecast,
                "pv_forecast": pv_forecast,
                "price_forecast": price_forecast
            },
            "algorithm": algorithm,
            **kwargs
        }
        
        if battery_config:
            request_data["battery_config"] = battery_config
        
        response = requests.post(
            f"{self.base_url}/optimize",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def optimize_batch(self, requests_list: list) -> Dict[str, Any]:
        """Run batch optimization.
        
        Args:
            requests_list: List of optimization request dictionaries
            
        Returns:
            Batch optimization results
        """
        response = requests.post(
            f"{self.base_url}/optimize/batch",
            json=requests_list,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get server statistics."""
        response = requests.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()


def example_basic_optimization():
    """Example: Basic MILP optimization."""
    print("=" * 70)
    print("Example 1: Basic MILP Optimization")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    # Check health
    health = client.health_check()
    print(f"\nAPI Status: {health['status']}")
    print(f"Version: {health['version']}")
    
    # Define forecasts (4-hour horizon)
    load_forecast = [2.0, 3.0, 4.0, 2.5]
    pv_forecast = [1.0, 2.0, 3.0, 1.5]
    price_forecast = [0.10, 0.15, 0.25, 0.12]
    
    # Run optimization
    result = client.optimize(
        load_forecast=load_forecast,
        pv_forecast=pv_forecast,
        price_forecast=price_forecast,
        algorithm="milp"
    )
    
    print(f"\nRequest ID: {result['request_id']}")
    print(f"Status: {result['status']}")
    print(f"Solver Status: {result['solver_status']}")
    print(f"Computation Time: {result['computation_time_ms']:.2f} ms")
    
    # Display schedule
    print("\nOptimized Schedule:")
    print("-" * 70)
    print(f"{'Hour':<6} {'Charge':<10} {'Discharge':<10} {'Grid Imp':<10} {'SOC':<10}")
    print("-" * 70)
    
    for t in range(len(load_forecast)):
        print(
            f"{t:<6} "
            f"{result['schedule']['charge'][t]:<10.2f} "
            f"{result['schedule']['discharge'][t]:<10.2f} "
            f"{result['schedule']['grid_import'][t]:<10.2f} "
            f"{result['schedule']['soc'][t]*100:<8.1f}%"
        )
    
    # Display metrics
    print("\nPerformance Metrics:")
    print(f"  Total Cost:          ${result['metrics']['total_cost']:.2f}")
    print(f"  Cost Savings:        ${result['metrics']['cost_savings']:.2f}")
    print(f"  Self-Consumption:    {result['metrics']['self_consumption_rate']*100:.1f}%")
    print(f"  Grid Import Energy:  {result['metrics']['total_import_energy']:.2f} kWh")
    print(f"  Grid Export Energy:  {result['metrics']['total_export_energy']:.2f} kWh")


def example_custom_battery():
    """Example: Custom battery configuration."""
    print("\n" + "=" * 70)
    print("Example 2: Custom Battery Configuration")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    # Custom battery config
    battery_config = {
        "capacity": 20.0,
        "max_charge_power": 10.0,
        "max_discharge_power": 10.0,
        "efficiency_charge": 0.92,
        "efficiency_discharge": 0.93,
        "soc_min": 0.15,
        "soc_max": 0.95,
        "soc_initial": 0.6
    }
    
    result = client.optimize(
        load_forecast=[3.0, 4.0, 5.0, 3.5],
        pv_forecast=[1.0, 2.0, 2.5, 1.5],
        price_forecast=[0.12, 0.20, 0.30, 0.18],
        algorithm="milp",
        battery_config=battery_config,
        reserve_requirement=0.25
    )
    
    print(f"\nBattery Capacity: 20 kWh")
    print(f"Total Cost: ${result['metrics']['total_cost']:.2f}")
    print(f"Cost Savings: ${result['metrics']['cost_savings']:.2f}")


def example_heuristic():
    """Example: Heuristic optimization (faster)."""
    print("\n" + "=" * 70)
    print("Example 3: Heuristic Optimization (Fast)")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    result = client.optimize(
        load_forecast=[2.0, 3.0, 4.0, 2.5],
        pv_forecast=[1.0, 2.0, 3.0, 1.5],
        price_forecast=[0.10, 0.15, 0.25, 0.12],
        algorithm="heuristic"
    )
    
    print(f"\nAlgorithm: Heuristic")
    print(f"Computation Time: {result['computation_time_ms']:.2f} ms")
    print(f"Total Cost: ${result['metrics']['total_cost']:.2f}")


def example_multi_objective():
    """Example: Multi-objective optimization."""
    print("\n" + "=" * 70)
    print("Example 4: Multi-Objective Optimization")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    # Optimize with weights for cost, peak shaving, and self-consumption
    result = client.optimize(
        load_forecast=[3.0, 4.0, 5.0, 4.0, 3.0],
        pv_forecast=[1.0, 2.0, 3.0, 2.0, 1.0],
        price_forecast=[0.10, 0.15, 0.30, 0.25, 0.12],
        algorithm="milp",
        alpha=1.0,   # Cost weight
        beta=0.5,    # Peak shaving weight
        gamma=0.3    # Self-consumption weight
    )
    
    print(f"\nWeights: alpha={1.0}, beta={0.5}, gamma={0.3}")
    print(f"Total Cost: ${result['metrics']['total_cost']:.2f}")
    print(f"Self-Consumption: {result['metrics']['self_consumption_rate']*100:.1f}%")


def example_batch_optimization():
    """Example: Batch optimization."""
    print("\n" + "=" * 70)
    print("Example 5: Batch Optimization")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    # Prepare multiple scenarios
    scenarios = [
        {
            "forecasts": {
                "load_forecast": [2.0, 3.0],
                "pv_forecast": [1.0, 2.0],
                "price_forecast": [0.10, 0.15]
            },
            "algorithm": "milp"
        },
        {
            "forecasts": {
                "load_forecast": [3.0, 4.0],
                "pv_forecast": [1.5, 2.5],
                "price_forecast": [0.12, 0.20]
            },
            "algorithm": "heuristic"
        }
    ]
    
    result = client.optimize_batch(scenarios)
    
    print(f"\nBatch Size: {result['batch_size']}")
    print(f"Results: {len(result['results'])} scenarios processed")
    
    for i, res in enumerate(result['results']):
        if res['status'] == 'success':
            print(f"  Scenario {i+1}: Cost=${res['metrics']['total_cost']:.2f}")
        else:
            print(f"  Scenario {i+1}: Error - {res.get('error', 'Unknown')}")


def example_server_stats():
    """Example: Get server statistics."""
    print("\n" + "=" * 70)
    print("Example 6: Server Statistics")
    print("=" * 70)
    
    client = HEMSAPIClient()
    
    stats = client.get_stats()
    
    print(f"\nActive Requests: {stats['active_requests']}")
    print(f"Total Processed: {stats['total_requests_processed']}")
    print(f"Uptime: {stats['uptime_hours']:.2f} hours")


def main():
    """Run all examples."""
    print("\n" + "=" * 70)
    print("HEMS API Client Examples")
    print("=" * 70)
    
    try:
        example_basic_optimization()
        example_custom_battery()
        example_heuristic()
        example_multi_objective()
        example_batch_optimization()
        example_server_stats()
        
        print("\n" + "=" * 70)
        print("All examples completed successfully!")
        print("=" * 70 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\nError: Cannot connect to API server.")
        print("Please start the server first:")
        print("  cd src")
        print("  python api_server.py")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

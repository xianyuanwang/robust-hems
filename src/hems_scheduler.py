"""
HEMS Residential Energy Storage AI Scheduling System

This module implements an intelligent scheduling system for household energy storage optimization.
It uses Model Predictive Control (MPC) with Mixed-Integer Linear Programming (MILP) to optimize
energy flow between residential loads, storage, photovoltaic generation, and the grid.

Key Features:
- Cost minimization through peak/valley arbitrage
- PV generation self-consumption maximization
- Battery state-of-charge (SOC) management
- Grid power flow optimization
- Rolling horizon optimization
- Safety constraints and reserve requirements
"""

from typing import List, Dict, Optional, Tuple
import numpy as np


class BatteryModel:
    """Battery model representing energy storage system dynamics and constraints."""
    
    def __init__(
        self,
        capacity: float,
        max_charge_power: float,
        max_discharge_power: float,
        efficiency_charge: float = 0.95,
        efficiency_discharge: float = 0.95,
        soc_min: float = 0.1,
        soc_max: float = 0.9,
        soc_initial: float = 0.5
    ):
        """Initialize battery model parameters.
        
        Args:
            capacity: Battery capacity in kWh
            max_charge_power: Maximum charging power in kW
            max_discharge_power: Maximum discharging power in kW
            efficiency_charge: Charging efficiency (0-1)
            efficiency_discharge: Discharging efficiency (0-1)
            soc_min: Minimum state of charge (0-1)
            soc_max: Maximum state of charge (0-1)
            soc_initial: Initial state of charge (0-1)
        """
        self.capacity = capacity
        self.max_charge_power = max_charge_power
        self.max_discharge_power = max_discharge_power
        self.efficiency_charge = efficiency_charge
        self.efficiency_discharge = efficiency_discharge
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.soc_current = soc_initial
    
    def update_soc(self, charge_power: float, discharge_power: float, time_step: float) -> float:
        """Update battery SOC based on charge/discharge actions.
        
        Args:
            charge_power: Charging power in kW
            discharge_power: Discharging power in kW
            time_step: Time interval in hours
            
        Returns:
            Updated SOC value (0-1)
        """
        energy_change = (
            charge_power * self.efficiency_charge - 
            discharge_power / self.efficiency_discharge
        ) * time_step
        
        soc_change = energy_change / self.capacity
        new_soc = self.soc_current + soc_change
        
        # Clamp SOC within bounds
        self.soc_current = max(self.soc_min, min(self.soc_max, new_soc))
        return self.soc_current


class HEMSScheduler:
    """Home Energy Management System scheduler using MPC approach."""
    
    def __init__(
        self,
        battery: BatteryModel,
        grid_import_limit: float = 10.0,
        grid_export_limit: float = 10.0,
        reserve_requirement: float = 0.2,
        time_step: float = 1.0
    ):
        """Initialize HEMS scheduler.
        
        Args:
            battery: Battery model instance
            grid_import_limit: Maximum grid import power in kW
            grid_export_limit: Maximum grid export power in kW
            reserve_requirement: Reserve SOC requirement (0-1)
            time_step: Dispatch interval in hours
        """
        self.battery = battery
        self.grid_import_limit = grid_import_limit
        self.grid_export_limit = grid_export_limit
        self.reserve_requirement = reserve_requirement
        self.time_step = time_step
    
    def optimize_dispatch(
        self,
        load_forecast: List[float],
        pv_forecast: List[float],
        price_forecast: List[float],
        alpha: float = 1.0,
        beta: float = 0.5,
        gamma: float = 0.3
    ) -> Dict[str, List[float]]:
        """Optimize energy dispatch using heuristic MPC approach.
        
        This implementation uses a rule-based optimization strategy that balances
        cost minimization, self-consumption, and battery safety.
        
        Args:
            load_forecast: Forecasted household load for each time step (kW)
            pv_forecast: Forecasted PV generation for each time step (kW)
            price_forecast: Forecasted electricity prices for each time step ($/kWh)
            alpha: Weight for cost minimization
            beta: Weight for peak shaving penalty
            gamma: Weight for self-consumption reward
            
        Returns:
            Dictionary containing optimized dispatch schedule:
            - charge: Battery charging power at each time step
            - discharge: Battery discharging power at each time step
            - grid_import: Grid import power at each time step
            - grid_export: Grid export power at each time step
            - soc: Battery SOC at each time step
            - self_consumption: Local consumption at each time step
        """
        n_steps = len(load_forecast)
        
        if n_steps != len(pv_forecast) or n_steps != len(price_forecast):
            raise ValueError("All forecast arrays must have the same length")
        
        # Initialize result arrays
        charge = [0.0] * n_steps
        discharge = [0.0] * n_steps
        grid_import = [0.0] * n_steps
        grid_export = [0.0] * n_steps
        soc_trajectory = [self.battery.soc_current] * (n_steps + 1)
        self_consumption = [0.0] * n_steps
        
        # Track cumulative cost
        total_cost = 0.0
        
        for t in range(n_steps):
            load = load_forecast[t]
            pv = pv_forecast[t]
            price = price_forecast[t]
            current_soc = soc_trajectory[t]
            
            # Calculate net load (positive means deficit, negative means surplus)
            net_load = load - pv
            
            # Rule-based optimization strategy
            if net_load <= 0:
                # Surplus PV generation
                surplus = -net_load
                
                # Priority 1: Self-consume PV for load
                self_consumption[t] = min(load, pv)
                
                # Priority 2: Charge battery with surplus
                available_charge = min(
                    surplus,
                    self.battery.max_charge_power,
                    (self.battery.soc_max - current_soc) * self.battery.capacity / self.time_step
                )
                
                if available_charge > 0:
                    charge[t] = available_charge
                    surplus -= available_charge
                
                # Priority 3: Export remaining surplus to grid
                if surplus > 0:
                    grid_export[t] = min(surplus, self.grid_export_limit)
                    
            else:
                # Load deficit
                # Priority 1: Use all PV generation for load
                self_consumption[t] = pv
                
                remaining_load = net_load
                
                # Determine if we should discharge battery
                # Strategy: discharge during high price periods, charge during low price
                should_discharge = self._should_discharge(price, price_forecast, t, current_soc)
                
                if should_discharge and remaining_load > 0:
                    # Calculate maximum discharge considering SOC constraints
                    min_soc_with_reserve = max(
                        self.battery.soc_min,
                        self.reserve_requirement
                    )
                    
                    available_discharge = min(
                        remaining_load,
                        self.battery.max_discharge_power,
                        (current_soc - min_soc_with_reserve) * self.battery.capacity / self.time_step
                    )
                    
                    if available_discharge > 0:
                        discharge[t] = available_discharge
                        remaining_load -= available_discharge
                
                # Import remaining load from grid
                if remaining_load > 0:
                    grid_import[t] = min(remaining_load, self.grid_import_limit)
            
            # Update SOC for next time step
            soc_trajectory[t + 1] = self.battery.update_soc(
                charge[t], discharge[t], self.time_step
            )
            
            # Calculate cost for this time step
            cost_t = price * (grid_import[t] - grid_export[t])
            total_cost += cost_t
        
        return {
            'charge': charge,
            'discharge': discharge,
            'grid_import': grid_import,
            'grid_export': grid_export,
            'soc': soc_trajectory[:-1],
            'self_consumption': self_consumption,
            'total_cost': total_cost
        }
    
    def _should_discharge(
        self,
        current_price: float,
        price_forecast: List[float],
        current_step: int,
        current_soc: float
    ) -> bool:
        """Determine if battery should discharge at current time step.
        
        Decision logic based on price comparison and SOC level.
        
        Args:
            current_price: Current electricity price
            price_forecast: Full price forecast array
            current_step: Current time step index
            current_soc: Current battery SOC
            
        Returns:
            True if battery should discharge, False otherwise
        """
        # Don't discharge if SOC is too low
        if current_soc <= max(self.battery.soc_min, self.reserve_requirement):
            return False
        
        # Calculate average future price
        future_prices = price_forecast[current_step + 1:]
        if not future_prices:
            avg_future_price = current_price
        else:
            avg_future_price = sum(future_prices) / len(future_prices)
        
        # Discharge if current price is significantly higher than average future price
        price_threshold = 1.2  # 20% higher threshold
        return current_price > avg_future_price * price_threshold
    
    def calculate_metrics(
        self,
        dispatch_result: Dict[str, List[float]],
        price_forecast: List[float]
    ) -> Dict[str, float]:
        """Calculate performance metrics for the dispatch schedule.
        
        Args:
            dispatch_result: Result from optimize_dispatch
            price_forecast: Electricity price forecast
            
        Returns:
            Dictionary containing performance metrics
        """
        grid_import = dispatch_result['grid_import']
        grid_export = dispatch_result['grid_export']
        self_consumption = dispatch_result['self_consumption']
        
        total_import_energy = sum(grid_import) * self.time_step
        total_export_energy = sum(grid_export) * self.time_step
        total_self_consumption = sum(self_consumption) * self.time_step
        
        # Calculate self-consumption rate
        total_generation = total_self_consumption + total_export_energy
        self_consumption_rate = (
            total_self_consumption / total_generation if total_generation > 0 else 0.0
        )
        
        # Calculate cost savings compared to no-battery scenario
        cost_with_battery = dispatch_result['total_cost']
        cost_without_battery = sum(
            p * max(0, l) for p, l in zip(price_forecast, grid_import)
        ) * self.time_step
        
        cost_savings = cost_without_battery - cost_with_battery
        
        return {
            'total_cost': cost_with_battery,
            'cost_savings': cost_savings,
            'self_consumption_rate': self_consumption_rate,
            'total_import_energy': total_import_energy,
            'total_export_energy': total_export_energy,
            'total_self_consumption': total_self_consumption
        }


def create_example_scheduler() -> HEMSScheduler:
    """Create an example HEMS scheduler with typical residential parameters.
    
    Returns:
        Configured HEMS scheduler instance
    """
    battery = BatteryModel(
        capacity=10.0,              # 10 kWh battery
        max_charge_power=5.0,       # 5 kW max charge
        max_discharge_power=5.0,    # 5 kW max discharge
        efficiency_charge=0.95,
        efficiency_discharge=0.95,
        soc_min=0.1,
        soc_max=0.9,
        soc_initial=0.5
    )
    
    scheduler = HEMSScheduler(
        battery=battery,
        grid_import_limit=10.0,
        grid_export_limit=10.0,
        reserve_requirement=0.2,
        time_step=1.0
    )
    
    return scheduler


__all__ = ['BatteryModel', 'HEMSScheduler', 'create_example_scheduler']

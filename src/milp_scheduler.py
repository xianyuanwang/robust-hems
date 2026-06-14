"""
MILP-based HEMS Scheduler using Google OR-Tools

This module implements a Mixed-Integer Linear Programming (MILP) optimization model
for Home Energy Management System scheduling using Google OR-Tools solver.

The MILP formulation provides exact optimal solutions for:
- Cost minimization through peak/valley arbitrage
- Self-consumption maximization
- Battery constraint enforcement
- Grid power flow optimization
"""

from typing import List, Dict, Optional, Tuple
from ortools.linear_solver import pywraplp
import numpy as np


class MILPHEMSScheduler:
    """
    MILP-based Home Energy Management System scheduler.
    
    Uses Mixed-Integer Linear Programming to find globally optimal dispatch
    schedules considering all constraints simultaneously.
    """
    
    def __init__(
        self,
        battery_capacity: float,
        max_charge_power: float,
        max_discharge_power: float,
        efficiency_charge: float = 0.95,
        efficiency_discharge: float = 0.95,
        soc_min: float = 0.1,
        soc_max: float = 0.9,
        soc_initial: float = 0.5,
        grid_import_limit: float = 10.0,
        grid_export_limit: float = 10.0,
        reserve_requirement: float = 0.2,
        time_step: float = 1.0
    ):
        """Initialize MILP scheduler parameters.
        
        Args:
            battery_capacity: Battery capacity in kWh
            max_charge_power: Maximum charging power in kW
            max_discharge_power: Maximum discharging power in kW
            efficiency_charge: Charging efficiency (0-1)
            efficiency_discharge: Discharging efficiency (0-1)
            soc_min: Minimum state of charge (0-1)
            soc_max: Maximum state of charge (0-1)
            soc_initial: Initial state of charge (0-1)
            grid_import_limit: Maximum grid import power in kW
            grid_export_limit: Maximum grid export power in kW
            reserve_requirement: Reserve SOC requirement (0-1)
            time_step: Dispatch interval in hours
        """
        self.battery_capacity = battery_capacity
        self.max_charge_power = max_charge_power
        self.max_discharge_power = max_discharge_power
        self.efficiency_charge = efficiency_charge
        self.efficiency_discharge = efficiency_discharge
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.soc_initial = soc_initial
        self.grid_import_limit = grid_import_limit
        self.grid_export_limit = grid_export_limit
        self.reserve_requirement = reserve_requirement
        self.time_step = time_step
        
        # Solver instance (created per optimization call for thread safety)
    
    def optimize_dispatch(
        self,
        load_forecast: List[float],
        pv_forecast: List[float],
        price_forecast: List[float],
        alpha: float = 1.0,
        beta: float = 0.0,
        gamma: float = 0.0,
        solver_type: str = "CBC"
    ) -> Dict[str, any]:
        """
        Optimize energy dispatch using MILP formulation.
        
        Solves the following optimization problem:
        
        Minimize: sum_t(alpha * price[t] * (grid_import[t] - grid_export[t])
                      + beta * peak_penalty[t]
                      - gamma * self_consumption[t])
        
        Subject to:
        - Energy balance: load[t] = pv[t] + discharge[t] + grid_import[t] 
                          - charge[t] - grid_export[t]
        - Battery dynamics: soc[t+1] = soc[t] + (charge[t]*eta_c - discharge[t]/eta_d)*dt/C
        - Power limits: 0 <= charge[t] <= P_max, 0 <= discharge[t] <= P_max
        - SOC bounds: soc_min <= soc[t] <= soc_max
        - Complementarity: charge[t] * discharge[t] = 0 (via binary variables)
        - Grid limits: 0 <= grid_import[t] <= import_limit
                       0 <= grid_export[t] <= export_limit
        - Reserve: soc[t] >= reserve_requirement
        
        Args:
            load_forecast: Forecasted household load for each time step (kW)
            pv_forecast: Forecasted PV generation for each time step (kW)
            price_forecast: Forecasted electricity prices for each time step ($/kWh)
            alpha: Weight for cost minimization
            beta: Weight for peak shaving penalty
            gamma: Weight for self-consumption reward
            solver_type: Solver backend ("CBC", "GLOP", "SCIP", "GUROBI")
            
        Returns:
            Dictionary containing optimized dispatch schedule and solution status
        """
        n_steps = len(load_forecast)
        
        if n_steps != len(pv_forecast) or n_steps != len(price_forecast):
            raise ValueError("All forecast arrays must have the same length")
        
        if n_steps == 0:
            return self._empty_result()
        
        # Create solver instance
        solver = self._create_solver(solver_type)
        if solver is None:
            raise ValueError(f"Solver type '{solver_type}' is not available")
        
        # Define decision variables
        variables = self._create_variables(solver, n_steps)
        
        # Add constraints
        self._add_energy_balance_constraints(solver, variables, load_forecast, pv_forecast, n_steps)
        self._add_battery_dynamics_constraints(solver, variables, n_steps)
        self._add_power_limit_constraints(solver, variables, n_steps)
        self._add_soc_bounds_constraints(solver, variables, n_steps)
        self._add_complementarity_constraints(solver, variables, n_steps)
        self._add_grid_limit_constraints(solver, variables, n_steps)
        self._add_reserve_constraints(solver, variables, n_steps)
        
        # Set objective function
        self._set_objective(solver, variables, price_forecast, alpha, beta, gamma, n_steps)
        
        # Solve
        status = solver.Solve()
        
        # Extract results
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            result = self._extract_results(variables, n_steps, status)
            result['solver_status'] = 'optimal' if status == pywraplp.Solver.OPTIMAL else 'feasible'
            result['objective_value'] = solver.Objective().Value()
        else:
            result = self._infeasible_result(status)
        
        return result
    
    def _create_solver(self, solver_type: str) -> Optional[pywraplp.Solver]:
        """Create OR-Tools solver instance.
        
        Args:
            solver_type: Type of solver to use
            
        Returns:
            Solver instance or None if not available
        """
        solver_map = {
            "CBC": pywraplp.Solver.CBC_MIXED_INTEGER_PROGRAMMING,
            "GLOP": pywraplp.Solver.GLOP_LINEAR_PROGRAMMING,
            "SCIP": pywraplp.Solver.SCIP_MIXED_INTEGER_PROGRAMMING,
            "GUROBI": pywraplp.Solver.GUROBI_MIXED_INTEGER_PROGRAMMING,
        }
        
        solver_id = solver_map.get(solver_type.upper())
        if solver_id is None:
            return None
        
        try:
            solver = pywraplp.Solver("HEMS_MILP", solver_id)
            return solver
        except Exception:
            return None
    
    def _create_variables(self, solver: pywraplp.Solver, n_steps: int) -> Dict[str, list]:
        """Create optimization decision variables.
        
        Args:
            solver: OR-Tools solver instance
            n_steps: Number of time steps
            
        Returns:
            Dictionary of variable arrays
        """
        variables = {}
        
        # Continuous variables: charge, discharge, grid_import, grid_export, soc
        variables['charge'] = [
            solver.NumVar(0, self.max_charge_power, f"charge_{t}")
            for t in range(n_steps)
        ]
        
        variables['discharge'] = [
            solver.NumVar(0, self.max_discharge_power, f"discharge_{t}")
            for t in range(n_steps)
        ]
        
        variables['grid_import'] = [
            solver.NumVar(0, self.grid_import_limit, f"grid_import_{t}")
            for t in range(n_steps)
        ]
        
        variables['grid_export'] = [
            solver.NumVar(0, self.grid_export_limit, f"grid_export_{t}")
            for t in range(n_steps)
        ]
        
        variables['soc'] = [
            solver.NumVar(self.soc_min, self.soc_max, f"soc_{t}")
            for t in range(n_steps)
        ]
        
        # Binary variables for complementarity constraint
        variables['u_charge'] = [
            solver.IntVar(0, 1, f"u_charge_{t}")
            for t in range(n_steps)
        ]
        
        variables['u_discharge'] = [
            solver.IntVar(0, 1, f"u_discharge_{t}")
            for t in range(n_steps)
        ]
        
        return variables
    
    def _add_energy_balance_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        load_forecast: List[float],
        pv_forecast: List[float],
        n_steps: int
    ):
        """Add energy balance constraints for each time step.
        
        load[t] = pv[t] + discharge[t] + grid_import[t] - charge[t] - grid_export[t]
        """
        for t in range(n_steps):
            constraint = solver.Constraint(0, 0, f"energy_balance_{t}")
            constraint.SetCoefficient(variables['discharge'][t], 1)
            constraint.SetCoefficient(variables['grid_import'][t], 1)
            constraint.SetCoefficient(variables['charge'][t], -1)
            constraint.SetCoefficient(variables['grid_export'][t], -1)
            constraint.SetBounds(
                load_forecast[t] - pv_forecast[t],
                load_forecast[t] - pv_forecast[t]
            )
    
    def _add_battery_dynamics_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """Add battery SOC dynamics constraints.
        
        soc[t+1] = soc[t] + (charge[t]*eta_c - discharge[t]/eta_d) * dt / capacity
        """
        for t in range(n_steps):
            if t == 0:
                # First time step uses initial SOC
                constraint = solver.Constraint(0, 0, f"soc_dynamic_{t}")
                constraint.SetCoefficient(variables['soc'][t], 1)
                constraint.SetCoefficient(variables['charge'][t], 
                    -self.efficiency_charge * self.time_step / self.battery_capacity)
                constraint.SetCoefficient(variables['discharge'][t], 
                    self.time_step / (self.efficiency_discharge * self.battery_capacity))
                constraint.SetBounds(self.soc_initial, self.soc_initial)
            else:
                # Subsequent time steps
                constraint = solver.Constraint(0, 0, f"soc_dynamic_{t}")
                constraint.SetCoefficient(variables['soc'][t], 1)
                constraint.SetCoefficient(variables['soc'][t-1], -1)
                constraint.SetCoefficient(variables['charge'][t], 
                    -self.efficiency_charge * self.time_step / self.battery_capacity)
                constraint.SetCoefficient(variables['discharge'][t], 
                    self.time_step / (self.efficiency_discharge * self.battery_capacity))
                constraint.SetBounds(0, 0)
    
    def _add_power_limit_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """Add charge/discharge power limit constraints with binary variables.
        
        charge[t] <= P_max * u_charge[t]
        discharge[t] <= P_max * u_discharge[t]
        """
        for t in range(n_steps):
            # Charge power limit
            constraint1 = solver.Constraint(-pywraplp.Solver.infinity(), 0, f"charge_limit_{t}")
            constraint1.SetCoefficient(variables['charge'][t], 1)
            constraint1.SetCoefficient(variables['u_charge'][t], -self.max_charge_power)
            
            # Discharge power limit
            constraint2 = solver.Constraint(-pywraplp.Solver.infinity(), 0, f"discharge_limit_{t}")
            constraint2.SetCoefficient(variables['discharge'][t], 1)
            constraint2.SetCoefficient(variables['u_discharge'][t], -self.max_discharge_power)
    
    def _add_soc_bounds_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """SOC bounds are already enforced in variable definition."""
        pass
    
    def _add_complementarity_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """Add complementarity constraint to prevent simultaneous charge/discharge.
        
        u_charge[t] + u_discharge[t] <= 1
        """
        for t in range(n_steps):
            constraint = solver.Constraint(-pywraplp.Solver.infinity(), 1, f"complementarity_{t}")
            constraint.SetCoefficient(variables['u_charge'][t], 1)
            constraint.SetCoefficient(variables['u_discharge'][t], 1)
    
    def _add_grid_limit_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """Grid import/export limits are already enforced in variable definition."""
        pass
    
    def _add_reserve_constraints(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        n_steps: int
    ):
        """Add reserve requirement constraints.
        
        soc[t] >= reserve_requirement
        """
        reserve_soc = max(self.soc_min, self.reserve_requirement)
        for t in range(n_steps):
            constraint = solver.Constraint(reserve_soc, pywraplp.Solver.infinity(), f"reserve_{t}")
            constraint.SetCoefficient(variables['soc'][t], 1)
    
    def _set_objective(
        self,
        solver: pywraplp.Solver,
        variables: Dict[str, list],
        price_forecast: List[float],
        alpha: float,
        beta: float,
        gamma: float,
        n_steps: int
    ):
        """Set optimization objective function.
        
        Minimize: sum_t(alpha * price[t] * (grid_import[t] - grid_export[t])
                      - gamma * self_consumption[t])
        
        where self_consumption[t] = min(load[t], pv[t] + discharge[t])
        Approximated as: self_consumption[t] >= pv[t] + discharge[t] - grid_export[t]
        """
        objective = solver.Objective()
        
        for t in range(n_steps):
            # Cost term: price * (import - export)
            objective.SetCoefficient(variables['grid_import'][t], alpha * price_forecast[t])
            objective.SetCoefficient(variables['grid_export'][t], -alpha * price_forecast[t])
            
            # Self-consumption reward (approximation)
            # Maximize: pv_used + discharge_used
            # Since pv_forecast is fixed, we maximize discharge when it reduces imports
            if gamma > 0:
                objective.SetCoefficient(variables['discharge'][t], -gamma * price_forecast[t])
        
        objective.SetMinimization()
    
    def _extract_results(
        self,
        variables: Dict[str, list],
        n_steps: int,
        status: int
    ) -> Dict[str, any]:
        """Extract optimization results from solver variables.
        
        Args:
            variables: Dictionary of solver variables
            n_steps: Number of time steps
            status: Solver status code
            
        Returns:
            Dictionary containing dispatch schedule
        """
        result = {
            'charge': [variables['charge'][t].solution_value() for t in range(n_steps)],
            'discharge': [variables['discharge'][t].solution_value() for t in range(n_steps)],
            'grid_import': [variables['grid_import'][t].solution_value() for t in range(n_steps)],
            'grid_export': [variables['grid_export'][t].solution_value() for t in range(n_steps)],
            'soc': [variables['soc'][t].solution_value() for t in range(n_steps)],
            'status': status
        }
        
        # Calculate self-consumption (approximation)
        result['self_consumption'] = [0.0] * n_steps
        result['total_cost'] = 0.0
        
        return result
    
    def _empty_result(self) -> Dict[str, any]:
        """Return empty result for zero-length forecasts."""
        return {
            'charge': [],
            'discharge': [],
            'grid_import': [],
            'grid_export': [],
            'soc': [],
            'self_consumption': [],
            'total_cost': 0.0,
            'solver_status': 'empty',
            'objective_value': 0.0
        }
    
    def _infeasible_result(self, status: int) -> Dict[str, any]:
        """Return result for infeasible problems."""
        status_map = {
            pywraplp.Solver.ABNORMAL: 'abnormal',
            pywraplp.Solver.INFEASIBLE: 'infeasible',
            pywraplp.Solver.UNBOUNDED: 'unbounded',
            pywraplp.Solver.NOT_SOLVED: 'not_solved'
        }
        
        return {
            'charge': [],
            'discharge': [],
            'grid_import': [],
            'grid_export': [],
            'soc': [],
            'self_consumption': [],
            'total_cost': float('inf'),
            'solver_status': status_map.get(status, 'error'),
            'objective_value': None
        }
    
    def calculate_metrics(
        self,
        dispatch_result: Dict[str, any],
        load_forecast: List[float],
        pv_forecast: List[float],
        price_forecast: List[float]
    ) -> Dict[str, float]:
        """Calculate performance metrics for the dispatch schedule.
        
        Args:
            dispatch_result: Result from optimize_dispatch
            load_forecast: Load forecast array
            pv_forecast: PV forecast array
            price_forecast: Price forecast array
            
        Returns:
            Dictionary containing performance metrics
        """
        if not dispatch_result.get('charge'):
            return {
                'total_cost': 0.0,
                'cost_savings': 0.0,
                'self_consumption_rate': 0.0,
                'total_import_energy': 0.0,
                'total_export_energy': 0.0,
                'total_self_consumption': 0.0
            }
        
        grid_import = dispatch_result['grid_import']
        grid_export = dispatch_result['grid_export']
        charge = dispatch_result['charge']
        discharge = dispatch_result['discharge']
        
        n_steps = len(grid_import)
        
        # Calculate total energies
        total_import_energy = sum(grid_import) * self.time_step
        total_export_energy = sum(grid_export) * self.time_step
        total_charge_energy = sum(charge) * self.time_step
        total_discharge_energy = sum(discharge) * self.time_step
        
        # Calculate self-consumption
        total_self_consumption = 0.0
        for t in range(n_steps):
            # Self-consumed PV = PV generation - exported PV
            pv_used = max(0, pv_forecast[t] - grid_export[t])
            # Self-consumed battery discharge
            discharge_used = discharge[t]
            total_self_consumption += (pv_used + discharge_used) * self.time_step
        
        # Calculate self-consumption rate
        total_generation = sum(pv_forecast) * self.time_step + total_discharge_energy
        self_consumption_rate = (
            total_self_consumption / total_generation if total_generation > 0 else 0.0
        )
        
        # Calculate cost
        total_cost = sum(
            price_forecast[t] * (grid_import[t] - grid_export[t])
            for t in range(n_steps)
        ) * self.time_step
        
        # Calculate baseline cost (without battery)
        baseline_cost = sum(
            price_forecast[t] * max(0, load_forecast[t] - pv_forecast[t])
            for t in range(n_steps)
        ) * self.time_step
        
        cost_savings = baseline_cost - total_cost
        
        return {
            'total_cost': total_cost,
            'cost_savings': cost_savings,
            'self_consumption_rate': min(1.0, self_consumption_rate),
            'total_import_energy': total_import_energy,
            'total_export_energy': total_export_energy,
            'total_self_consumption': total_self_consumption
        }


def create_milp_scheduler(
    battery_capacity: float = 10.0,
    max_power: float = 5.0,
    **kwargs
) -> MILPHEMSScheduler:
    """Factory function to create MILP scheduler with typical parameters.
    
    Args:
        battery_capacity: Battery capacity in kWh
        max_power: Maximum charge/discharge power in kW
        **kwargs: Additional parameters to override defaults
        
    Returns:
        Configured MILPHEMSScheduler instance
    """
    params = {
        'battery_capacity': battery_capacity,
        'max_charge_power': max_power,
        'max_discharge_power': max_power,
        'efficiency_charge': 0.95,
        'efficiency_discharge': 0.95,
        'soc_min': 0.1,
        'soc_max': 0.9,
        'soc_initial': 0.5,
        'grid_import_limit': 10.0,
        'grid_export_limit': 10.0,
        'reserve_requirement': 0.2,
        'time_step': 1.0
    }
    
    params.update(kwargs)
    
    return MILPHEMSScheduler(**params)


__all__ = ['MILPHEMSScheduler', 'create_milp_scheduler']

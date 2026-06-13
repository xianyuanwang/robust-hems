# HEMS Residential Energy Storage AI Scheduling Algorithm

## 1. Overview

A Home Energy Management System (HEMS) optimizes the energy flow between residential loads, storage, and the grid. As a senior expert in residential storage AI scheduling, this solution defines an intelligent scheduling system for household operation. It considers price signals, forecasted load, battery state of charge (SOC), photovoltaic generation, user preferences, and equipment constraints to deliver cost-optimal, comfortable, and efficient dispatch.

Objectives:
- Minimize household energy cost
- Maximize local self-consumption
- Keep the storage system operating within a safe SOC range
- Meet user requirements for peak/off-peak consumption and reserve power

## 2. System Inputs and State Variables

### 2.1 Input Data

- `load_forecast[t]`: forecasted household load at time `t`
- `pv_forecast[t]`: forecasted PV generation
- `price_forecast[t]`: forecasted electricity prices, including peak/flat/off-peak tariffs
- `soc_current`: current battery state of charge
- `grid_limit`: maximum grid import/export power
- `battery_capacity`: battery capacity in kWh
- `battery_power_max`: maximum charge/discharge power in kW
- `battery_efficiency_charge` / `battery_efficiency_discharge`: charge/discharge efficiency
- `time_step`: dispatch interval (e.g., 1 hour, 30 minutes)
- `user_preferences`: user dispatch preferences (e.g., self-consumption priority, reserve priority, strict peak control)
- `reserve_requirement`: reserve energy requirement for outage protection

### 2.2 State Variables

- `soc[t]`: battery SOC at time `t`
- `grid_import[t]`: electricity imported from the grid
- `grid_export[t]`: electricity exported to the grid
- `charge[t]`: battery charging power
- `discharge[t]`: battery discharging power
- `self_consumption[t]`: local consumption of PV and stored energy

## 3. Objective Function

The scheduling objective is usually cost minimization, optionally combined with user preference terms. A typical objective is:

`minimize Sum_t( price[t] * grid_import[t] - price[t] * grid_export[t] + penalty_terms )`

Where:
- `grid_import[t]`: energy purchased from the grid
- `grid_export[t]`: energy sold back to the grid
- `penalty_terms`: penalties for SOC violations, insufficient reserve, peak limits, comfort violations, etc.

To balance self-consumption and peak shaving, the objective can be extended to:

`minimize Alpha * cost + Beta * peak_penalty - Gamma * self_consumption`

Alpha/Beta/Gamma are weighting factors reflecting customer priorities.

## 4. Constraints

### 4.1 Energy Balance Constraint

For each time step `t`:

`load_forecast[t] = pv_forecast[t] + discharge[t] + grid_import[t] - charge[t] - grid_export[t]`

This means household load is served by PV generation, battery discharge, and grid import. Battery charge and exports are subtracted.

### 4.2 Battery Capacity and Power Constraints

- Charge/discharge power limits:
  - `0 <= charge[t] <= battery_power_max`
  - `0 <= discharge[t] <= battery_power_max`
- Prevent simultaneous charge and discharge:
  - `charge[t] * discharge[t] = 0` (strict complementary constraint)
  - Or use binary variables `u_charge[t], u_discharge[t]` for linear modeling

### 4.3 SOC Dynamics Constraint

- `soc[t+1] = soc[t] + (charge[t] * eta_charge - discharge[t] / eta_discharge) * time_step / battery_capacity`
- SOC bounds:
  - `soc_min <= soc[t] <= soc_max`

### 4.4 Grid Power Constraints

- `0 <= grid_import[t] <= import_limit`
- `0 <= grid_export[t] <= export_limit`
- For bidirectional flow, use: `-export_limit <= grid_flow[t] <= import_limit`

### 4.5 Comfort and Reserve Constraints

- Ensure household load is met.
- If a reserve requirement exists, preserve minimum discharge capacity:
  - `soc[t] >= soc_reserve[t]`
- Limit peak grid import:
  - `grid_import[t] <= peak_limit[t]`

## 5. Algorithm Framework

### 5.1 Data Input and Forecasting

- Collect historical load, weather, and PV generation data
- Run load and PV forecasting models to create `load_forecast` and `pv_forecast`
- Retrieve price signals
- Update current state `soc_current` and device status

### 5.2 Optimization Model Selection

Choose an algorithm based on problem complexity:

1. Linear Programming / Mixed-Integer Linear Programming (LP/MILP)
   - Suitable for strict constraints and global optimality
   - Requires binary variables for charge/discharge complementarity and ON/OFF logic

2. Dynamic Programming (DP)
   - Suitable for short horizons, discretized SOC, and control policy optimization
   - Can handle nonlinear reward structures and reserve requirements

3. Reinforcement Learning (RL)
   - Useful for long-term adaptation in uncertain environments
   - Offers fast online control after training, but requires extensive historical data and simulation

4. Rule-based heuristic algorithms
   - Suitable for constrained edge hardware
   - Uses peak/valley arbitrage, SOC reservation, and self-consumption heuristics

### 5.3 Recommended Approach: Hybrid Optimization

For practical residential storage, a hybrid Model Predictive Control (MPC) plus rule-based approach is recommended:

- Run rolling optimization every hour or half-hour
- Forecast the next `N` intervals for load, PV, and price
- Solve an MILP for optimal `charge`, `discharge`, `grid_import`, and `grid_export`
- Execute the first-step action and reoptimize in the next cycle

This balances reliability, cost efficiency, and dynamic responsiveness.

## 6. Detailed Dispatch Strategy

### 6.1 Rule Layer

Define priority order:
- Guarantee minimum SOC and reserve energy first
- Maximize local PV self-consumption next
- Finally, perform peak shaving and cost reduction

Typical rules:
- During daytime PV production, use PV for load first, then charge the battery to `soc_max`; if surplus remains and export is allowed, sell back to the grid.
- During peak price periods (for example 18:00-21:00), discharge the battery to serve load and reduce grid purchases.
- During low-price periods, charge from the grid if SOC is below the upper bound and future energy is expected.
- When a high load period or outage risk is forecast, reserve SOC in advance.

### 6.2 Optimization Layer

Model MPC or MILP as:

Variables:
- `charge[t], discharge[t], grid_import[t], grid_export[t], soc[t]`

Objective:
- `min Sum_t( price[t] * grid_import[t] - price[t] * grid_export[t] + lambda1 * peak_penalty[t] + lambda2 * reserve_penalty[t] )`

Constraints: as described above.

To encourage self-consumption, add:
- `-lambda3 * self_consumption[t]`

### 6.3 Reserve and Safety Strategy

- Set `soc_min_safe` as a minimum safety reserve to avoid deep discharge.
- If grid outage risk increases, allocate remaining SOC to a `reserve_block`.
- In outage forecasting scenarios, explicitly reserve `reserve_requirement` capacity.

## 7. Extensions: Multi-objective and Distributed Coordination

### 7.1 Multi-objective Scheduling

Extend the optimization to multiple objectives:
- Minimize cost
- Maximize self-consumption
- Minimize peak demand
- Minimize battery degradation

Use weighted sum or lexicographic optimization:
- First satisfy safety and reserve constraints
- Then minimize cost
- Finally maximize self-consumption within feasible solutions

### 7.2 Grid and VPP Coordination

- Participate in demand response (DR), discharging or reducing load in high-price periods
- Coordinate with a virtual power plant to provide flexible load and storage services
- Adjust household dispatch using dynamic price signals or bidding strategies

## 8. Implementation Recommendations

### 8.1 Dispatch Frequency

- Recommend rolling dispatch every 15-60 minutes
- Use shorter intervals when PV or load changes rapidly

### 8.2 Data Updates

- Update prices, weather forecasts, load forecasts, and SOC in real time
- Continuously correct forecast error with historical data

### 8.3 Software and Hardware Implementation

- Deploy the scheduler on a gateway or cloud-connected edge device
- Implement the optimization layer in Python/Matlab/Julia, with a lightweight rule layer on edge hardware
- Use solvers such as CPLEX, Gurobi, CBC, GLPK, or lightweight MILP libraries like `PuLP` and `Pyomo`

## 9. Conclusion

This document defines a practical residential storage HEMS AI scheduling architecture:

1. Use MPC + MILP rolling optimization
2. Combine a rule layer to ensure safety, self-consumption, and reserve energy
3. Use forecast-driven constraints to perform peak/valley arbitrage and reliable dispatch
4. Support multi-objective extensions and grid/VPP coordination

This approach is suitable for small and medium household storage systems and can evolve into aggregated multi-user and distributed energy coordination.

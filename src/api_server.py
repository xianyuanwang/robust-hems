"""
FastAPI Service for HEMS AI Scheduling

This module provides a RESTful API for the Home Energy Management System
scheduling algorithms, supporting both rule-based and MILP optimization.

Features:
- Multi-user concurrent access support
- Thread-safe scheduler instances
- Asynchronous request handling
- Comprehensive input validation
- Performance monitoring and logging
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, validator
from typing import List, Dict, Optional, Any
import asyncio
import time
import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import threading

from milp_scheduler import MILPHEMSScheduler, create_milp_scheduler
from hems_scheduler import HEMSScheduler, BatteryModel, create_example_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class ForecastData(BaseModel):
    """Forecast data for scheduling optimization."""
    load_forecast: List[float] = Field(..., description="Load forecast in kW", min_items=1, max_items=168)
    pv_forecast: List[float] = Field(..., description="PV generation forecast in kW", min_items=1, max_items=168)
    price_forecast: List[float] = Field(..., description="Electricity price forecast in $/kWh", min_items=1, max_items=168)
    
    @validator('pv_forecast', 'price_forecast')
    def validate_array_lengths(cls, v, values):
        """Validate all forecast arrays have the same length."""
        if 'load_forecast' in values and len(v) != len(values['load_forecast']):
            raise ValueError('All forecast arrays must have the same length')
        return v
    
    @validator('load_forecast', 'pv_forecast', 'price_forecast', each_item=True)
    def validate_non_negative(cls, v):
        """Validate non-negative values."""
        if v < 0:
            raise ValueError('Forecast values must be non-negative')
        return v


class BatteryConfig(BaseModel):
    """Battery configuration parameters."""
    capacity: float = Field(10.0, description="Battery capacity in kWh", gt=0, le=1000)
    max_charge_power: float = Field(5.0, description="Maximum charging power in kW", gt=0, le=500)
    max_discharge_power: float = Field(5.0, description="Maximum discharging power in kW", gt=0, le=500)
    efficiency_charge: float = Field(0.95, description="Charging efficiency", ge=0.5, le=1.0)
    efficiency_discharge: float = Field(0.95, description="Discharging efficiency", ge=0.5, le=1.0)
    soc_min: float = Field(0.1, description="Minimum SOC", ge=0, le=1)
    soc_max: float = Field(0.9, description="Maximum SOC", ge=0, le=1)
    soc_initial: float = Field(0.5, description="Initial SOC", ge=0, le=1)
    
    @validator('soc_max')
    def validate_soc_range(cls, v, values):
        """Validate SOC max is greater than SOC min."""
        if 'soc_min' in values and v <= values['soc_min']:
            raise ValueError('soc_max must be greater than soc_min')
        return v
    
    @validator('soc_initial')
    def validate_initial_soc(cls, v, values):
        """Validate initial SOC is within bounds."""
        if 'soc_min' in values and 'soc_max' in values:
            if not (values['soc_min'] <= v <= values['soc_max']):
                raise ValueError('soc_initial must be between soc_min and soc_max')
        return v


class OptimizationRequest(BaseModel):
    """Optimization request payload."""
    forecasts: ForecastData
    battery_config: Optional[BatteryConfig] = None
    grid_import_limit: float = Field(10.0, description="Grid import limit in kW", gt=0, le=1000)
    grid_export_limit: float = Field(10.0, description="Grid export limit in kW", gt=0, le=1000)
    reserve_requirement: float = Field(0.2, description="Reserve requirement", ge=0, le=1)
    time_step: float = Field(1.0, description="Time step in hours", gt=0, le=24)
    algorithm: str = Field("milp", description="Optimization algorithm (milp or heuristic)")
    solver_type: str = Field("CBC", description="MILP solver type (CBC, GLOP, SCIP)")
    alpha: float = Field(1.0, description="Cost weight", ge=0)
    beta: float = Field(0.0, description="Peak shaving weight", ge=0)
    gamma: float = Field(0.0, description="Self-consumption weight", ge=0)
    
    @validator('algorithm')
    def validate_algorithm(cls, v):
        """Validate algorithm selection."""
        if v.lower() not in ['milp', 'heuristic']:
            raise ValueError('Algorithm must be either "milp" or "heuristic"')
        return v.lower()
    
    @validator('solver_type')
    def validate_solver(cls, v):
        """Validate solver type."""
        if v.upper() not in ['CBC', 'GLOP', 'SCIP', 'GUROBI']:
            raise ValueError('Solver must be CBC, GLOP, SCIP, or GUROBI')
        return v.upper()


class DispatchSchedule(BaseModel):
    """Optimized dispatch schedule."""
    charge: List[float]
    discharge: List[float]
    grid_import: List[float]
    grid_export: List[float]
    soc: List[float]
    self_consumption: List[float]


class OptimizationMetrics(BaseModel):
    """Performance metrics."""
    total_cost: float
    cost_savings: float
    self_consumption_rate: float
    total_import_energy: float
    total_export_energy: float
    total_self_consumption: float


class OptimizationResponse(BaseModel):
    """Optimization response."""
    request_id: str
    status: str
    schedule: DispatchSchedule
    metrics: OptimizationMetrics
    solver_status: Optional[str] = None
    objective_value: Optional[float] = None
    computation_time_ms: float
    timestamp: datetime


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    uptime_seconds: float
    active_requests: int
    total_requests_processed: int


# ============================================================================
# Scheduler Manager (Thread-Safe)
# ============================================================================

class SchedulerManager:
    """
    Thread-safe manager for scheduler instances.
    
    Creates isolated scheduler instances per request to support
    concurrent multi-user access without state conflicts.
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._active_requests = 0
        self._total_requests = 0
        self._start_time = time.time()
    
    def create_scheduler(self, config: OptimizationRequest) -> Any:
        """Create a new scheduler instance based on request configuration.
        
        Args:
            config: Optimization request configuration
            
        Returns:
            Scheduler instance (MILP or heuristic)
        """
        battery = config.battery_config or BatteryConfig()
        
        if config.algorithm == "milp":
            scheduler = create_milp_scheduler(
                battery_capacity=battery.capacity,
                max_power=max(battery.max_charge_power, battery.max_discharge_power),
                efficiency_charge=battery.efficiency_charge,
                efficiency_discharge=battery.efficiency_discharge,
                soc_min=battery.soc_min,
                soc_max=battery.soc_max,
                soc_initial=battery.soc_initial,
                grid_import_limit=config.grid_import_limit,
                grid_export_limit=config.grid_export_limit,
                reserve_requirement=config.reserve_requirement,
                time_step=config.time_step
            )
        else:
            # Heuristic scheduler
            battery_model = BatteryModel(
                capacity=battery.capacity,
                max_charge_power=battery.max_charge_power,
                max_discharge_power=battery.max_discharge_power,
                efficiency_charge=battery.efficiency_charge,
                efficiency_discharge=battery.efficiency_discharge,
                soc_min=battery.soc_min,
                soc_max=battery.soc_max,
                soc_initial=battery.soc_initial
            )
            
            scheduler = HEMSScheduler(
                battery=battery_model,
                grid_import_limit=config.grid_import_limit,
                grid_export_limit=config.grid_export_limit,
                reserve_requirement=config.reserve_requirement,
                time_step=config.time_step
            )
        
        return scheduler
    
    def increment_active(self):
        """Increment active request counter."""
        with self._lock:
            self._active_requests += 1
            self._total_requests += 1
    
    def decrement_active(self):
        """Decrement active request counter."""
        with self._lock:
            self._active_requests -= 1
    
    def get_stats(self) -> Dict[str, any]:
        """Get current statistics."""
        with self._lock:
            return {
                'active_requests': self._active_requests,
                'total_requests': self._total_requests,
                'uptime_seconds': time.time() - self._start_time
            }


# Global scheduler manager instance
scheduler_manager = SchedulerManager()


# ============================================================================
# FastAPI Application
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("HEMS API server starting up...")
    yield
    logger.info("HEMS API server shutting down...")


app = FastAPI(
    title="HEMS AI Scheduling API",
    description="Home Energy Management System - AI-powered scheduling optimization",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    stats = scheduler_manager.get_stats()
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        uptime_seconds=stats['uptime_seconds'],
        active_requests=stats['active_requests'],
        total_requests_processed=stats['total_requests']
    )


@app.post("/optimize", response_model=OptimizationResponse)
async def optimize_dispatch(request: OptimizationRequest):
    """
    Optimize energy dispatch schedule.
    
    Performs optimization using either MILP (exact optimal) or heuristic
    (fast approximate) algorithms based on request configuration.
    
    Supports concurrent requests from multiple users with thread-safe
    scheduler instance management.
    """
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    logger.info(f"Request {request_id}: Starting optimization (algorithm={request.algorithm})")
    
    try:
        # Increment active request counter
        scheduler_manager.increment_active()
        
        # Create isolated scheduler instance
        scheduler = scheduler_manager.create_scheduler(request)
        
        # Extract forecast data
        load_forecast = request.forecasts.load_forecast
        pv_forecast = request.forecasts.pv_forecast
        price_forecast = request.forecasts.price_forecast
        
        # Run optimization
        if request.algorithm == "milp":
            result = scheduler.optimize_dispatch(
                load_forecast=load_forecast,
                pv_forecast=pv_forecast,
                price_forecast=price_forecast,
                alpha=request.alpha,
                beta=request.beta,
                gamma=request.gamma,
                solver_type=request.solver_type
            )
            
            # Calculate metrics for MILP
            metrics_dict = scheduler.calculate_metrics(
                result, load_forecast, pv_forecast, price_forecast
            )
        else:
            # Heuristic optimization
            result = scheduler.optimize_dispatch(
                load_forecast=load_forecast,
                pv_forecast=pv_forecast,
                price_forecast=price_forecast,
                alpha=request.alpha,
                beta=request.beta,
                gamma=request.gamma
            )
            
            # Calculate metrics for heuristic
            metrics_dict = scheduler.calculate_metrics(result, price_forecast)
        
        computation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Build response
        response = OptimizationResponse(
            request_id=request_id,
            status="success",
            schedule=DispatchSchedule(
                charge=result.get('charge', []),
                discharge=result.get('discharge', []),
                grid_import=result.get('grid_import', []),
                grid_export=result.get('grid_export', []),
                soc=result.get('soc', []),
                self_consumption=result.get('self_consumption', [])
            ),
            metrics=OptimizationMetrics(**metrics_dict),
            solver_status=result.get('solver_status'),
            objective_value=result.get('objective_value'),
            computation_time_ms=computation_time,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Request {request_id}: Completed in {computation_time:.2f}ms")
        
        return response
    
    except ValueError as e:
        logger.error(f"Request {request_id}: Validation error - {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Request {request_id}: Unexpected error - {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")
    
    finally:
        # Decrement active request counter
        scheduler_manager.decrement_active()


@app.post("/optimize/batch")
async def optimize_batch(requests: List[OptimizationRequest]):
    """
    Batch optimization endpoint for multiple scenarios.
    
    Processes multiple optimization requests concurrently.
    Maximum batch size: 10 requests.
    """
    if len(requests) > 10:
        raise HTTPException(status_code=400, detail="Batch size exceeded (max 10)")
    
    # Process requests concurrently
    tasks = [optimize_dispatch(req) for req in requests]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Separate successful results and errors
    response_list = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            response_list.append({
                "index": i,
                "status": "error",
                "error": str(result)
            })
        else:
            response_list.append(result.dict())
    
    return {
        "batch_size": len(requests),
        "results": response_list
    }


@app.get("/stats")
async def get_statistics():
    """Get server statistics."""
    stats = scheduler_manager.get_stats()
    
    return {
        "active_requests": stats['active_requests'],
        "total_requests_processed": stats['total_requests'],
        "uptime_seconds": stats['uptime_seconds'],
        "uptime_hours": stats['uptime_seconds'] / 3600
    }


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting HEMS API server...")
    
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=4,  # Multiple workers for concurrent request handling
        log_level="info"
    )

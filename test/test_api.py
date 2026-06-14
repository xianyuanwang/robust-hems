"""
Test suite for FastAPI HEMS Service

This module contains tests for the REST API endpoints,
including validation, concurrent access, and error handling.
"""

import sys
import os
import pytest
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient
from src.api_server import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'version' in data
    assert 'uptime_seconds' in data
    assert 'active_requests' in data
    
    print("✓ Health check test passed")


def test_optimize_milp_basic(client):
    """Test basic MILP optimization via API."""
    request_data = {
        "forecasts": {
            "load_forecast": [2.0, 3.0, 4.0, 2.5],
            "pv_forecast": [1.0, 2.0, 3.0, 1.5],
            "price_forecast": [0.10, 0.15, 0.25, 0.12]
        },
        "algorithm": "milp",
        "solver_type": "CBC"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'success'
    assert 'request_id' in data
    assert 'schedule' in data
    assert 'metrics' in data
    assert 'computation_time_ms' in data
    
    # Verify schedule structure
    schedule = data['schedule']
    assert len(schedule['charge']) == 4
    assert len(schedule['discharge']) == 4
    assert len(schedule['grid_import']) == 4
    assert len(schedule['soc']) == 4
    
    # Verify metrics
    metrics = data['metrics']
    assert metrics['total_cost'] >= 0
    assert metrics['self_consumption_rate'] >= 0
    
    print("✓ Basic MILP optimization API test passed")


def test_optimize_heuristic_basic(client):
    """Test basic heuristic optimization via API."""
    request_data = {
        "forecasts": {
            "load_forecast": [2.0, 3.0, 4.0],
            "pv_forecast": [1.0, 2.0, 1.5],
            "price_forecast": [0.10, 0.15, 0.25]
        },
        "algorithm": "heuristic"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'success'
    
    print("✓ Basic heuristic optimization API test passed")


def test_optimize_with_custom_battery_config(client):
    """Test optimization with custom battery configuration."""
    request_data = {
        "forecasts": {
            "load_forecast": [3.0, 4.0, 5.0],
            "pv_forecast": [1.0, 2.0, 2.5],
            "price_forecast": [0.12, 0.20, 0.28]
        },
        "battery_config": {
            "capacity": 20.0,
            "max_charge_power": 10.0,
            "max_discharge_power": 10.0,
            "efficiency_charge": 0.92,
            "efficiency_discharge": 0.93,
            "soc_min": 0.15,
            "soc_max": 0.95,
            "soc_initial": 0.6
        },
        "algorithm": "milp"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'success'
    
    print("✓ Custom battery config API test passed")


def test_optimize_validation_error(client):
    """Test input validation errors."""
    # Mismatched array lengths
    request_data = {
        "forecasts": {
            "load_forecast": [2.0, 3.0],
            "pv_forecast": [1.0],
            "price_forecast": [0.10, 0.15]
        },
        "algorithm": "milp"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 400
    
    print("✓ Validation error test passed")


def test_optimize_negative_values(client):
    """Test rejection of negative forecast values."""
    request_data = {
        "forecasts": {
            "load_forecast": [-2.0, 3.0, 4.0],
            "pv_forecast": [1.0, 2.0, 1.5],
            "price_forecast": [0.10, 0.15, 0.25]
        },
        "algorithm": "milp"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 422  # Validation error
    
    print("✓ Negative values test passed")


def test_optimize_invalid_algorithm(client):
    """Test invalid algorithm parameter."""
    request_data = {
        "forecasts": {
            "load_forecast": [2.0, 3.0],
            "pv_forecast": [1.0, 2.0],
            "price_forecast": [0.10, 0.15]
        },
        "algorithm": "invalid_algo"
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 422
    
    print("✓ Invalid algorithm test passed")


def test_batch_optimization(client):
    """Test batch optimization endpoint."""
    requests = [
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
    
    response = client.post("/optimize/batch", json=requests)
    assert response.status_code == 200
    
    data = response.json()
    assert data['batch_size'] == 2
    assert len(data['results']) == 2
    
    print("✓ Batch optimization test passed")


def test_batch_size_limit(client):
    """Test batch size limit enforcement."""
    # Create 11 requests (exceeds limit of 10)
    requests = [
        {
            "forecasts": {
                "load_forecast": [2.0],
                "pv_forecast": [1.0],
                "price_forecast": [0.10]
            },
            "algorithm": "milp"
        }
        for _ in range(11)
    ]
    
    response = client.post("/optimize/batch", json=requests)
    assert response.status_code == 400
    
    print("✓ Batch size limit test passed")


def test_statistics_endpoint(client):
    """Test statistics endpoint."""
    response = client.get("/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert 'active_requests' in data
    assert 'total_requests_processed' in data
    assert 'uptime_seconds' in data
    
    print("✓ Statistics endpoint test passed")


def test_concurrent_requests(client):
    """Test concurrent request handling."""
    import concurrent.futures
    
    def make_request(i):
        request_data = {
            "forecasts": {
                "load_forecast": [2.0 + i*0.1, 3.0 + i*0.1],
                "pv_forecast": [1.0 + i*0.1, 2.0 + i*0.1],
                "price_forecast": [0.10, 0.15]
            },
            "algorithm": "milp"
        }
        response = client.post("/optimize", json=request_data)
        return response.status_code
    
    # Send 5 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(5)]
        results = [f.result() for f in futures]
    
    # All should succeed
    assert all(status == 200 for status in results)
    
    print("✓ Concurrent requests test passed")


def test_multi_objective_weights(client):
    """Test multi-objective weight parameters."""
    request_data = {
        "forecasts": {
            "load_forecast": [3.0, 4.0, 5.0],
            "pv_forecast": [1.0, 2.0, 2.5],
            "price_forecast": [0.12, 0.20, 0.28]
        },
        "algorithm": "milp",
        "alpha": 1.0,
        "beta": 0.5,
        "gamma": 0.3
    }
    
    response = client.post("/optimize", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data['status'] == 'success'
    
    print("✓ Multi-objective weights test passed")


def run_all_tests():
    """Run all API tests."""
    print("=" * 70)
    print("Running FastAPI HEMS Service Tests")
    print("=" * 70)
    
    # Create test client
    client = TestClient(app)
    
    tests = [
        lambda: test_health_check(client),
        lambda: test_optimize_milp_basic(client),
        lambda: test_optimize_heuristic_basic(client),
        lambda: test_optimize_with_custom_battery_config(client),
        lambda: test_optimize_validation_error(client),
        lambda: test_optimize_negative_values(client),
        lambda: test_optimize_invalid_algorithm(client),
        lambda: test_batch_optimization(client),
        lambda: test_batch_size_limit(client),
        lambda: test_statistics_endpoint(client),
        lambda: test_concurrent_requests(client),
        lambda: test_multi_objective_weights(client),
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ Test failed: {e}")
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

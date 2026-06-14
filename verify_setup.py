"""
Verification Script for HEMS API Server

This script verifies that all dependencies are installed and
the API server can be imported correctly.
"""

import sys
import os


def check_dependencies():
    """Check if all required packages are installed."""
    print("Checking dependencies...")
    
    required_packages = [
        ('fastapi', 'FastAPI web framework'),
        ('uvicorn', 'ASGI server'),
        ('ortools', 'Google OR-Tools for MILP'),
        ('pydantic', 'Data validation'),
        ('numpy', 'Numerical computing'),
    ]
    
    all_ok = True
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {package:15} - {description}")
        except ImportError as e:
            print(f"  ✗ {package:15} - NOT INSTALLED")
            all_ok = False
    
    return all_ok


def check_imports():
    """Check if HEMS modules can be imported."""
    print("\nChecking HEMS module imports...")
    
    # Add src directory to path
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    modules_to_check = [
        ('milp_scheduler', 'MILP optimization engine'),
        ('hems_scheduler', 'Heuristic scheduler'),
        ('api_server', 'FastAPI service'),
    ]
    
    all_ok = True
    for module, description in modules_to_check:
        try:
            __import__(module)
            print(f"  ✓ {module:20} - {description}")
        except ImportError as e:
            print(f"  ✗ {module:20} - IMPORT ERROR: {e}")
            all_ok = False
    
    return all_ok


def check_api_server():
    """Check if API server can be instantiated."""
    print("\nChecking API server instantiation...")
    
    src_path = os.path.join(os.path.dirname(__file__), 'src')
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        from api_server import app
        print(f"  ✓ FastAPI app created successfully")
        print(f"  ✓ Routes: {len(app.routes)} endpoints registered")
        return True
    except Exception as e:
        print(f"  ✗ Failed to create API server: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 70)
    print("HEMS API Server Verification")
    print("=" * 70)
    print()
    
    # Check dependencies
    deps_ok = check_dependencies()
    if not deps_ok:
        print("\n❌ Some dependencies are missing.")
        print("Please install them with: pip install -r requirements.txt")
        return False
    
    # Check imports
    imports_ok = check_imports()
    if not imports_ok:
        print("\n❌ Some module imports failed.")
        print("Please check the error messages above.")
        return False
    
    # Check API server
    api_ok = check_api_server()
    if not api_ok:
        print("\n❌ API server initialization failed.")
        return False
    
    print("\n" + "=" * 70)
    print("✅ All checks passed! The API server is ready to start.")
    print("=" * 70)
    print("\nTo start the server:")
    print("  cd src")
    print("  python api_server.py")
    print("\nOr use the startup script:")
    print("  Windows: start_api.bat")
    print("  Linux/Mac: ./start_api.sh")
    print()
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

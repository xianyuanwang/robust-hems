#!/bin/bash
# HEMS API Server Startup Script

echo "=========================================="
echo "  HEMS AI Scheduling API Server"
echo "=========================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Virtual environment is not activated."
    echo "It's recommended to activate your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
fi

# Check if required packages are installed
echo "Checking dependencies..."
python -c "import fastapi, uvicorn, ortools" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: Required packages not found."
    echo "Please install dependencies:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

echo "✓ Dependencies OK"
echo ""

# Configuration
HOST=${HEMS_HOST:-"0.0.0.0"}
PORT=${HEMS_PORT:-8000}
WORKERS=${HEMS_WORKERS:-4}
LOG_LEVEL=${HEMS_LOG_LEVEL:-"info"}

echo "Starting API server..."
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Workers: $WORKERS"
echo "  Log Level: $LOG_LEVEL"
echo ""
echo "API Documentation will be available at:"
echo "  Swagger UI: http://localhost:${PORT}/docs"
echo "  ReDoc:      http://localhost:${PORT}/redoc"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=========================================="
echo ""

# Start the server
cd src
uvicorn api_server:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level $LOG_LEVEL

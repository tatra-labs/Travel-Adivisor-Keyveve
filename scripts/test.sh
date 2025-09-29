#!/bin/bash

# Travel Advisory Agent Test Script

set -e

echo "🧪 Running Travel Advisory Agent tests..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run backend tests
echo "🔧 Running backend tests..."
cd backend

# Run unit tests
echo "  📋 Unit tests..."
pytest tests/ -v --tb=short

# Run linting (if available)
if command -v flake8 &> /dev/null; then
    echo "  🔍 Linting..."
    flake8 app/ --max-line-length=120 --ignore=E203,W503
fi

# Run type checking (if available)
if command -v mypy &> /dev/null; then
    echo "  🔍 Type checking..."
    mypy app/ --ignore-missing-imports
fi

cd ..

# Test API endpoints
echo "🌐 Testing API endpoints..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "  ✅ Health endpoint working"
    
    # Test health check
    health_response=$(curl -s http://localhost:8000/health)
    if echo "$health_response" | grep -q '"status":"ok"'; then
        echo "  ✅ Health check passed"
    else
        echo "  ❌ Health check failed"
    fi
    
    # Test comprehensive health
    healthz_response=$(curl -s http://localhost:8000/healthz)
    if echo "$healthz_response" | grep -q '"status"'; then
        echo "  ✅ Comprehensive health check passed"
    else
        echo "  ❌ Comprehensive health check failed"
    fi
    
    # Test metrics
    metrics_response=$(curl -s http://localhost:8000/metrics)
    if echo "$metrics_response" | grep -q '"timestamp"'; then
        echo "  ✅ Metrics endpoint working"
    else
        echo "  ❌ Metrics endpoint failed"
    fi
    
else
    echo "  ⚠️  Backend not running. Start with ./scripts/start.sh to test API endpoints."
fi

# Test frontend (if running)
echo "🎨 Testing frontend..."
if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
    echo "  ✅ Frontend health check passed"
else
    echo "  ⚠️  Frontend not running. Start with ./scripts/start.sh to test frontend."
fi

echo ""
echo "🎉 All tests completed!"
echo ""
echo "To run specific test categories:"
echo "  Backend only: cd backend && pytest"
echo "  With coverage: cd backend && pytest --cov=app"
echo "  Specific test: cd backend && pytest tests/test_auth.py::test_password_hashing"


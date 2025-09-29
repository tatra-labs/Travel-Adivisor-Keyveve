#!/bin/bash

# Travel Advisory Agent Start Script

set -e

echo "🚀 Starting Travel Advisory Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env files exist
if [ ! -f ".env" ] || [ ! -f "backend/.env" ] || [ ! -f "frontend/.env" ]; then
    echo "❌ Environment files not found. Run ./scripts/setup.sh first."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Function to check if port is available
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        echo "❌ Port $1 is already in use"
        return 1
    fi
    return 0
}

# Check ports
if ! check_port 8000; then
    echo "Backend port 8000 is in use. Please stop the existing service or change the port."
    exit 1
fi

if ! check_port 8501; then
    echo "Frontend port 8501 is in use. Please stop the existing service or change the port."
    exit 1
fi

# Start backend in background
echo "🔧 Starting backend on port 8000..."
cd backend
python run.py &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        kill $BACKEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Start frontend in background
echo "🎨 Starting frontend on port 8501..."
cd frontend
python run.py &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
echo "⏳ Waiting for frontend to start..."
for i in {1..30}; do
    if curl -s http://localhost:8501/_stcore/health > /dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Frontend failed to start within 30 seconds"
        kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

echo ""
echo "🎉 Travel Advisory Agent is running!"
echo ""
echo "📱 Frontend: http://localhost:8501"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "❤️  Health Check: http://localhost:8000/healthz"
echo "📊 Metrics: http://localhost:8000/metrics"
echo ""
echo "Demo credentials: admin@example.com / admin123"
echo ""
echo "Press Ctrl+C to stop all services"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "✅ All services stopped"
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Wait for user to stop
wait


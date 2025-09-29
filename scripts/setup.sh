#!/bin/bash

# Travel Advisory Agent Setup Script

set -e

echo "🚀 Setting up Travel Advisory Agent..."

# Check if Python 3.11+ is available
python_version=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.11+ is required. Found: $python_version"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install backend dependencies
echo "📚 Installing backend dependencies..."
cd backend
pip install -r requirements.txt
pip install argon2-cffi PyPDF2 pytest pytest-asyncio
cd ..

# Install frontend dependencies
echo "🎨 Installing frontend dependencies..."
cd frontend
pip install -r requirements.txt
cd ..

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "⚠️  PostgreSQL not found. Please install PostgreSQL 14+ and pgvector extension."
    echo "   Ubuntu/Debian: sudo apt install postgresql postgresql-contrib"
    echo "   macOS: brew install postgresql"
    echo "   Then install pgvector: https://github.com/pgvector/pgvector"
else
    echo "✅ PostgreSQL found"
fi

# Copy environment files
echo "📝 Setting up environment files..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "⚠️  Please edit .env with your configuration (especially OPENAI_API_KEY)"
fi

if [ ! -f "backend/.env" ]; then
    cp backend/.env.example backend/.env
    echo "⚠️  Please edit backend/.env with your configuration"
fi

if [ ! -f "frontend/.env" ]; then
    cp frontend/.env.example frontend/.env
    echo "⚠️  Please edit frontend/.env with your configuration"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env files with your configuration"
echo "2. Set up PostgreSQL database:"
echo "   sudo -u postgres psql -c \"CREATE DATABASE travel_advisor;\""
echo "   sudo -u postgres psql -d travel_advisor -c \"CREATE EXTENSION vector;\""
echo "3. Run database migrations:"
echo "   cd backend && alembic upgrade head && python seed_data.py"
echo "4. Start the application:"
echo "   ./scripts/start.sh"
echo ""
echo "📖 See README.md for detailed instructions"


#!/bin/bash

# Travel Advisory Agent Setup Script
# This script helps you set up the Travel Advisory Agent project

set -e

echo "🌍 Travel Advisory Agent Setup"
echo "================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cat > .env << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# Database Configuration
DATABASE_URL=postgresql://travel_user:travel_password@postgres:5432/travel_db
POSTGRES_USER=travel_user
POSTGRES_PASSWORD=travel_password
POSTGRES_DB=travel_db

# Redis Configuration
REDIS_URL=redis://redis:6379

# Security Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
ENVIRONMENT=development

# API Configuration
API_V1_STR=/api/v1
PROJECT_NAME=Travel Advisory Agent

# CORS Settings
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8501"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
EOF
    echo "✅ .env file created"
    echo "⚠️  Please edit .env file and add your OpenAI API key"
else
    echo "✅ .env file already exists"
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads
mkdir -p logs
mkdir -p data

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
if docker-compose ps | grep -q "Up"; then
    echo "✅ Services are running successfully!"
    echo ""
    echo "🌐 Access URLs:"
    echo "   Frontend: http://localhost:8501"
    echo "   Backend API: http://localhost:8000"
    echo "   API Docs: http://localhost:8000/docs"
    echo ""
    echo "🔑 Default Login Credentials:"
    echo "   Admin: admin@example.com / admin123"
    echo "   User: user@example.com / user123"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Edit .env file and add your OpenAI API key"
    echo "   2. Restart services: docker-compose restart"
    echo "   3. Visit http://localhost:8501 to start using the app"
    echo ""
    echo "🎉 Setup complete! Happy traveling!"
else
    echo "❌ Some services failed to start. Check logs with:"
    echo "   docker-compose logs"
    exit 1
fi

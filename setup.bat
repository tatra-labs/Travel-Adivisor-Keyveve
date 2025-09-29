@echo off
REM Travel Advisory Agent Setup Script for Windows
REM This script helps you set up the Travel Advisory Agent project

echo 🌍 Travel Advisory Agent Setup
echo ================================

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker Desktop first.
    echo    Visit: https://docs.docker.com/desktop/windows/install/
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    echo    Visit: https://docs.docker.com/compose/install/
    pause
    exit /b 1
)

echo ✅ Docker and Docker Compose are installed

REM Create .env file if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from template...
    (
        echo # OpenAI Configuration
        echo OPENAI_API_KEY=your_openai_api_key_here
        echo OPENAI_API_BASE=https://api.openai.com/v1
        echo.
        echo # Database Configuration
        echo DATABASE_URL=postgresql://travel_user:travel_password@postgres:5432/travel_db
        echo POSTGRES_USER=travel_user
        echo POSTGRES_PASSWORD=travel_password
        echo POSTGRES_DB=travel_db
        echo.
        echo # Redis Configuration
        echo REDIS_URL=redis://redis:6379
        echo.
        echo # Security Configuration
        echo SECRET_KEY=your_super_secret_key_here_change_this_in_production
        echo ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo.
        echo # Application Settings
        echo DEBUG=False
        echo LOG_LEVEL=INFO
        echo ENVIRONMENT=development
        echo.
        echo # API Configuration
        echo API_V1_STR=/api/v1
        echo PROJECT_NAME=Travel Advisory Agent
        echo.
        echo # CORS Settings
        echo BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8501"]
        echo.
        echo # Rate Limiting
        echo RATE_LIMIT_PER_MINUTE=60
    ) > .env
    echo ✅ .env file created
    echo ⚠️  Please edit .env file and add your OpenAI API key
) else (
    echo ✅ .env file already exists
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist uploads mkdir uploads
if not exist logs mkdir logs
if not exist data mkdir data

REM Build and start services
echo 🐳 Building and starting Docker services...
docker-compose build

echo 🚀 Starting services...
docker-compose up -d

REM Wait for services to be ready
echo ⏳ Waiting for services to be ready...
timeout /t 10 /nobreak >nul

REM Check if services are running
echo 🔍 Checking service status...
docker-compose ps | findstr "Up" >nul
if %errorlevel% equ 0 (
    echo ✅ Services are running successfully!
    echo.
    echo 🌐 Access URLs:
    echo    Frontend: http://localhost:8501
    echo    Backend API: http://localhost:8000
    echo    API Docs: http://localhost:8000/docs
    echo.
    echo 🔑 Default Login Credentials:
    echo    Admin: admin@example.com / admin123
    echo    User: user@example.com / user123
    echo.
    echo 📋 Next Steps:
    echo    1. Edit .env file and add your OpenAI API key
    echo    2. Restart services: docker-compose restart
    echo    3. Visit http://localhost:8501 to start using the app
    echo.
    echo 🎉 Setup complete! Happy traveling!
) else (
    echo ❌ Some services failed to start. Check logs with:
    echo    docker-compose logs
    pause
    exit /b 1
)

pause

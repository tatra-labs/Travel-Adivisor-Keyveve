# Environment Setup Instructions

## Quick Start

1. **Create a `.env` file** in the project root with the following content:

```env
# OpenAI API Key (Required) - Get from https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Optional: Custom OpenAI API Base URL
OPENAI_API_BASE=https://api.openai.com/v1

# Optional: Custom secret key for JWT tokens
SECRET_KEY=your-secret-key-for-jwt-tokens-change-this-in-production

# Database (usually don't need to change)
DATABASE_URL=postgresql://postgres:postgres@localhost/travel_advisor

# Redis (usually don't need to change)
REDIS_URL=redis://localhost:6379

# Environment
ENVIRONMENT=development
```

2. **Replace `sk-your-openai-api-key-here`** with your actual OpenAI API key from https://platform.openai.com/api-keys

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

## Access the Application

- 🌐 **Frontend**: http://localhost:8501
- 🔧 **Backend API**: http://localhost:8000
- 📚 **API Documentation**: http://localhost:8000/docs

## Current Status

✅ All services are running and healthy
✅ Backend API is responding correctly
✅ Frontend is accessible
✅ Database and Redis are connected
✅ Basic AI functionality is working (without OpenAI API key, it will use fallback responses)

## Next Steps

1. Add your OpenAI API key to the `.env` file
2. Restart the services: `docker-compose restart`
3. Test the travel planning functionality
4. Record your demo video!

## Troubleshooting

If you encounter any issues:

- Check service status: `docker-compose ps`
- View logs: `docker-compose logs [service-name]`
- Restart services: `docker-compose restart`

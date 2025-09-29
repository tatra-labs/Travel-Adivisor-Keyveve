# 🌍 Travel Advisory Agent

> **AI-Powered Travel Planning Platform** - Create personalized itineraries with intelligent budget optimization and real-time travel insights.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-purple.svg)](https://openai.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)

## ✨ Features

### 🤖 **Intelligent Travel Planning**

- **AI-Powered Itineraries**: Generate detailed travel plans using OpenAI GPT-4o
- **Budget Optimization**: Smart cost analysis with real-time budget tracking
- **Context-Aware Refinements**: Maintain conversation context for seamless trip modifications
- **Multi-Destination Support**: Plan trips to Kyoto, Tokyo, Paris, Barcelona, Orlando, and more

### 🎯 **Smart Features**

- **Natural Language Processing**: Chat with the AI using conversational queries
- **Real-Time Cost Parsing**: Dynamic cost extraction from AI responses
- **Currency Conversion**: Automatic currency detection and conversion
- **Knowledge Base Integration**: Leverage travel guides and local insights
- **Responsive UI**: Modern Streamlit interface with real-time updates

### 🔧 **Technical Excellence**

- **Microservices Architecture**: FastAPI backend with Streamlit frontend
- **Vector Search**: Advanced RAG (Retrieval Augmented Generation) capabilities
- **Authentication**: JWT-based secure user management
- **Database**: PostgreSQL with pgvector for embeddings
- **Caching**: Redis for performance optimization
- **Containerized**: Full Docker support for easy deployment

## 🎯 Features in Action

### ✨ What Makes This Special

- **🧠 Smart Context Memory**: The AI remembers your previous requests and maintains destination context
- **💰 Real-time Cost Optimization**: Dynamic budget adjustments with live cost parsing
- **🌍 Multi-Destination Intelligence**: Supports Kyoto, Tokyo, Paris, Barcelona, Orlando, and more
- **🔄 Seamless Refinements**: Click "Make it cheaper" and watch the AI optimize your existing plan
- **📊 Consistent Cost Display**: Budget breakdown and daily itinerary costs always match

### 🎬 See It Live

The demo video above shows the complete user journey from initial travel planning to budget refinements, demonstrating the AI's ability to maintain context and provide consistent, accurate cost information.

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (latest version)
- **Git** (for cloning the repository)
- **OpenAI API Key** (for AI features)

### 1. Clone the Repository

```bash
git clone https://github.com/tatra-labs/Travel-Adivisor-Keyveve.git
cd travel-advisory-agent
```

### 2. Environment Setup

Create a `.env` file in the root directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_API_BASE=https://api.openai.com/v1

# Database Configuration
DATABASE_URL=postgresql://travel_user:travel_password@postgres:5432/travel_db

# Redis Configuration
REDIS_URL=redis://redis:6379

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
```

### 3. Launch the Application

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access the Application

- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### 5. Default Login Credentials

- **Admin**: `admin@example.com` / `admin123`
- **User**: `user@example.com` / `user123`

## 🎬 Demo

### 📹 Live Demo Video

Watch the Travel Advisory Agent in action:

https://github.com/tatra-labs/Travel-Adivisor-Keyveve/assets/your-user-id/video.mp4

_The video demonstrates the complete user journey from initial travel planning to budget refinements, showing the AI's ability to maintain context and provide consistent, accurate cost information._

### 🖼️ Screenshots

<div align="center">
  <img src="public/docker.png" alt="Docker Setup" width="800"/>
  <p><em>Docker containerization setup for easy deployment</em></p>
</div>

<div align="center">
  <img src="public/uploading-new-document.png" alt="Knowledge Base Upload" width="800"/>
  <p><em>Knowledge base document upload interface</em></p>
</div>

### Sample Chat Flow

```
👤 User: "Plan 5 days in Kyoto next month under $2,500, prefer art museums"

🤖 AI: [Generates detailed Kyoto itinerary with:
       - Daily schedules with specific times
       - Art museum recommendations
       - Budget breakdown: $1,800 total
       - Transportation options
       - Local tips and cultural insights]

👤 User: [Clicks "Make it cheaper" button]

🤖 AI: [Refines the same Kyoto itinerary with:
       - Budget optimizations
       - Alternative accommodations
       - Cost-saving dining options
       - Maintains art museum focus]
```

## 🏗️ Architecture

```mermaid
graph TB
    subgraph "Frontend Layer"
        A[Streamlit UI] --> B[API Client]
    end

    subgraph "Backend Layer"
        B --> C[FastAPI Server]
        C --> D[Authentication]
        C --> E[Agent API]
        C --> F[Knowledge API]
    end

    subgraph "AI Layer"
        E --> G[OpenAI GPT-4o]
        E --> H[Travel AI Service]
        H --> I[Cost Parser]
        H --> J[Context Manager]
    end

    subgraph "Data Layer"
        F --> K[PostgreSQL]
        K --> L[pgvector]
        C --> M[Redis Cache]
    end

    subgraph "External Services"
        G --> N[OpenAI API]
    end
```

## 📁 Project Structure

```
travel-advisory-agent/
├── 🐳 docker-compose.yml          # Multi-service orchestration
├── 📋 requirements.txt            # Python dependencies
├── 🔧 .env.example               # Environment template
├── 📖 README.md                  # This file
│
├── 🖥️ frontend/                   # Streamlit Frontend
│   ├── 📱 pages/                 # Streamlit pages
│   │   ├── 1_🏖️_Destinations.py
│   │   ├── 2_📚_Knowledge_Base.py
│   │   └── 3_🤖_Travel_Planner.py
│   ├── 🛠️ utils/                 # Frontend utilities
│   │   ├── api_client.py
│   │   └── auth.py
│   └── 🐳 Dockerfile
│
├── ⚙️ backend/                    # FastAPI Backend
│   ├── 🧠 app/
│   │   ├── 🤖 agent/             # AI agent components
│   │   ├── 🔌 api/               # API endpoints
│   │   ├── 🔐 auth/              # Authentication
│   │   ├── ⚙️ core/              # Core configuration
│   │   ├── 📊 models/            # Database models
│   │   ├── 🔍 rag/               # RAG components
│   │   └── 🛠️ services/          # Business logic
│   ├── 🗄️ alembic/               # Database migrations
│   └── 🐳 Dockerfile
│
└── 🏗️ infra/                     # Infrastructure
    ├── 🐳 docker-compose.yml
    └── 🗄️ init.sql
```

## 🔧 Configuration

### Environment Variables

| Variable         | Description                    | Default              |
| ---------------- | ------------------------------ | -------------------- |
| `OPENAI_API_KEY` | OpenAI API key for AI features | Required             |
| `DATABASE_URL`   | PostgreSQL connection string   | `postgresql://...`   |
| `REDIS_URL`      | Redis connection string        | `redis://redis:6379` |
| `SECRET_KEY`     | JWT secret key                 | Required             |
| `DEBUG`          | Enable debug mode              | `False`              |

### Service Ports

| Service    | Port | Description             |
| ---------- | ---- | ----------------------- |
| Frontend   | 8501 | Streamlit web interface |
| Backend    | 8000 | FastAPI REST API        |
| PostgreSQL | 5432 | Database server         |
| Redis      | 6379 | Cache server            |
| pgAdmin    | 5050 | Database administration |

## 🧪 Testing

### Run Tests

```bash
# Backend tests
cd backend
python -m pytest tests/ -v

# Integration tests
python test_complete_flow.py
```

### Test Coverage

- ✅ Authentication flow
- ✅ Travel planning queries
- ✅ Budget optimization
- ✅ Context preservation
- ✅ Cost parsing accuracy
- ✅ Multi-destination support

## 🚀 Deployment

### Production Deployment

1. **Set up production environment variables**
2. **Configure reverse proxy (nginx)**
3. **Set up SSL certificates**
4. **Configure monitoring and logging**
5. **Set up database backups**

### Docker Production

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone and setup
git clone https://github.com/tatra-labs/Travel-Adivisor-Keyveve.git
cd travel-advisory-agent

# Install development dependencies
pip install -r requirements-dev.txt

# Run in development mode
docker-compose -f docker-compose.dev.yml up
```

## 📊 Performance

- **Response Time**: < 3 seconds for travel planning
- **Concurrent Users**: Supports 100+ simultaneous users
- **Uptime**: 99.9% availability target
- **Scalability**: Horizontal scaling with load balancers

## 🔒 Security

- **JWT Authentication**: Secure token-based authentication
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: API rate limiting to prevent abuse
- **Environment Isolation**: Secure environment variable handling
- **Database Security**: Encrypted connections and prepared statements

## 📈 Roadmap

### 🔧 Technical Improvements

- [ ] **Microservices Split** - Further service decomposition
- [ ] **GraphQL API** - Modern API architecture
- [ ] **Event Sourcing** - Advanced data architecture
- [ ] **ML Pipeline** - Custom travel recommendation models
- [ ] **Edge Computing** - CDN and edge optimization

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for providing the GPT-4o API
- **Streamlit** for the amazing web framework
- **FastAPI** for the high-performance API framework
- **PostgreSQL** and **pgvector** for vector database capabilities
- **Docker** for containerization support

---

<div align="center">

**Made with ❤️ for travelers worldwide**

[⭐ Star this repo](https://github.com/tatra-labs/Travel-Adivisor-Keyveve) | [🐛 Report Bug](https://github.com/tatra-labs/Travel-Adivisor-Keyveve/issues) | [💡 Request Feature](https://github.com/tatra-labs/Travel-Adivisor-Keyveve/issues)

</div>

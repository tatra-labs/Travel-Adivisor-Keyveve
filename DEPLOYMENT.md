# 🚀 Deployment Guide

This guide covers different deployment scenarios for the Travel Advisory Agent.

## 📋 Prerequisites

- Docker & Docker Compose
- OpenAI API Key
- Domain name (for production)
- SSL certificate (for production)

## 🏠 Local Development

### Quick Start

```bash
# Clone the repository
git clone https://github.com/yourusername/travel-advisory-agent.git
cd travel-advisory-agent

# Run setup script
./setup.sh  # Linux/Mac
# or
setup.bat   # Windows

# Access the application
# Frontend: http://localhost:8501
# Backend: http://localhost:8000
```

### Manual Setup

```bash
# 1. Create environment file
cp .env.example .env
# Edit .env with your OpenAI API key

# 2. Start services
docker-compose up -d

# 3. Check status
docker-compose ps
```

## 🌐 Production Deployment

### 1. Server Setup

**Recommended Server Specs:**

- CPU: 2+ cores
- RAM: 4GB+
- Storage: 20GB+
- OS: Ubuntu 20.04+ or CentOS 8+

### 2. Environment Configuration

```bash
# Create production environment
cat > .env.prod << EOF
# OpenAI Configuration
OPENAI_API_KEY=your_production_openai_key
OPENAI_API_BASE=https://api.openai.com/v1

# Database Configuration
DATABASE_URL=postgresql://travel_user:secure_password@postgres:5432/travel_db
POSTGRES_USER=travel_user
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=travel_db

# Security Configuration
SECRET_KEY=$(openssl rand -hex 32)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Application Settings
DEBUG=False
LOG_LEVEL=INFO
ENVIRONMENT=production

# CORS Settings
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]
EOF
```

### 3. Docker Production Setup

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Reverse Proxy (Nginx)

```nginx
# /etc/nginx/sites-available/travel-advisory-agent
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;

    # Frontend (Streamlit)
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://localhost:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. SSL Certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## ☁️ Cloud Deployment

### AWS Deployment

1. **EC2 Instance Setup**:

   ```bash
   # Launch EC2 instance (t3.medium or larger)
   # Install Docker
   sudo apt update
   sudo apt install docker.io docker-compose
   sudo usermod -aG docker $USER
   ```

2. **RDS Database**:

   - Create PostgreSQL RDS instance
   - Update DATABASE_URL in .env

3. **ElastiCache Redis**:

   - Create Redis cluster
   - Update REDIS_URL in .env

4. **Load Balancer**:
   - Configure Application Load Balancer
   - Set up health checks

### Google Cloud Platform

1. **Compute Engine**:

   ```bash
   # Create VM instance
   gcloud compute instances create travel-agent \
     --image-family=ubuntu-2004-lts \
     --image-project=ubuntu-os-cloud \
     --machine-type=e2-medium
   ```

2. **Cloud SQL**:

   - Create PostgreSQL instance
   - Configure connection

3. **Cloud Memorystore**:
   - Create Redis instance
   - Update configuration

### Azure Deployment

1. **Virtual Machine**:

   ```bash
   # Create VM
   az vm create \
     --resource-group myResourceGroup \
     --name travel-agent-vm \
     --image UbuntuLTS \
     --size Standard_B2s
   ```

2. **Azure Database**:

   - Create PostgreSQL Flexible Server
   - Configure firewall rules

3. **Azure Cache**:
   - Create Redis Cache
   - Update connection strings

## 🐳 Docker Compose Configurations

### Development

```yaml
# docker-compose.dev.yml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: travel_db
      POSTGRES_USER: travel_user
      POSTGRES_PASSWORD: travel_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://travel_user:travel_password@postgres:5432/travel_db
      - REDIS_URL=redis://redis:6379
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend
    volumes:
      - ./frontend:/app
    command: streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### Production

```yaml
# docker-compose.prod.yml
version: "3.8"
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  postgres_data:
```

## 📊 Monitoring & Logging

### Health Checks

```bash
# Backend health check
curl http://localhost:8000/health

# Frontend health check
curl http://localhost:8501/_stcore/health
```

### Log Management

```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Log rotation
# Add to /etc/logrotate.d/docker
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=1M
    missingok
    delaycompress
    copytruncate
}
```

### Monitoring Setup

1. **Prometheus + Grafana**:

   ```yaml
   # Add to docker-compose.prod.yml
   prometheus:
     image: prom/prometheus
     ports:
       - "9090:9090"
     volumes:
       - ./prometheus.yml:/etc/prometheus/prometheus.yml

   grafana:
     image: grafana/grafana
     ports:
       - "3000:3000"
     environment:
       - GF_SECURITY_ADMIN_PASSWORD=admin
   ```

2. **Application Metrics**:
   - Response times
   - Error rates
   - API usage
   - Database performance

## 🔒 Security Considerations

### Production Security

1. **Environment Variables**:

   - Use strong, unique passwords
   - Rotate API keys regularly
   - Never commit secrets to version control

2. **Network Security**:

   - Use HTTPS only
   - Configure firewall rules
   - Enable DDoS protection

3. **Database Security**:

   - Enable SSL connections
   - Use strong passwords
   - Regular backups
   - Access control

4. **Application Security**:
   - Regular security updates
   - Input validation
   - Rate limiting
   - CORS configuration

## 🔄 Backup & Recovery

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U travel_user travel_db > backup.sql

# Restore backup
docker-compose exec -T postgres psql -U travel_user travel_db < backup.sql

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec postgres pg_dump -U travel_user travel_db > "backup_${DATE}.sql"
aws s3 cp "backup_${DATE}.sql" s3://your-backup-bucket/
```

### Application Backup

```bash
# Backup application data
tar -czf app_backup_$(date +%Y%m%d).tar.gz uploads/ logs/

# Backup configuration
cp .env env_backup_$(date +%Y%m%d)
```

## 🚨 Troubleshooting

### Common Issues

1. **Services Won't Start**:

   ```bash
   # Check logs
   docker-compose logs

   # Check port conflicts
   netstat -tulpn | grep :8000
   ```

2. **Database Connection Issues**:

   ```bash
   # Test database connection
   docker-compose exec postgres psql -U travel_user -d travel_db -c "SELECT 1;"
   ```

3. **API Errors**:

   ```bash
   # Check backend logs
   docker-compose logs backend

   # Test API endpoint
   curl http://localhost:8000/health
   ```

### Performance Optimization

1. **Database Optimization**:

   - Add indexes for frequently queried columns
   - Optimize queries
   - Monitor slow queries

2. **Caching**:

   - Enable Redis caching
   - Cache API responses
   - Use CDN for static assets

3. **Scaling**:
   - Horizontal scaling with load balancer
   - Database read replicas
   - Microservices architecture

## 📞 Support

For deployment issues:

- Check the [GitHub Issues](https://github.com/yourusername/travel-advisory-agent/issues)
- Review the [Documentation](https://github.com/yourusername/travel-advisory-agent/wiki)
- Contact: support@traveladvisoryagent.com

# TETRIX Hospital Bot

Telegram bot system for TETRIX token holders with metrics tracking and user management.

## TODO
- Move message formatting to HTML
- Make invites by link
- Onreload - don't request all parameters, use them from redis cache
- make text for all steps more understandable 

## Local Development Setup

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- Redis 7+
- Node.js 18+ (for frontend)

### Environment Setup

1. Create virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

3. Install and start services (macOS):
```bash
brew install postgresql@15 redis
brew services start postgresql@15
brew services start redis
```

4. Create `.env` file in project root:
```env
# Required environment variables
BACKEND_URL=http://localhost:5000  # or your domain in production
FRONTEND_URL=http://localhost:3000 # or your frontend URL in production
TELEGRAM_BOT_TOKEN=your_bot_token  # from @BotFather
JWT_SECRET_KEY=your_secret_key     # for JWT token generation
OPENAI_API_KEY=your_openai_key     # from OpenAI platform

# Optional development variables (defaults shown)
FLASK_ENV=development              # development/production
POSTGRES_USER=tetrix              # default user
POSTGRES_DB=tetrix               # default database
REDIS_HOST=redis                # redis in docker, localhost for dev
REDIS_PORT=6379                # default Redis port
```

### Database Setup

1. Create database:
```bash
createdb tetrix
```

2. Initialize database:
```bash
cd backend
python setup_db.py
```

### Running the Application

#### Local Development (without Docker)

1. Start backend:
```bash
cd backend
python app.py
```

2. Start frontend:
```bash
cd frontend
npm install
npm start
```

#### Production with Docker

```bash
docker-compose up -d
```

## Production Deployment

### Prerequisites
- Domain with SSL certificate
- Docker and Docker Compose
- GitHub account (for CI/CD)

### GitHub Actions Setup

1. Go to your repository's Settings → Secrets and variables → Actions
2. Add the following secrets:
   ```
   # Required secrets
   TELEGRAM_BOT_TOKEN     - Your Telegram bot token from @BotFather
   JWT_SECRET_KEY         - Secret key for JWT token generation
   PROD_SSH_KEY          - Private SSH key for deployment
   OPENAI_API_KEY        - Your OpenAI API key from platform.openai.com

   # Required variables
   BACKEND_URL          - Your backend URL (e.g., https://api.your-domain.com)
   FRONTEND_URL         - Your frontend URL (e.g., https://your-domain.com)
   ```

3. Generate SSH key for deployment:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions"
   # Add public key to production server's ~/.ssh/authorized_keys
   # Add private key to GitHub secrets as PROD_SSH_KEY
   ```

### Configuration

1. Configure SSL:
```bash
mkdir -p nginx/ssl
# Place your SSL certificates in nginx/ssl:
# - certificate.crt
# - private.key
```

2. The system will automatically:
   - Parse domain from BACKEND_URL
   - Configure nginx with the domain
   - Generate self-signed SSL certificate if none exists

### Deployment Methods

#### 1. Automated Deployment (GitHub Actions)

The CI/CD pipeline automatically:
- Detects changed services (backend, frontend, nginx)
- Runs tests for changed services
- Builds and pushes Docker images
- Updates only the changed services in production
- Verifies deployment health

Triggers on pushes to main branch that modify:
- `backend/**`
- `frontend/**`
- `nginx/**`
- `docker-compose.prod.yml`

#### 2. Manual Deployment

##### Full System Deployment
```bash
# Pull all latest images
docker-compose -f docker-compose.prod.yml pull

# Update all services
docker-compose -f docker-compose.prod.yml up -d
```

##### Single Service Updates
```bash
# Update specific service (e.g., backend)
docker-compose -f docker-compose.prod.yml pull app
docker-compose -f docker-compose.prod.yml up -d --no-deps --build app

# Update configuration only (e.g., nginx)
docker-compose -f docker-compose.prod.yml up -d --no-deps nginx

# Force rebuild specific service
docker-compose -f docker-compose.prod.yml up -d --no-deps --build nginx
```

##### Update Multiple Services
```bash
# Update specific services
docker-compose -f docker-compose.prod.yml up -d --no-deps --build nginx app redis
```

### Volume Management

Data persistence is handled through Docker named volumes:
```yaml
volumes:
  postgres_data:    # Database files
  redis_data:      # Redis data
  prometheus_data: # Metrics
  grafana_data:   # Dashboards
```

These volumes persist:
- Between service restarts
- During deployments
- After container removal

### Monitoring Deployment

1. Check service logs:
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f app
```

2. Check service health:
```bash
# Backend health
curl http://localhost:5000/health

# Container status
docker-compose -f docker-compose.prod.yml ps
```

3. Monitor metrics:
- Prometheus: http://your-domain:9090
- Grafana: http://your-domain:3000

### Backup

1. Automated backups:
```bash
# Run backup script
./scripts/backup.sh
```

2. Manual volume backup:
```bash
# Backup volume data
docker run --rm -v tetrix_postgres_data:/data -v /backup:/backup alpine tar czf /backup/postgres_data.tar.gz /data

# Restore volume data
docker run --rm -v tetrix_postgres_data:/data -v /backup:/backup alpine tar xzf /backup/postgres_data.tar.gz
```

### Troubleshooting

1. Check service health:
```bash
docker-compose -f docker-compose.prod.yml ps
```

2. View service logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f [service_name]
```

3. Restart specific service:
```bash
docker-compose -f docker-compose.prod.yml restart [service_name]
```

4. Clean up:
```bash
# Remove unused images
docker image prune -f

# Remove unused volumes (careful!)
docker volume prune -f
```

## Architecture

### Components
- Flask Backend API
- React Frontend
- Telegram Bot (webhook-based)
- PostgreSQL Database
- Redis Cache
- Nginx Reverse Proxy
- Prometheus Metrics
- Grafana Dashboards

### Features
- TON Wallet Integration
- User Authentication
- Metrics Collection
- Rate Limiting
- Caching
- Health Monitoring

## API Documentation

Swagger UI available at: `http://localhost:5000/apidocs`

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request 

## Frontend Environment Variables

Required environment variables for the frontend application:

- `VITE_BACKEND_URL`: URL of the backend API (e.g., https://api.your-domain.com)
- `VITE_FRONTEND_URL`: URL of the frontend application (e.g., https://tetrix-hospital.pages.dev)

These variables need to be set in Cloudflare Pages environment settings for production deployment.

## Cloudflare Pages Setup

Set these environment variables in Cloudflare Pages settings:

```
VITE_BACKEND_URL=https://api.your-domain.com
VITE_FRONTEND_URL=https://your-cf-pages-domain.pages.dev
```
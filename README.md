# TETRIX Hospital Bot

Telegram bot system for TETRIX token holders with metrics tracking and user management.

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
# Database
DATABASE_URL=postgresql://localhost:5432/tetrix
POSTGRES_USER=your_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=tetrix

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
WEBHOOK_URL=https://your-domain.com  # or ngrok URL for local testing

# Security
JWT_SECRET_KEY=your_secret_key
FLASK_SECRET_KEY=another_secret_key

# Environment
FLASK_ENV=development
FLASK_DEBUG=1
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
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

#### Development with Docker

```bash
docker-compose -f docker-compose.dev.yml up
```

#### Production with Docker

```bash
docker-compose -f docker-compose.prod.yml up
```

## Production Deployment

### Prerequisites
- Domain with SSL certificate
- Docker and Docker Compose
- PostgreSQL database (can be containerized or external)
- Redis instance (can be containerized or external)
- Docker Hub account (for CI/CD)

### GitHub Actions Setup

1. Go to your repository's Settings → Secrets and variables → Actions
2. Add the following secrets:
   ```
   # Docker Hub Credentials
   DOCKER_HUB_USERNAME    - Your Docker Hub username
   DOCKER_HUB_TOKEN       - Your Docker Hub access token (not password)

   # Production Server Details
   PROD_HOST             - Your production server IP/domain
   PROD_USERNAME         - SSH username for production server
   PROD_SSH_KEY          - Private SSH key for authentication
   ```

3. Generate Docker Hub token:
   - Go to Docker Hub → Account Settings → Security
   - Click "New Access Token"
   - Give it a name and copy the token

4. Generate SSH key for deployment:
   ```bash
   ssh-keygen -t ed25519 -C "github-actions"
   # Add public key to production server's ~/.ssh/authorized_keys
   # Add private key to GitHub secrets as PROD_SSH_KEY
   ```

### Configuration

1. Create `secrets` directory:
```bash
mkdir secrets
echo "your-postgres-password" > secrets/postgres_password.txt
echo "your-grafana-password" > secrets/grafana_password.txt
```

2. Configure SSL:
```bash
mkdir -p nginx/ssl
# Place your SSL certificates in nginx/ssl:
# - fullchain.pem
# - privkey.pem
```

3. Update production environment variables in `.env.prod`

### Deployment

1. Build and start services:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. Monitor logs:
```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Monitoring

- Prometheus: http://your-domain:9090
- Grafana: http://your-domain:3000

### Backup

Automated backups are configured in `scripts/backup.sh`. Run manually:
```bash
./scripts/backup.sh
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
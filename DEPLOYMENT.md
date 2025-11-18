# Deployment Guide

This guide covers multiple deployment options for the Water Utilities Financial Analysis Platform.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Production Checklist](#production-checklist)

---

## Local Development

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Node.js 18+ (for frontend)
- 100GB+ free disk space (for PDFs)

### Setup Steps

1. **Clone Repository**
```bash
git clone <repo-url>
cd Water-Utilities-Finances-Database
```

2. **Install Python Dependencies**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Setup Database**
```bash
# Make sure PostgreSQL is running
python run_pipeline.py --setup
```

4. **Generate Sample Data** (Optional)
```bash
python run_pipeline.py --generate-data --utilities 20 --years 10
```

5. **Start Backend API**
```bash
cd api
python main.py
# API available at http://localhost:8000
```

6. **Start Frontend** (Optional)
```bash
cd frontend
npm install
npm run dev
# Dashboard at http://localhost:5173
```

### Local Development Costs

**Total: $0** (Everything runs on your machine)

---

## Docker Deployment

### Quick Start with Docker Compose

1. **Set Environment Variables**
```bash
# Create .env file
cat > .env << EOF
DB_PASSWORD=your_secure_password
EOF
```

2. **Start All Services**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL database (port 5432)
- Backend API (port 8000)

3. **Initialize Database**
```bash
docker-compose exec api python database/db_setup.py init
```

4. **Generate Sample Data** (Optional)
```bash
docker-compose exec api python tests/generate_sample_data.py --utilities 10
```

5. **Access API**
```
http://localhost:8000
http://localhost:8000/docs  # Swagger UI
```

### Docker Commands

```bash
# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Stop and remove volumes (deletes data!)
docker-compose down -v

# Rebuild after code changes
docker-compose up --build
```

### Docker Deployment Costs

**Local Docker:** $0
**Cloud Docker (optional):**
- AWS ECS: ~$30/month (t3.small)
- DigitalOcean: ~$12/month (Basic Droplet)
- Google Cloud Run: ~$15/month

---

## Cloud Deployment

### Option 1: AWS (Moderate Cost)

#### Architecture
```
AWS Infrastructure:
├── RDS PostgreSQL (db.t3.micro)
├── ECS Fargate (API containers)
├── S3 (PDF storage)
├── CloudFront (CDN for frontend)
└── Route 53 (DNS)
```

#### Setup Steps

1. **Create RDS PostgreSQL Instance**
```bash
aws rds create-db-instance \
  --db-instance-identifier water-utilities-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username wateradmin \
  --master-user-password <password> \
  --allocated-storage 20
```

2. **Build and Push Docker Image**
```bash
# Authenticate to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -t water-utilities-api .

# Tag
docker tag water-utilities-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/water-utilities-api:latest

# Push
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/water-utilities-api:latest
```

3. **Create ECS Task Definition**

See `deploy/aws/task-definition.json` (create this file)

4. **Deploy Frontend to S3**
```bash
cd frontend
npm run build
aws s3 sync dist/ s3://water-utilities-frontend
```

5. **Setup CloudFront Distribution**
```bash
aws cloudfront create-distribution \
  --origin-domain-name water-utilities-frontend.s3.amazonaws.com \
  --default-root-object index.html
```

#### AWS Costs (Estimated Monthly)

- RDS (db.t3.micro): $15
- ECS Fargate (0.25 vCPU): $12
- S3 Storage (100GB): $2
- Data Transfer: $5
- CloudFront: $1
**Total: ~$35/month**

### Option 2: DigitalOcean (Lower Cost)

#### Architecture
```
DigitalOcean Setup:
├── Droplet (4GB RAM)
├── Managed PostgreSQL (Starter)
└── Spaces (Object Storage)
```

#### Setup Steps

1. **Create Droplet**
```bash
doctl compute droplet create water-utilities \
  --region nyc1 \
  --size s-2vcpu-4gb \
  --image ubuntu-22-04-x64 \
  --ssh-keys <your-ssh-key-id>
```

2. **SSH into Droplet**
```bash
ssh root@<droplet-ip>
```

3. **Install Docker**
```bash
curl -fsSL https://get.docker.com | sh
```

4. **Clone Repository**
```bash
git clone <repo-url>
cd Water-Utilities-Finances-Database
```

5. **Setup Environment**
```bash
# Create .env
nano .env
# Add:
# DB_HOST=<managed-db-host>
# DB_PASSWORD=<password>
```

6. **Start Services**
```bash
docker-compose up -d
```

7. **Configure Nginx Reverse Proxy**
```bash
apt install nginx
nano /etc/nginx/sites-available/water-utilities
```

Add:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/water-utilities /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

8. **Setup SSL (Free with Let's Encrypt)**
```bash
apt install certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
```

#### DigitalOcean Costs (Estimated Monthly)

- Droplet (4GB): $24
- Managed PostgreSQL (Starter): $15
- Spaces (100GB): $5
**Total: ~$44/month**

### Option 3: Heroku (Easiest, Moderate Cost)

#### Setup Steps

1. **Install Heroku CLI**
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

2. **Login and Create App**
```bash
heroku login
heroku create water-utilities-api
```

3. **Add PostgreSQL**
```bash
heroku addons:create heroku-postgresql:mini
```

4. **Configure Environment**
```bash
heroku config:set DB_HOST=$(heroku pg:credentials:url DATABASE_URL | grep Host | awk '{print $2}')
```

5. **Deploy**
```bash
git push heroku main
```

6. **Initialize Database**
```bash
heroku run python database/db_setup.py init
```

#### Heroku Costs (Estimated Monthly)

- Dyno (Basic): $7
- PostgreSQL (Mini): $5
**Total: ~$12/month** (smallest option)

### Option 4: Vercel/Netlify (Frontend) + Render (Backend)

**Frontend (Vercel/Netlify):** Free
**Backend (Render):** $7/month
**Database (Render PostgreSQL):** $7/month
**Total: ~$14/month**

---

## Production Checklist

### Security

- [ ] Change default database password
- [ ] Enable HTTPS/SSL
- [ ] Set up firewall rules
- [ ] Enable database backups
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting on API
- [ ] Add API authentication (optional)
- [ ] Regular security updates

### Performance

- [ ] Enable database connection pooling
- [ ] Add Redis cache layer (optional)
- [ ] Optimize database queries with indexes
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets
- [ ] Monitor API response times

### Monitoring

- [ ] Set up logging (CloudWatch, Loggly, or DataDog)
- [ ] Configure alerts for errors
- [ ] Monitor database performance
- [ ] Track API usage
- [ ] Set up uptime monitoring

### Backup Strategy

- [ ] Automated daily database backups
- [ ] PDF storage backups
- [ ] Test restore procedures
- [ ] Document backup locations
- [ ] Set retention policies (30-90 days)

### Cost Optimization

- [ ] Use spot instances for batch processing
- [ ] Implement S3 lifecycle policies
- [ ] Schedule non-critical tasks for off-peak hours
- [ ] Monitor and optimize database queries
- [ ] Use database read replicas judiciously

---

## Environment Variables

Create a `.env` file with:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=water_utilities
DB_USER=postgres
DB_PASSWORD=your_secure_password

# API
API_HOST=0.0.0.0
API_PORT=8000
DATA_DIR=./data

# Frontend (optional)
VITE_API_URL=http://localhost:8000
```

---

## Scaling Considerations

### Horizontal Scaling

When you reach 1,000+ concurrent users:

1. **Load Balancer**
   - AWS ALB or DigitalOcean Load Balancer
   - Distribute traffic across multiple API instances

2. **Database Scaling**
   - Read replicas for analytics queries
   - Connection pooling (PgBouncer)
   - Consider sharding by state

3. **Caching**
   - Redis for API responses
   - Cache aggregated statistics
   - 15-minute TTL for dashboard data

### Vertical Scaling

Increase resources as needed:
- Start: 2GB RAM, 1 vCPU
- Light usage: 4GB RAM, 2 vCPU
- Medium usage: 8GB RAM, 4 vCPU
- Heavy usage: 16GB RAM, 8 vCPU

---

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql -h localhost -U water_user -d water_utilities

# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres
```

### API Not Starting

```bash
# Check logs
docker-compose logs api

# Restart service
docker-compose restart api

# Rebuild
docker-compose up --build api
```

### Frontend Not Loading

```bash
# Check API is accessible
curl http://localhost:8000/api/stats

# Verify CORS settings in api/main.py
# Make sure frontend URL is in allow_origins
```

---

## Cost Comparison Summary

| Option | Setup Difficulty | Monthly Cost | Best For |
|--------|------------------|--------------|----------|
| **Local** | Easy | $0 | Development, Testing |
| **Docker (Local)** | Medium | $0 | Development, Small Team |
| **Heroku** | Easy | $12-50 | Quick Deploy, MVP |
| **DigitalOcean** | Medium | $25-50 | Production, Custom Control |
| **AWS** | Hard | $35-100 | Enterprise, High Scale |
| **Vercel+Render** | Easy | $14-30 | Startups, Small Projects |

---

## Next Steps

1. Choose deployment option based on your needs and budget
2. Follow setup steps for chosen option
3. Initialize database with schema
4. Generate or collect real data
5. Configure monitoring and backups
6. Set up custom domain (optional)
7. Enable HTTPS
8. Launch! 🚀

---

## Support

For deployment issues:
1. Check logs for error messages
2. Verify environment variables are set
3. Ensure all services are running
4. Test database connectivity
5. Check firewall/security group rules

**Remember: You can run the entire stack locally for $0!**

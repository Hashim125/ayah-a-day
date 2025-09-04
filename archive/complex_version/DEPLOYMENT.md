# Ayah App Deployment Guide

This guide covers deploying the Ayah App in various environments, from development to production.

## Table of Contents
- [Quick Start (Development)](#quick-start-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Email Setup](#email-setup)
- [Monitoring & Maintenance](#monitoring--maintenance)

## Quick Start (Development)

### Prerequisites
- Python 3.8+
- pip or poetry
- Git

### Local Development Setup

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd ayah-a-day
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -e .[dev]
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Move Data Files**
   ```bash
   # Move your JSON data files to the data/ directory
   mv data/qpc-hafs.json ./data/
   mv data/en-taqi-usmani-simple.json ./data/
   mv data/en-tafisr-ibn-kathir.json ./data/
   ```

4. **Run Development Server**
   ```bash
   python -m src.ayah_app.app
   # Or using Flask CLI:
   flask run --debug
   ```

   Visit http://localhost:5000

## Production Deployment

### System Requirements
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- Nginx
- PostgreSQL (optional, can use SQLite)
- Redis (for caching and background tasks)
- SSL certificate for HTTPS

### Production Setup

1. **Server Preparation**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y
   
   # Install dependencies
   sudo apt install -y python3-pip python3-venv nginx postgresql redis-server git
   ```

2. **Application Setup**
   ```bash
   # Create application user
   sudo useradd -r -s /bin/bash -d /opt/ayah-app ayah
   sudo mkdir -p /opt/ayah-app
   sudo chown ayah:ayah /opt/ayah-app
   
   # Switch to app user
   sudo su - ayah
   
   # Clone and setup
   git clone <repository-url> /opt/ayah-app
   cd /opt/ayah-app
   
   python3 -m venv venv
   source venv/bin/activate
   pip install -e .
   ```

3. **Database Setup** (PostgreSQL)
   ```bash
   sudo -u postgres createuser ayah_user
   sudo -u postgres createdb ayah_db -O ayah_user
   sudo -u postgres psql -c "ALTER USER ayah_user PASSWORD 'secure_password';"
   ```

4. **Configuration**
   ```bash
   cp .env.example .env
   # Edit .env for production settings:
   FLASK_ENV=production
   DEBUG=False
   SECRET_KEY=your-very-secure-secret-key
   DATABASE_URL=postgresql://ayah_user:secure_password@localhost/ayah_db
   # ... other production settings
   ```

5. **Systemd Service**
   Create `/etc/systemd/system/ayah-app.service`:
   ```ini
   [Unit]
   Description=Ayah App
   After=network.target
   
   [Service]
   Type=exec
   User=ayah
   WorkingDirectory=/opt/ayah-app
   Environment=PATH=/opt/ayah-app/venv/bin
   ExecStart=/opt/ayah-app/venv/bin/gunicorn --bind unix:/opt/ayah-app/ayah-app.sock --workers 4 src.ayah_app.app:create_app()
   Restart=always
   
   [Install]
   WantedBy=multi-user.target
   ```

6. **Nginx Configuration**
   Create `/etc/nginx/sites-available/ayah-app`:
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       
       location / {
           include proxy_params;
           proxy_pass http://unix:/opt/ayah-app/ayah-app.sock;
       }
       
       location /static/ {
           alias /opt/ayah-app/static/;
           expires 30d;
           add_header Cache-Control "public, immutable";
       }
   }
   ```

7. **Enable and Start Services**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ayah-app
   sudo systemctl start ayah-app
   
   sudo ln -s /etc/nginx/sites-available/ayah-app /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

## Docker Deployment

### Using Docker Compose (Recommended)

1. **Setup**
   ```bash
   git clone <repository-url>
   cd ayah-a-day
   
   # Copy environment file
   cp .env.example .env
   # Edit .env with your settings
   ```

2. **Development**
   ```bash
   docker-compose up --build
   ```

3. **Production**
   ```bash
   # Use production profile
   docker-compose --profile production up -d --build
   
   # Or with override file
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

### Docker Standalone

```bash
# Build image
docker build -t ayah-app .

# Run container
docker run -d \
  --name ayah-app \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data:ro \
  -e SECRET_KEY=your-secret-key \
  -e MAIL_USERNAME=your-email \
  -e MAIL_PASSWORD=your-password \
  ayah-app
```

## Cloud Deployment

### Heroku

1. **Prepare for Heroku**
   ```bash
   # Create Procfile
   echo "web: gunicorn src.ayah_app.app:create_app()" > Procfile
   
   # Create runtime.txt
   echo "python-3.11.0" > runtime.txt
   ```

2. **Deploy**
   ```bash
   heroku create your-app-name
   heroku config:set SECRET_KEY=your-secret-key
   heroku config:set MAIL_USERNAME=your-email
   heroku config:set MAIL_PASSWORD=your-password
   
   git push heroku main
   ```

### AWS/DigitalOcean/VPS

1. **Using Docker**
   - Use the Docker setup above
   - Configure load balancer/reverse proxy
   - Set up SSL termination
   - Configure auto-scaling if needed

2. **Using systemd**
   - Follow the production setup guide
   - Configure firewall rules
   - Set up monitoring and backups

## Email Setup

### Gmail Configuration

1. **Enable 2-Factor Authentication** on your Gmail account

2. **Create App Password**
   - Go to Google Account settings
   - Security > 2-Step Verification > App passwords
   - Generate password for "Mail"

3. **Environment Variables**
   ```env
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USE_TLS=True
   MAIL_USERNAME=your-email@gmail.com
   MAIL_PASSWORD=your-app-password
   ```

### Other Email Providers

**SendGrid:**
```env
MAIL_SERVER=smtp.sendgrid.net
MAIL_PORT=587
MAIL_USERNAME=apikey
MAIL_PASSWORD=your-sendgrid-api-key
```

**Amazon SES:**
```env
MAIL_SERVER=email-smtp.us-east-1.amazonaws.com
MAIL_PORT=587
MAIL_USERNAME=your-ses-username
MAIL_PASSWORD=your-ses-password
```

## SSL/HTTPS Setup

### Using Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal is set up automatically
```

### Using Custom Certificate

Update Nginx configuration:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # ... rest of configuration
}

server {
    listen 80;
    return 301 https://$server_name$request_uri;
}
```

## Monitoring & Maintenance

### Health Checks

The application provides a health check endpoint:
```bash
curl http://localhost:5000/health
```

### Logging

Logs are stored in `/app/logs/` (Docker) or `/opt/ayah-app/logs/` (systemd):
- `ayah_app.log` - Application logs
- `ayah_app_errors.log` - Error logs
- `access.log` - HTTP access logs (Gunicorn)

### Backup Strategy

1. **Database Backup**
   ```bash
   # PostgreSQL
   pg_dump ayah_db > backup_$(date +%Y%m%d).sql
   
   # SQLite
   sqlite3 ayah_app.db ".backup backup_$(date +%Y%m%d).db"
   ```

2. **Data Files Backup**
   ```bash
   tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
   ```

3. **Automated Backups**
   Add to crontab:
   ```bash
   0 2 * * * /path/to/backup_script.sh
   ```

### Monitoring

1. **Application Metrics**
   - Use `/health` endpoint for basic health checks
   - Monitor `/admin/data-integrity` for data validation
   - Track email delivery success rates

2. **System Monitoring**
   - CPU and memory usage
   - Disk space
   - Network connectivity
   - Database performance

3. **Error Tracking**
   - Set up Sentry or similar service
   - Monitor application logs
   - Set up alerts for critical errors

### Updates and Maintenance

1. **Application Updates**
   ```bash
   # Pull latest changes
   git pull origin main
   
   # Update dependencies
   pip install -e .
   
   # Restart services
   sudo systemctl restart ayah-app
   
   # Or for Docker
   docker-compose pull && docker-compose up -d
   ```

2. **Data Updates**
   - Replace JSON files in `data/` directory
   - Clear cache: `rm -rf cache/*`
   - Restart application

### Troubleshooting

**Common Issues:**

1. **Email not sending**
   - Check SMTP credentials
   - Verify firewall allows SMTP traffic
   - Check email provider settings

2. **Data loading errors**
   - Verify JSON file format
   - Check file permissions
   - Review error logs

3. **Performance issues**
   - Enable caching
   - Optimize database queries
   - Scale with multiple workers

**Getting Help:**

- Check application logs
- Review configuration settings
- Test individual components
- Use health check endpoints

## Security Considerations

1. **Environment Variables**
   - Never commit `.env` files
   - Use strong, unique passwords
   - Rotate secrets regularly

2. **Network Security**
   - Use HTTPS in production
   - Configure firewall rules
   - Keep system updated

3. **Application Security**
   - Validate all inputs
   - Use CSRF protection
   - Monitor for suspicious activity

4. **Database Security**
   - Use dedicated database user
   - Limit database permissions
   - Enable connection encryption

This completes the deployment guide. Choose the deployment method that best fits your needs and infrastructure.
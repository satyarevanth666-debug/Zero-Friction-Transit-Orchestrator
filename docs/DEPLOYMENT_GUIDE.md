# Zero-Friction Transit Orchestrator — Production Deployment Guide

This guide covers complete, production-ready deployment strategies for the **Zero-Friction Transit Orchestrator** multi-modal transit application (Next.js 14 frontend + FastAPI backend + RAPTOR routing engine).

---

## 1. Deployment Options Matrix

| Deployment Strategy | Best For | Typical Hosting | Estimated Cost | Setup Time |
| :--- | :--- | :--- | :--- | :--- |
| **Option A: Docker Compose** *(Recommended)* | Single-server / Cloud VM | AWS EC2, DigitalOcean, Hetzner, GCP | $5 – $12 / mo | 5 mins |
| **Option B: Cloud PaaS (Serverless)** | Hackathon demos & presentations | Vercel (Frontend) + Render / Railway (Backend) | Free – $7 / mo | 10 mins |
| **Option C: Bare Linux VPS** | Custom domain & maximum control | Ubuntu 22.04 / 24.04 + Nginx + Certbot | $5 / mo | 15 mins |

---

## 2. Essential Production Environment Variables

Ensure these variables are configured in your production `.env` or cloud dashboard:

### Backend (`backend/.env`)

```ini
# Application Mode
APP_ENV=production
TIMEZONE=Asia/Kolkata

# Security (CRITICAL)
# Generate a strong key: openssl rand -hex 32
JWT_SECRET=replace_this_with_a_secure_random_string_at_least_32_characters_long
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7

# CORS & Cookies
# Set to your actual frontend domain:
FRONTEND_ORIGIN=https://transit.yourdomain.com
# Set to true when serving behind HTTPS:
COOKIE_SECURE=true

# Database (SQLite for single instance, PostgreSQL for multi-replica)
DATABASE_URL=sqlite:///./zero_friction_transit.db
# Or PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/transit_db

# Live Third-Party APIs
ENABLE_THIRD_PARTY_RAIL=true
RAIL_API_KEY=your_rapidapi_irctc_key_here
FLIGHT_PROVIDER=airlabs
FLIGHT_API_KEY=your_airlabs_api_key_here

# LLM Fallback (Optional)
LLM_ENABLED=false
# If using hosted Ollama:
# OLLAMA_BASE_URL=http://ollama:11434
# LLM_MODEL=qwen2.5:7b-instruct
```

### Frontend (`frontend/.env.production`)

```ini
# URL pointing to your deployed FastAPI backend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api
NODE_ENV=production
```

---

## 3. Option A: Deploy with Docker Compose (Turnkey)

This deploys the complete stack (FastAPI backend, Next.js standalone frontend, and optional Ollama) in isolated Docker containers with automated restarts.

### Step 1: Clone Repository on Server

```bash
git clone https://github.com/your-username/zero-friction-transit.git
cd zero-friction-transit
```

### Step 2: Configure Environment

```bash
cp .env.example .env
nano .env  # Add your JWT_SECRET, RAIL_API_KEY, and FLIGHT_API_KEY
```

### Step 3: Build and Launch Containers

```bash
# Build and run in detached mode
docker compose up --build -d
```

### Step 4: Verify Containers Are Running

```bash
docker compose ps
docker compose logs -f
```

- **Frontend**: Accessible on port `3000` (`http://your-server-ip:3000`)
- **Backend API**: Accessible on port `8000` (`http://your-server-ip:8000/api/docs`)

---

## 4. Option B: Cloud PaaS (Vercel + Render / Railway)

Ideal for live demos, zero server management, and automated continuous deployment via GitHub.

### Part 1: Deploy Backend on Render / Railway

1. Push your repository to GitHub.
2. Sign up at [Render.com](https://render.com/) or [Railway.app](https://railway.app/).
3. **If using Render**:
   - Go to **Blueprints** → Click **New Blueprint Instance**.
   - Select your GitHub repository.
   - Render will automatically detect the [render.yaml](file:///c:/Users/SATYA%20REVANTH/OneDrive/Desktop/EA%20Hackathon/render.yaml) blueprint in the repository.
   - Fill in `RAIL_API_KEY`, `FLIGHT_API_KEY`, and `FRONTEND_ORIGIN` in the dashboard.
   - Click **Apply**.
4. **If using Manual Web Service on Render**:
   - **Environment**: Python
   - **Root Directory**: `backend`
   - **Build Command**: `pip install --upgrade pip && pip install .`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**: Add variables from Section 2.
5. Note your backend URL: e.g., `https://zero-friction-backend.onrender.com`.

### Part 2: Deploy Frontend on Vercel

1. Sign up at [Vercel.com](https://vercel.com/) and click **Add New** → **Project**.
2. Select your repository.
3. Configure project settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: Click Edit → select `frontend`.
4. Add Environment Variable:
   - `NEXT_PUBLIC_API_URL` = `https://zero-friction-backend.onrender.com/api`
5. Click **Deploy**.
6. Once deployed, copy your Vercel URL (e.g. `https://zero-friction-transit.vercel.app`) and update the backend's `FRONTEND_ORIGIN` variable on Render to match it.

---

## 5. Option C: Production Linux VPS (Ubuntu + Nginx + Systemd + SSL)

For enterprise or custom domain hosting on a virtual private server.

### Step 1: Install System Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip nodejs npm nginx certbot python3-certbot-nginx git
```

### Step 2: Set Up Backend

```bash
cd /var/www/zero-friction-transit/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install .
```

Create Systemd Service (`/etc/systemd/system/transit-backend.service`):

```ini
[Unit]
Description=Zero-Friction Transit FastAPI Backend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/zero-friction-transit/backend
EnvironmentFile=/var/www/zero-friction-transit/backend/.env
ExecStart=/var/www/zero-friction-transit/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable transit-backend
sudo systemctl start transit-backend
```

### Step 3: Build & Set Up Frontend

```bash
cd /var/www/zero-friction-transit/frontend
npm install
npm run build
```

Create Systemd Service (`/etc/systemd/system/transit-frontend.service`):

```ini
[Unit]
Description=Zero-Friction Transit Next.js Frontend
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/zero-friction-transit/frontend
Environment="NODE_ENV=production"
Environment="PORT=3000"
ExecStart=/usr/bin/node .next/standalone/server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable transit-frontend
sudo systemctl start transit-frontend
```

### Step 4: Configure Nginx & SSL

Create `/etc/nginx/sites-available/transit`:

```nginx
server {
    server_name yourdomain.com api.yourdomain.com;

    # Frontend Reverse Proxy
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # Backend API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and secure with Let's Encrypt:

```bash
sudo ln -s /etc/nginx/sites-available/transit /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com
```

---

## 6. Verification & Health Checks

Once deployed, verify that all services are operational:

```bash
# 1. Backend Health Check
curl -I https://api.yourdomain.com/api/health
# Expected: HTTP/2 200 OK

# 2. Synchronous Plan Search Check
curl -X POST https://api.yourdomain.com/api/plan/sync \
  -H "Content-Type: application/json" \
  -d '{"query":"Hyderabad to Chennai"}'
# Expected: JSON payload with best_balance itineraries and train services

# 3. Frontend Check
curl -I https://yourdomain.com
# Expected: HTTP/2 200 OK
```

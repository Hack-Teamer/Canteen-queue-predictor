# QueueSense ⏱️🍔

**QueueSense** is a canteen wait-time prediction and crowd management platform. It fuses real-time computer vision camera counts of the queue zone with live kitchen ordering workloads, predicts wait-time ranges using LightGBM quantile regression models, forecasts wait times over the next 30 minutes, and provides schedule-aware departure alerts for students.

---

## 🏗️ Architecture & Features

```
[ YOLOv8 Camera Service ] ──(POST /api/v1/vision/count)──> [ QueueSense API ] <───> [ Redis ]
                                                                   │                   (Live Queue &
                                                                   │                    Pub/Sub)
                                                                   ├───> [ Postgres ]
                                                                   │     (Orders & History)
                                                                   │
                                                                   ├───> [ ML Engine ]
                                                                   │     (LightGBM Quantile
                                                                   │      0.1 / 0.5 / 0.9)
                                                                   │
                                                                   └───> [ Celery Workers ]
                                                                         (Retraining & Forecasts)
```

1. **Camera & Online Fusion Engine**:
   - Calculates hidden walk-in customers: `estimated_walk_ins = max(0, camera_count - online_orders)`.
   - Distributes walk-in load across kitchen stations according to historical station demand.
2. **LightGBM Quantile Prediction**:
   - Predicts low (10th percentile), median (50th percentile), and high (90th percentile) wait times.
   - Enforces $q_{10} \le q_{50} \le q_{90}$ and rounds to whole minutes.
   - Automatic fallback to station-aware baseline formula if model is unavailable (`"source": "baseline"`).
3. **Timetable & Break Intelligence**:
   - Analyzes campus schedule (class periods, morning break, lunch break) to project arrival spikes (10–15 minutes post-bell).
4. **Kitchen Operations & Status Machine**:
   - Supports states: `placed` ➔ `accepted` ➔ `preparing` ➔ `ready` ➔ `collected`.
   - Records true wait time upon `ready` to train and evaluate future models.
5. **Real-time WebSockets**:
   - `/ws/queue`: Student stream for personal order events and crowd levels.
   - `/ws/kitchen`: Staff stream for live order board and station load spikes.
6. **30-Minute Forecast & "Leave-Now" Advice**:
   - Recommends the best slot to order in the next 30 minutes.
   - Computes latest departure time given `next_class_at` timestamp.

---

## 🚀 Quickstart with Docker Compose

To start all services (FastAPI, Vision Service, PostgreSQL, Redis, Celery Worker, Celery Beat, MLflow, Prometheus, Nginx):

```bash
# Clone and enter directory
cd queuesense/infra

# Start services
docker compose up --build -d
```

Check health status:
```bash
curl http://localhost:8000/api/v1/health/ready
```

---

## 🛠️ Local Development Setup

### 1. Backend

```bash
cd queuesense/backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\activate

pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed initial stations, menu, and demo accounts
python app/db/seed.py

# Run FastAPI server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Vision Service

```bash
cd queuesense/vision
pip install -r requirements.txt
python main.py
```

### 3. Generate Simulated Data & Train Initial Model

```bash
cd queuesense/backend

# Generate 5,000 synthetic canteen orders using SimPy
python scripts/generate_data.py --orders 5000 --output data/canteen_simulation.csv

# Train LightGBM quantile regression models
python scripts/train_model.py --data data/canteen_simulation.csv --promote
```

---

## 🔑 Demo Credentials

| Role | Email | Password |
|---|---|---|
| **Student** | `student@queuesense.edu` | `student123` |
| **Kitchen Staff** | `kitchen@queuesense.edu` | `kitchen123` |
| **Admin** | `admin@queuesense.edu` | `admin123` |

---

## 📡 API Examples (cURL)

### 1. Student Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@queuesense.edu",
    "password": "student123"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user_id": "...",
  "role": "student"
}
```

### 2. View Menu

```bash
curl -X GET http://localhost:8000/api/v1/menu
```

### 3. Place an Order (with Wait-Time Prediction)

```bash
curl -X POST http://localhost:8000/api/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <STUDENT_TOKEN>" \
  -H "Idempotency-Key: ord-unique-key-101" \
  -d '{
    "items": [
      {
        "menu_item_id": "<ITEM_UUID>",
        "quantity": 1
      }
    ]
  }'
```

Response:
```json
{
  "order_id": "a9bf2810-...",
  "token_number": 42,
  "status": "placed",
  "wait": {
    "low": 6,
    "median": 8,
    "high": 11,
    "source": "ml",
    "model_version": "v_20261009_120000"
  },
  "explanation": {
    "estimated_walk_ins": 3,
    "busiest_station": "tawa"
  }
}
```

### 4. Kitchen Updates Order Status

```bash
# Accept order
curl -X PATCH http://localhost:8000/api/v1/kitchen/orders/<ORDER_ID>/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <KITCHEN_TOKEN>" \
  -d '{"status": "accepted"}'

# Mark ready
curl -X PATCH http://localhost:8000/api/v1/kitchen/orders/<ORDER_ID>/status \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <KITCHEN_TOKEN>" \
  -d '{"status": "ready"}'
```

### 5. Camera Vision Ingestion

```bash
curl -X POST http://localhost:8000/api/v1/vision/count \
  -H "Content-Type: application/json" \
  -H "X-API-Key: vision-secret-api-key-2024" \
  -d '{
    "people_count": 14,
    "zone_id": "canteen_queue_zone",
    "captured_at": "2026-10-09T12:00:00Z"
  }'
```

### 6. 30-Minute Wait Forecast & Leave Time

```bash
# Get 30-min window forecast
curl -X GET http://localhost:8000/api/v1/forecast

# Check if you can order before your 1:30 PM class
curl -X GET "http://localhost:8000/api/v1/forecast/leave-time?next_class_at=2026-10-09T13:30:00Z"
```

---

## 🧪 Testing

Run all unit, integration, ML, and WebSocket tests:

```bash
cd queuesense/backend
pytest -v
```

---

## 📊 Monitoring & Metrics

- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Swagger Documentation**: `http://localhost:8000/api/v1/docs`
- **ReDoc**: `http://localhost:8000/api/v1/redoc`
- **MLflow UI**: `http://localhost:5000`

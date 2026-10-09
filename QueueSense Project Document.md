# QueueSense: An Order and Camera Fusion System for Canteen Wait-Time Prediction

Project document | Version 1.0 | October 2026

## 1. Executive Summary

Students in most college canteens stand in line without knowing how long they will wait, and canteens suffer sudden rushes right after lectures end. QueueSense is a web application that predicts the wait for each order as a range (for example, 9-14 minutes) and actively helps students avoid the rush.

It combines two data sources that are usually used separately:

- **The order system**, which knows what is being cooked and at which station.
- **A canteen camera**, which sees everyone physically in line, including walk-in customers who did not order online.

The system fuses both signals into one estimate of the kitchen's real pending workload, predicts the wait with a machine learning model, forecasts the next 30 minutes, and recommends better times to order.

## 2. Problem Statement

Students place canteen orders online and should see an estimated wait time based on the current queue. A simple estimate such as "queue length × fixed minutes" fails for several reasons:

- Ten cups of tea and one order of five dosas are very different workloads, but have the same length.
- Walk-in customers who did not order online are invisible to the ordering system.
- Rushes follow the lecture timetable, but a static formula cannot anticipate them.
- A single number such as "12 minutes" hides the real uncertainty.

**Core requirement (from the problem brief):** menu, order placement, and a live queue with token numbers.

**Stretch requirement:** wait-time prediction from past order data and an "order ready" notification.

## 3. Background and Related Work

### 3.1 Reference repository

The repository `zoezhousy/Canteen_Queue_Monitoring` is a COMP4423 Computer Vision course project. Its front page shows a `Dataset/label` folder, a `Source Code` folder, and an instruction to run `Main.py`. The README contains no method description, and the source folder could not be opened during analysis. The following is therefore an inference, not a verified description: the project appears to monitor queues from camera or video input, most likely by detecting and counting people.

### 3.2 Comparison

| Aspect | Reference repository (inferred) | Typical ordering app | QueueSense |
| --- | --- | --- | --- |
| Input | Camera or video | Online orders | Orders and camera together |
| Measures | How many people are in line | Number of orders in queue | Workload per station plus hidden walk-ins |
| Output | Crowd level | One wait number | Wait range and 30-minute forecast |
| Behaviour | Passive monitoring | Passive display | Recommends when to order |
| Learning | Static | Static | Retrains on actual wait times |

## 4. Objectives

1. Let students order online and track a token and live queue position.
2. Predict the wait time of each order as a low-high range.
3. Estimate hidden demand from walk-in customers using the camera.
4. Forecast the next 30 minutes and recommend better order times.
5. Give kitchen staff a fast panel and give management an analytics dashboard.
6. Improve prediction accuracy over time from real kitchen timestamps.

## 5. Users and Requirements

### 5.1 Users

| User | Goals |
| --- | --- |
| Student | Order quickly, know the wait, avoid the rush, get an alert when ready |
| Kitchen staff | See orders by station, mark progress with one tap |
| Canteen manager / admin | Understand peak hours, staffing needs, and system accuracy |

### 5.2 Functional requirements

- **FR1:** Students can browse the menu and place an order.
- **FR2:** The system issues a token number and shows live queue status.
- **FR3:** The system shows a wait-time range for every active order.
- **FR4:** The system suggests a better time to order based on a 30-minute forecast.
- **FR5:** Students receive a notification when the order is ready.
- **FR6:** Kitchen staff can set order status: accepted, preparing, ready.
- **FR7:** The system counts people in the queue zone from the camera feed.
- **FR8:** Admins can view peak hours, station performance, popular items, and prediction accuracy.
- **FR9:** The model retrains periodically from logged actual wait times.
- **FR10:** Role-based login for student, kitchen, and admin.

### 5.3 Non-functional requirements

| Requirement | Target |
| --- | --- |
| Live update latency | Under 2 seconds from kitchen tap to student screen |
| Prediction latency | Under 500 ms per request |
| Availability | The app must keep working if the camera or ML service fails (fall back to the baseline formula) |
| Privacy | No faces or video stored; only counts are kept |
| Usability | Kitchen actions require one tap and no typing |
| Scalability | Handle the peak of all students ordering within a few minutes |

## 6. Proposed Solution: QueueSense

### 6.1 Core idea

The order system knows the content of the queue but misses walk-ins. The camera sees everyone but not what they ordered. QueueSense uses the gap between the two to estimate the hidden demand, then predicts the wait from the full picture.

### 6.2 Fusion logic

1. **Order stream:** items, stations, and timestamps from the app.
2. **Vision stream:** a person detector counts people inside a defined queue zone every few seconds.
3. **Walk-in estimate:**

   `estimated walk-ins = people physically in line - people with online orders in line` (never below zero)
4. **Workload assignment:** online orders contribute their exact per-station prep time. Each estimated walk-in is assigned the historical average workload for that time of day.
5. **Station load:**

   `station load = sum of prep time of known items + (estimated walk-ins × average station demand)`
6. **Prediction:** a quantile regression model turns station loads and context into a wait range.
7. **Forecast and advice:** the model runs over the next 30 minutes to find low-wait slots and detect coming rushes.
8. **Feedback:** the actual wait is logged when an order is marked ready and used for retraining.

### 6.3 Key features

- **Station-aware prediction:** each menu item has a station and a prep time.
- **Range output:** low and high estimates from the 10th and 90th percentile models.
- **Timetable awareness:** minutes since the last lecture bell, break periods, and weekday.
- **Best time to order:** for example, "Order now: 14 min. Order at 1:20: 4 min."
- **Leave-now alert:** the student gives the next class time, and the app says when to order so food is ready on arrival.
- **Self-correcting ETA:** live estimates for people still waiting update whenever an order completes.

## 7. System Architecture

```
React PWA (student / kitchen / admin)
        |  REST + WebSocket
        v
FastAPI backend  <---->  PostgreSQL
        |   \
        |    +--> Redis (live queue, cache, pub/sub, job broker)
        |
        +--> ML service (LightGBM predictor, models from MLflow)
        |
        +--> Vision service (YOLOv8 on camera stream) --> people count --> Redis
        |
Celery workers + Beat: retrain model, refresh forecast, send notifications
```

### 7.1 Components

| Component | Responsibility |
| --- | --- |
| Frontend (React PWA) | Student ordering, kitchen board, admin dashboard |
| Backend API (FastAPI) | Authentication, orders, queue logic, WebSocket updates |
| PostgreSQL | Durable data: users, menu, orders, history, predictions |
| Redis | Live queue state, cached predictions, pub/sub, job broker |
| ML service | Loads models, computes features, returns wait ranges |
| Vision service | Reads the camera stream, counts people in the queue zone |
| Celery workers | Scheduled retraining, forecast refresh, notifications |
| MLflow | Model versions, metrics, rollback |

### 7.2 Data flow for one order

1. The student places an order; the backend creates it and splits items by station.
2. The order is pushed to the kitchen board over WebSocket.
3. The backend collects features (station loads, camera count, timetable) and calls the ML service.
4. The student sees a token and a wait range.
5. Staff tap Accepted, Preparing, Ready; each tap is timestamped.
6. On Ready, the actual wait is stored with the original prediction, and ETAs for later orders are recalculated.

## 8. Machine Learning Design

### 8.1 Task

Quantile regression of the order wait time (minutes from order placement to ready).

### 8.2 Features

| Group | Features |
| --- | --- |
| Order load | Items ahead per station, total prep minutes ahead per station, items in this order |
| Fusion | People in queue zone, estimated walk-ins |
| Time context | Hour of day, day of week, minutes since last lecture bell, break flag |
| Capacity | Number of active cooks per station |

### 8.3 Model

LightGBM with three models at quantiles 0.1, 0.5, and 0.9. The output is shown as "low to high" with the median used for sorting and alerts.

### 8.4 Training data

- **Before launch:** synthetic data from a SimPy discrete-event simulation of the canteen (arrival rates tied to the timetable, random prep times, a set number of cooks per station).
- **After launch:** real logs from the `predictions` table, which replace and extend the synthetic data.

### 8.5 Baseline fallback

If the ML or vision service is unavailable, the system falls back to the station-aware formula (items ahead × prep time per station) so the app continues to work.

## 9. Computer Vision Design

- **Model:** YOLOv8 (nano or small), pretrained on COCO, using the "person" class. No training is needed.
- **Zone:** a polygon drawn over the queue area; a person is counted when the centre of their bounding box falls inside it.
- **Frequency:** one count every few seconds, smoothed with a short moving average to avoid flicker.
- **Output:** an integer written to Redis and stored in `crowd_snapshots`.
- **Placement:** a high, angled camera position gives the best accuracy.
- **Privacy:** frames are processed in memory and discarded; only the number is kept.

## 10. Dashboards

All dashboards share one backend. Live data (current queue, station load) is pushed from Redis over WebSockets. Historical data is queried from PostgreSQL through REST endpoints, with heavy aggregations precomputed by Celery and cached.

### 10.1 Kitchen dashboard

- Incoming orders grouped by station, oldest first.
- Station load meters in minutes of pending work.
- Rush warning from the forecast, and the current crowd level.
- One-tap status buttons. The Ready tap stores the actual wait time used for training.

### 10.2 Admin dashboard

| Section | Content |
| --- | --- |
| Today at a glance | Orders, average wait, current queue |
| Peak hours | Heatmap of orders and waits by hour and weekday |
| Station performance | Average prep time and load per station |
| Popular items | Top sellers and slow items |
| Prediction accuracy | Predicted vs actual wait, share of waits inside the range |
| Crowd trend | Camera people count over time |
| Model health | Error trend, last retrain date, model version |

### 10.3 Student view

Token, queue position, wait range, best-time-to-order suggestion, and an order-ready notification.

### 10.4 Model monitoring

- Daily mean absolute error between predicted and actual wait.
- Coverage: the share of actual waits inside the predicted range (about 80% expected for a 10th-90th percentile band).
- A drift alert when error rises for several days, which triggers retraining.
- A comparison of error with and without the camera feature.

## 11. Database Design

| Table | Purpose |
| --- | --- |
| `users` | Accounts and roles (student, kitchen, admin) |
| `stations` | Tea counter, tawa, fryer, with active cook count |
| `menu_items` | Name, price, station, prep time |
| `orders` | Order header, status, token, timestamps |
| `order_items` | Items and quantities in each order |
| `queue_events` | Every status change with a timestamp |
| `predictions` | Predicted low, median, high, actual wait, model version, features |
| `crowd_snapshots` | Camera people count over time |
| `notifications` | Alerts sent to students |

## 12. Technology Stack

| Layer | Choice |
| --- | --- |
| Frontend | React, Vite, TypeScript, Tailwind CSS, React Query, built as a PWA |
| Backend | FastAPI (Python) with WebSockets |
| Database | PostgreSQL with SQLAlchemy 2.0 and Alembic |
| Cache and live state | Redis (pub/sub, queue state, job broker) |
| Background jobs | Celery and Celery Beat |
| Authentication | JWT with role-based access |
| ML | LightGBM (quantile regression), MLflow for tracking |
| Vision | YOLOv8 (Ultralytics) and OpenCV as a separate service |
| Simulation | SimPy, NumPy, pandas |
| Notifications | Firebase Cloud Messaging and Web Push; optional SMS |
| Analytics | Recharts or Grafana |
| DevOps | Docker Compose, GitHub Actions, Prometheus, Grafana, Sentry |
| Testing | pytest, Vitest, Playwright |

## 13. API Overview (sample routes)

| Route | Method | Purpose |
| --- | --- | --- |
| `/auth/login` | POST | Obtain a token |
| `/menu` | GET | List menu items |
| `/orders` | POST | Place an order and receive a token and wait range |
| `/orders/{id}` | GET | Order status and current ETA |
| `/queue` | GET | Current queue summary |
| `/ws/queue` | WebSocket | Live updates for students and kitchen |
| `/kitchen/orders/{id}/status` | PATCH | Set Accepted, Preparing, or Ready |
| `/forecast` | GET | 30-minute wait forecast and best order time |
| `/admin/peak-hours` | GET | Peak-hour aggregates |
| `/admin/accuracy` | GET | Prediction error and coverage |

## 14. Evaluation Plan

### 14.1 Predictor comparison

Compare four predictors on the same held-out data:

| Model | Inputs |
| --- | --- |
| Baseline | Queue length × fixed minutes |
| Orders only | Station-aware order load |
| Camera only | People count |
| QueueSense (fused) | Orders, camera, and timetable |

**Metrics:** mean absolute error, root mean squared error, and range coverage (the share of actual waits inside the predicted range). Break results down by the proportion of walk-ins, since the fused model should help most when walk-ins are common.

### 14.2 Recommendation impact

Run the simulator with and without best-time-to-order suggestions, with a fixed share of students following them. Compare peak queue length and average wait.

### 14.3 System tests

- Unit tests for queue logic and the fusion calculation.
- API tests for order flow and role permissions.
- End-to-end tests of order, kitchen update, and student notification.
- Load test with all users ordering in a short window.

## 15. Uniqueness

Individual parts (online ordering, YOLO counting, gradient boosting) are common. The contribution is the combination:

1. **Fusion for walk-ins:** the gap between camera count and order count estimates demand the order system cannot see.
2. **Content-aware load:** prediction from what is queued per station, not just how many people are waiting.
3. **Honest uncertainty:** a wait range from quantile regression.
4. **Demand shifting:** the system recommends order times in order to flatten the rush.
5. **Continuous learning:** every Ready tap improves the model.

A safe claim is: "We combine station-aware prediction, camera crowd sensing, and demand-shifting recommendations in a single campus system." It should not be described as an idea nobody has tried.

## 16. Privacy and Ethics

- The camera is used only to count people. Faces and video are not stored or identified.
- Post a visible notice near the camera explaining its purpose.
- Collect only the personal data needed for orders and notifications.
- Keep roles strict: only admins see analytics, and only kitchen staff change order status.
- Obtain the canteen and college administration's approval before installing a camera.

## 17. Risks and Limitations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| No real data at the start | Model is trained on assumptions | Use the SimPy simulator, then replace it with real logs |
| Walk-in workload differs from average | Wrong estimate | Widen the range and track error by walk-in share |
| Camera misses people in dense crowds | Count is a lower bound | Use a high angle, smooth counts, and show uncertainty |
| Kitchen staff skip status taps | Training data is lost | One-tap design, large buttons, and training for staff |
| Peak-hour load | Slow app | Redis caching, WebSockets, and a load test |
| Service failure | No prediction | Fall back to the baseline formula |
| Synthetic results overstate accuracy | Misleading claims | State clearly that real accuracy needs real logs |

## 18. Development Roadmap

| Phase | Deliverables |
| --- | --- |
| 1. Foundation | Docker Compose, PostgreSQL, Redis, FastAPI, authentication, menu, orders, token numbers |
| 2. Live queue | WebSockets, kitchen panel, student queue view |
| 3. Baseline ETA | Station-aware formula so the app works without ML |
| 4. ML | SimPy data, LightGBM quantile models, prediction logging, feedback loop |
| 5. Vision | YOLO people counter, walk-in estimator, error comparison with and without camera |
| 6. Smart features | Forecast, best-time-to-order, leave-now alerts, admin dashboard |
| 7. Hardening | Tests, CI, monitoring, deployment, pilot with the canteen |

## 19. Future Work

- Per-item demand forecasting to help the canteen plan stock.
- Dynamic cook staffing suggestions.
- Payment integration and pre-paid orders.
- Tracking people across frames to estimate how long each has been waiting.
- Multi-canteen support across a campus.

## 20. Conclusion

QueueSense turns a canteen queue from something people only observe into something the system predicts and helps reduce. By fusing the order system with a camera feed, it estimates demand that either source would miss, gives students an honest wait range, and recommends better order times. The project is built in stages, so a working version exists early and each phase adds measurable value.

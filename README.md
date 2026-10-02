# ⚡ Redis Learning Project

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Django-6.x-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django">
  <img src="https://img.shields.io/badge/Redis-Cache-DC382D?style=for-the-badge&logo=redis&logoColor=white" alt="Redis">
  <img src="https://img.shields.io/badge/PostgreSQL-Database-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Postman-API_Testing-FF6C37?style=for-the-badge&logo=postman&logoColor=white" alt="Postman">
  <img src="https://img.shields.io/badge/Git-GitHub-F05032?style=for-the-badge&logo=git&logoColor=white" alt="Git">
</p>

<p align="center">
  <b>A practical Redis learning project focused on caching, performance, reliability, and real-world Django integration.</b>
</p>

---

## 📌 About the Project

This project was built to understand **Redis practically**, rather than learning Redis commands only from theory.

The project integrates Redis with a **Django Product API** and **PostgreSQL**, allowing Redis concepts to be implemented, tested, inspected, and observed through real API requests.

The main goal is to understand:

- How Redis stores data
- How caching works
- How Cache HIT and MISS work
- How cache invalidation works
- How TTL controls cached data
- How Redis Hashes can represent objects
- How counters work
- How cache stampede happens
- How Redis locks prevent duplicate database work
- How cache penetration happens
- How negative caching reduces repeated database queries
- What happens when Redis becomes unavailable
- How Redis key naming should be designed
- How memory limits and eviction policies work
- How to inspect Redis using the CLI
- How Redis fits into a Django backend architecture

---

# 🎯 Project Objectives

The project focuses on learning Redis through a complete backend workflow.

### Primary Objectives

- Understand Redis fundamentals
- Practice Redis commands directly using Redis CLI
- Integrate Redis with Django
- Use PostgreSQL as the source of truth
- Implement Cache-Aside caching
- Implement cache invalidation
- Implement TTL-based expiration
- Use Redis Hashes for product caching
- Implement Redis counters
- Handle cache stampede using Redis locks
- Handle cache penetration using negative caching
- Implement Redis failure fallback
- Design structured Redis keys
- Understand Redis memory and eviction
- Practice Redis key discovery using `SCAN`
- Test Redis behavior through API requests
- Document the complete architecture and request flows

---

# 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │      Client         │
                         │  Postman / HTTP     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       Django        │
                         │    Product API      │
                         └───────┬───────┬─────┘
                                 │       │
                    Cache HIT ───┘       └─── Cache MISS
                                 │
                    ┌────────────▼───┐
                    │      Redis     │
                    │ Cache / Lock   │
                    │ Counter / TTL  │
                    └────────────────┘
                                 │
                          Cache MISS
                                 │
                    ┌────────────▼───┐
                    │  PostgreSQL    │
                    │ Source of Truth│
                    └────────────────┘
```

### Core Principle

> **PostgreSQL is the source of truth. Redis is the performance and caching layer.**

Redis does not replace PostgreSQL in this project.

---

# 🔄 Cache-Aside Architecture

The project primarily uses the **Cache-Aside Pattern**.

```text
                     GET /products/1/
                            │
                            ▼
                         Django
                            │
                            ▼
                       Redis GET
                       /        \
                    HIT          MISS
                     │             │
                     ▼             ▼
                Return Cache   PostgreSQL
                                  │
                                  ▼
                              Redis SET
                                  │
                                  ▼
                              Response
```

### Cache HIT

```text
Client
  ↓
Django
  ↓
Redis
  ↓
Cached Product
  ↓
Response
```

The database is not queried.

### Cache MISS

```text
Client
  ↓
Django
  ↓
Redis → MISS
  ↓
PostgreSQL
  ↓
Redis SET
  ↓
Response
```

---

# 🚀 Redis Features Implemented

| Redis Feature | Implementation |
|---|---|
| Key-Value Storage | Basic Redis data storage |
| Cache-Aside | Product caching |
| Cache HIT/MISS | GET APIs |
| TTL | Automatic cache expiration |
| Cache Invalidation | POST / PUT / DELETE |
| Redis Hashes | Individual product cache |
| Counters | Product view counter |
| Redis Locks | Cache stampede protection |
| Negative Caching | Non-existing product protection |
| Failure Fallback | PostgreSQL fallback |
| Key Naming | Structured Redis key strategy |
| SCAN | Redis key inspection |
| Memory Management | `maxmemory` and eviction concepts |

---

# 🧠 Redis Concepts Practiced

### Basic Commands

```text
SET
GET
EXISTS
DEL
```

### Expiration

```text
EXPIRE
TTL
PERSIST
```

### Hashes

```text
HSET
HGET
HGETALL
HEXISTS
HDEL
HMGET
HINCRBY
HINCRBYFLOAT
HKEYS
HVALS
```

### Counters

```text
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT
```

### Locks

```text
SET key value NX
SET key value NX EX seconds
```

### Key Management

```text
SCAN
MATCH
COUNT
```

### Memory

```text
CONFIG GET maxmemory
CONFIG GET maxmemory-policy
INFO memory
```

---

# 🗄️ Database

The project uses **PostgreSQL as the primary database**.

The Product model contains:

```text
Product
├── id
├── name
├── price
└── stock
```

PostgreSQL remains the permanent storage layer while Redis stores temporary cached data.

---

# ⚡ Redis Cache Design

### Collection Cache

```text
products:all
```

Stores the cached product list.

### Individual Product Cache

```text
product:<id>
```

Example:

```text
product:1
```

Implemented using a Redis Hash.

### Product View Counter

```text
product:<id>:views
```

Example:

```text
product:1:views
```

### Negative Cache

```text
product:<id>:not_found
```

Example:

```text
product:999:not_found
```

### Redis Lock

```text
lock:product:<id>
```

Example:

```text
lock:product:1
```

---

# ⏱️ TTL Strategy

Different Redis keys use different expiration strategies.

| Key | TTL |
|---|---:|
| `product:<id>` | 60 seconds |
| `products:all` | 60 seconds |
| `product:<id>:not_found` | 30 seconds |
| `lock:product:<id>` | 10 seconds |
| `product:<id>:views` | No TTL |

### Why?

Different data has different purposes.

- Product cache → temporary
- Product list cache → temporary
- Negative cache → short-lived
- Lock → very short-lived safety mechanism
- View counter → retained until explicitly removed

---

# 🛡️ Cache Stampede Protection

A cache stampede can occur when a popular cache entry expires and many requests arrive simultaneously.

Without protection:

```text
Request 1 ──┐
Request 2 ──┤
Request 3 ──┤── Redis MISS ── PostgreSQL
Request 4 ──┤
Request 5 ──┘
```

Multiple requests can hit PostgreSQL unnecessarily.

This project uses a **Redis lock**:

```text
Request
   ↓
Redis MISS
   ↓
Acquire Lock
   ↓
Check Cache Again
   ↓
PostgreSQL
   ↓
Redis SET
   ↓
Release Lock
```

Only the lock holder performs the database query.

---

# 🚫 Cache Penetration Protection

Requests for non-existing products can repeatedly reach PostgreSQL.

Example:

```text
GET /products/999/
```

Instead of repeatedly querying PostgreSQL:

```text
Request
  ↓
Redis
  ↓
Negative Cache
  ↓
NOT_FOUND
  ↓
404 Response
```

Negative cache entries expire after a short period so that a product can later be created without being permanently blocked by stale negative data.

---

# 🔥 Redis Failure Handling

Redis is treated as a **performance layer**, not the source of truth.

If Redis becomes unavailable:

```text
Client
  ↓
Django
  ↓
Redis unavailable
  ↓
PostgreSQL
  ↓
Response
```

This allows the application to continue serving product data using PostgreSQL for the implemented single-product read path.

When Redis becomes available again:

```text
Redis Recovery
      ↓
Next Request
      ↓
Cache MISS
      ↓
PostgreSQL
      ↓
Redis SET
      ↓
Future Requests → Cache HIT
```

---

# 🌐 API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/products/` | Get all products |
| `GET` | `/products/<id>/` | Get one product |
| `POST` | `/products/` | Create product |
| `PUT` | `/products/<id>/` | Update product |
| `DELETE` | `/products/<id>/` | Delete product |

### Example Product

```json
{
    "id": 1,
    "name": "Laptop",
    "price": 55000,
    "stock": 10
}
```

---

# 🔄 Cache Invalidation

Whenever product data changes, the corresponding cache is invalidated.

### POST

```text
Create Product
      ↓
PostgreSQL
      ↓
Delete products:all
```

### PUT

```text
Update Product
      ↓
PostgreSQL
      ↓
Delete product:<id>
      ↓
Delete products:all
```

### DELETE

```text
Delete Product
      ↓
PostgreSQL
      ↓
Delete product:<id>
      ↓
Delete products:all
```

This prevents stale cached product data from remaining after database changes.

---

# 🧪 Testing

The project was tested using multiple layers.

### Redis CLI

Used to directly inspect:

```text
SET
GET
EXISTS
DEL
TTL
EXPIRE
HSET
HGETALL
INCR
SCAN
CONFIG
INFO
```

### Django

Redis connectivity was verified through Django shell.

Example:

```text
PONG
True
'hello_redis'
```

### API Testing

APIs were tested using **Postman**.

Testing covered:

- Cache HIT
- Cache MISS
- TTL expiration
- Cache invalidation
- CRUD operations
- Redis Hashes
- Counters
- Redis locks
- Negative caching
- Redis failure fallback
- Redis recovery
- Key inspection
- Memory information

---

# 📁 Project Structure

```text
redis-learning-project/
│
├── README.md
│
├── docs/
│   ├── 01-project-overview.md
│   ├── 02-architecture.md
│   ├── 03-redis-concepts.md
│   ├── 04-cache-strategies.md
│   ├── 05-redis-commands.md
│   ├── 06-api-documentation.md
│   ├── 07-request-flows.md
│   ├── 08-testing.md
│   ├── 09-problems-and-solutions.md
│   └── 10-learning-outcomes.md
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── redis_client.py
│   ├── asgi.py
│   └── wsgi.py
│
├── products/
│   ├── migrations/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── manage.py
```

---

# 🛠️ Tech Stack

### Backend

- **Python**
- **Django**

### Database

- **PostgreSQL**

### Cache / Performance

- **Redis**
- **Memurai** for Redis-compatible local development on Windows

### API Testing

- **Postman**

### Development Tools

- **Git**
- **GitHub**
- **VS Code**

---

# ⚙️ Setup

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd redis-learning-project
```

## 2. Create Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

## 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 4. Configure Environment Variables

Create `.env` in the project root:

```env
DB_NAME=redis_learning_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

> `.env` should never be committed to GitHub.

## 5. Run Migrations

```bash
python manage.py migrate
```

## 6. Start Redis / Memurai

Make sure Redis-compatible service is running.

Verify:

```bash
memurai-cli ping
```

Expected:

```text
PONG
```

## 7. Start Django

```bash
python manage.py runserver
```

The API can then be accessed through:

```text
http://127.0.0.1:8000/products/
```

---

# 📚 Documentation

The complete learning journey is divided into focused documents:

| Document | Description |
|---|---|
| `01-project-overview.md` | Project purpose, objectives and scope |
| `02-architecture.md` | Complete system and Redis architecture |
| `03-redis-concepts.md` | Redis concepts used in the project |
| `04-cache-strategies.md` | Caching strategies and implementation |
| `05-redis-commands.md` | Redis commands practiced |
| `06-api-documentation.md` | Product API documentation |
| `07-request-flows.md` | Request and cache flows |
| `08-testing.md` | Testing and observed behavior |
| `09-problems-and-solutions.md` | Problems encountered and solutions |
| `10-learning-outcomes.md` | Final knowledge and project outcomes |

---

# 🎓 Learning Outcomes

After completing this project, the following concepts were practically understood:

- Redis fundamentals
- Redis CLI
- Key-value storage
- Redis Hashes
- Redis counters
- TTL
- Cache HIT / MISS
- Cache-Aside
- Cache invalidation
- Cache stampede
- Redis distributed locking concept
- Cache penetration
- Negative caching
- Redis failure fallback
- Redis recovery
- Redis key naming
- `SCAN`
- Memory configuration
- Eviction policies
- Django + Redis integration
- PostgreSQL + Redis architecture
- API-level caching
- Performance-oriented backend design
- Debugging Redis behavior
- Observing cache behavior in real requests

---

# 🧠 Final Mental Model

The most important concept learned from this project:

```text
                  CLIENT
                     │
                     ▼
                  DJANGO
                     │
             ┌───────┴───────┐
             │               │
             ▼               ▼
           REDIS         POSTGRESQL
          Cache Layer    Source of Truth
             │               │
             └───────┬───────┘
                     │
                     ▼
                  RESPONSE
```

Redis is not simply a place to store random data.

It is used strategically to:

```text
Reduce Database Load
        ↓
Improve Response Time
        ↓
Handle Repeated Reads
        ↓
Control Cache Lifetime
        ↓
Prevent Duplicate Work
        ↓
Handle Missing Data
        ↓
Improve Application Resilience
```

---

# 🚀 Project Scope

This project intentionally focuses on **Redis fundamentals and practical caching architecture**.

The following topics were kept outside this project's scope and can be explored through separate Redis projects:

- Redis Pub/Sub
- Redis Streams
- Redis Transactions
- Redis Pipelines
- Redis Sets
- Redis Sorted Sets
- Redis Bitmaps
- HyperLogLog
- Redis Cluster
- Advanced Lua scripting

This keeps the project focused on understanding **Redis as a caching and performance layer in a Django backend**.

---

# ⭐ Key Takeaway

> **The purpose of this project was not just to use Redis, but to understand why Redis is used, where it fits in a backend architecture, how requests flow through it, and what happens when caching succeeds, fails, expires, or becomes unavailable.**

---

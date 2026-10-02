# Redis Learning Project — Architecture

## 1. Architecture Overview

The project follows a simple backend architecture where **Django acts as the application/API layer**, **PostgreSQL stores the source-of-truth data**, and **Redis provides caching and performance-related functionality**.

```text
                         Client / Postman
                                │
                                │ HTTP Request
                                ▼
                         ┌─────────────┐
                         │   Django    │
                         │ Product API │
                         └──────┬──────┘
                                │
                   ┌────────────┴────────────┐
                   │                         │
                   ▼                         ▼
             ┌───────────┐             ┌────────────┐
             │   Redis   │             │ PostgreSQL │
             │   Cache   │             │  Database  │
             └───────────┘             └────────────┘
```

---

## 2. System Components

The project contains four main runtime components:

### Client / Postman

Used to send and test HTTP requests against the Product API.

### Django

Processes requests, executes application logic, communicates with Redis and PostgreSQL, and returns JSON responses.

### Redis / Memurai

Used as the in-memory performance layer for:

- Product caching
- Product view counters
- Negative caching
- Cache locks
- TTL-based data
- Cache inspection and management

### PostgreSQL

Acts as the **source of truth** for product data.

---

## 3. Component Responsibilities

| Component | Responsibility |
|---|---|
| Client / Postman | Send API requests |
| Django | API and application logic |
| Redis | Cache and temporary performance data |
| PostgreSQL | Persistent product data |

The important architectural principle is:

```text
PostgreSQL = Source of Truth
Redis      = Cache / Performance Layer
```

Redis is not treated as the permanent database for the application.

---

## 4. Application Structure

The Django project is organized into a project configuration and a Product application.

```text
redis-learning-project/
│
├── config/
│   ├── settings.py
│   ├── urls.py
│   ├── redis_client.py
│   ├── asgi.py
│   └── wsgi.py
│
├── products/
│   ├── migrations/
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── urls.py
│   ├── views.py
│   └── tests.py
│
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

### `config/`

Contains project-level configuration, URL routing, settings, and the Redis client connection.

### `products/`

Contains the Product model and Product API implementation.

### `redis_client.py`

Creates the connection used by Django to communicate with Redis/Memurai.

---

## 5. API Layer

The Product API exposes the following endpoints:

```text
GET    /products/
GET    /products/<id>/
POST   /products/
PUT    /products/<id>/
DELETE /products/<id>/
```

The request flow is:

```text
Client
   ↓
Django URL Router
   ↓
Product View
   ↓
Redis / PostgreSQL
   ↓
JSON Response
```

---

## 6. PostgreSQL Architecture

PostgreSQL stores the actual Product records.

```text
Product
├── id
├── name
├── price
└── stock
```

Example:

```text
Product ID: 1
Name: Laptop
Price: 60000
Stock: 10
```

When product information is created, updated, or deleted, PostgreSQL is the authoritative storage layer.

---

## 7. Redis Architecture

Redis stores temporary and performance-oriented information.

The project uses different Redis keys for different purposes.

```text
products:all
        ↓
All-product cache

product:1
        ↓
Individual product Hash

product:1:views
        ↓
Product view counter

product:999:not_found
        ↓
Negative cache

lock:product:1
        ↓
Cache rebuild lock
```

Each key has a specific responsibility.

---

## 8. Cache Architecture

For cached reads, the project follows the **Cache-Aside pattern**.

```text
                         GET Request
                              │
                              ▼
                           Django
                              │
                              ▼
                           Redis
                         /       \
                      HIT         MISS
                       │             │
                       │             ▼
                       │        PostgreSQL
                       │             │
                       │             ▼
                       │           Redis
                       │             │
                       └──────┬──────┘
                              ▼
                         JSON Response
```

### Cache HIT

A **Cache HIT** occurs when the requested data already exists in Redis.

```text
Client
   │
   │ GET /products/1/
   ▼
Django
   │
   │ Check Redis
   ▼
Redis
   │
   │ HIT
   ▼
Cached Data
   │
   ▼
Django
   │
   ▼
JSON Response
```

In this case, PostgreSQL does not need to be queried for the normal cache-hit path.

---

### Cache MISS

A **Cache MISS** occurs when the requested data is not available in Redis.

```text
Client
   │
   │ GET /products/1/
   ▼
Django
   │
   │ Check Redis
   ▼
Redis
   │
   │ MISS
   ▼
PostgreSQL
   │
   │ Query Product
   ▼
Django
   │
   ├──────────────► Redis
   │                Store Cache
   │
   ▼
JSON Response
```

The database provides the actual data, and Django stores a cached representation in Redis for future requests.

---

## 9. Collection Cache Architecture

The project uses:

```text
products:all
```

to cache the complete product list.

The flow is:

```text
GET /products/
      │
      ▼
    Django
      │
      ▼
    Redis
      │
 ┌────┴────┐
 │         │
HIT       MISS
 │         │
 ▼         ▼
Return   PostgreSQL
Data        │
            ▼
          Redis
            │
            ▼
         Response
```

The collection cache has a TTL so that the cached data does not remain permanently.

---

## 10. Individual Product Cache Architecture

Individual products are stored using Redis Hashes.

The key pattern is:

```text
product:<id>
```

Example:

```text
product:1
```

The Hash contains:

```text
product:1
├── id
├── name
├── price
└── stock
```

The request flow is:

```text
GET /products/1/
        │
        ▼
      Django
        │
        ▼
      Redis
        │
        │ HGETALL
        ▼
   Product Hash
        │
        ▼
     Response
```

The individual product cache uses a TTL of **60 seconds**.

---

## 11. Cache Invalidation Architecture

Cache invalidation is used when the underlying database data changes.

The project performs writes through:

```text
POST
PUT
DELETE
```

The general flow is:

```text
Client
   ↓
Django
   ↓
PostgreSQL
   ↓
Database Changed
   ↓
Invalidate Redis Cache
   ↓
Response
```

The purpose is to prevent stale cached data from being returned.

---

## 12. POST — Cache Invalidation

When a new product is created:

```text
POST /products/
```

the flow is:

```text
Client
   ↓
Django
   ↓
Create Product
   ↓
PostgreSQL
   ↓
Invalidate products:all
   ↓
Response
```

The list cache is invalidated because the existing cached product list no longer represents the current database state.

The next:

```text
GET /products/
```

causes a Cache MISS and rebuilds the list cache.

---

## 13. PUT — Cache Invalidation

When a product is updated:

```text
PUT /products/1/
```

the flow is:

```text
Client
   ↓
Django
   ↓
Update PostgreSQL
   ↓
Invalidate product:1
   ↓
Invalidate products:all
   ↓
Clear related negative cache
   ↓
Response
```

The affected caches are removed because the product information has changed.

The next read obtains the fresh database data and rebuilds the cache.

---

## 14. DELETE — Cache Invalidation

When a product is deleted:

```text
DELETE /products/1/
```

the flow is:

```text
Client
   ↓
Django
   ↓
Delete from PostgreSQL
   ↓
Invalidate Product Cache
   ↓
Invalidate List Cache
   ↓
Response
```

This prevents the deleted product from remaining available through stale Redis data.

---

## 15. Cache Stampede Architecture

A cache stampede can occur when a popular cache entry expires and multiple requests arrive at approximately the same time.

Example:

```text
product:1
```

expires.

Multiple requests arrive:

```text
Request A
Request B
Request C
Request D
```

Without protection:

```text
Request A → PostgreSQL
Request B → PostgreSQL
Request C → PostgreSQL
Request D → PostgreSQL
```

This creates unnecessary database load.

---

## 16. Redis Lock Architecture

The project uses a Redis lock to control cache rebuilding.

Lock key:

```text
lock:product:<id>
```

Example:

```text
lock:product:1
```

The lock is created using:

```text
SET lock:product:1 1 NX EX 10
```

Meaning:

```text
NX
→ Create the lock only if it does not already exist.

EX 10
→ Automatically expire the lock after 10 seconds.
```

The flow becomes:

```text
                 Multiple Requests
                        │
                        ▼
                    Redis MISS
                        │
                        ▼
                  Try to acquire
                       lock
                        │
              ┌─────────┴─────────┐
              │                   │
              ▼                   ▼
         Lock Holder          Other Requests
              │                   │
              ▼                   ▼
         PostgreSQL           Wait / Retry
              │                   │
              ▼                   │
            Redis                 │
              │                   │
              └─────────┬─────────┘
                        ▼
                     Response
```

Only one request is responsible for rebuilding the missing cache.

---

## 17. Second Cache Check

After acquiring the lock, the lock holder checks Redis again.

This is important because another request may have populated the cache before the current request acquired the lock.

```text
Initial Redis Check
        ↓
      MISS
        ↓
   Acquire Lock
        ↓
 Check Redis Again
        ↓
   ┌────┴────┐
   │         │
  HIT       MISS
   │         │
   ▼         ▼
Return    PostgreSQL
             │
             ▼
           Redis
```

This prevents unnecessary database queries.

---

## 18. Negative Cache Architecture

The project also protects PostgreSQL from repeated requests for products that do not exist.

Example:

```text
GET /products/999/
```

First request:

```text
Request
   ↓
Django
   ↓
Redis
   ↓
Product Cache MISS
   ↓
PostgreSQL
   ↓
Product Does Not Exist
   ↓
Store Negative Cache
   ↓
404 Response
```

The negative-cache key is:

```text
product:999:not_found
```

The value is:

```text
NOT_FOUND
```

The negative cache uses a **30-second TTL**.

---

## 19. Negative Cache HIT

When the same nonexistent product is requested again before the negative cache expires:

```text
Request
   ↓
Django
   ↓
Negative Cache
   ↓
HIT
   ↓
404 Response
```

PostgreSQL does not need to be queried again during the negative-cache period.

---

## 20. Product View Counter Architecture

The project also uses Redis for product view counters.

Key pattern:

```text
product:<id>:views
```

Example:

```text
product:1:views
```

The counter can be incremented using:

```text
INCR product:1:views
```

Architecture:

```text
Product Request
      ↓
Django
      ↓
Redis Counter
      ↓
INCR
      ↓
Updated View Count
```

The counter is separate from the product cache.

It does not use a TTL in the project.

---

## 21. Redis Failure Architecture

Redis is a performance layer, not the source of truth.

If Redis becomes unavailable, the implemented single-product GET path can fall back to PostgreSQL.

```text
Request
   ↓
Django
   ↓
Redis
   ↓
Connection Failure
   ↓
PostgreSQL
   ↓
Product Response
```

During testing, when Memurai was stopped, the following Redis connection error was observed:

```text
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

The application was still able to retrieve the product through PostgreSQL for the implemented fallback path.

---

## 22. Redis Recovery Architecture

After Redis/Memurai is restarted:

```text
memurai-cli ping
```

returns:

```text
PONG
```

The normal Cache-Aside flow can then resume.

```text
Request
   ↓
Redis Available
   ↓
Cache MISS
   ↓
PostgreSQL
   ↓
Redis Cache Rebuilt
   ↓
Response
```

A later request can then become:

```text
Request
   ↓
Redis
   ↓
Cache HIT
   ↓
Response
```

---

## 23. TTL Architecture

Different Redis keys use different TTL strategies.

| Redis Key | TTL | Purpose |
|---|---:|---|
| `product:<id>` | 60 sec | Individual product cache |
| `products:all` | 60 sec | Product list cache |
| `product:<id>:not_found` | 30 sec | Negative cache |
| `lock:product:<id>` | 10 sec | Cache rebuild lock |
| `product:<id>:views` | No TTL | View counter |

TTL provides automatic expiration.

Cache invalidation handles database changes.

Therefore the project uses both:

```text
TTL
+
Explicit Cache Invalidation
```

---

## 24. Redis Key Naming Architecture

The project follows a structured Redis key naming strategy.

```text
<resource>:<id>
```

Example:

```text
product:1
```

For a specific purpose:

```text
<resource>:<id>:<purpose>
```

Examples:

```text
product:1:views
product:999:not_found
```

For locks:

```text
lock:<resource>:<id>
```

Example:

```text
lock:product:1
```

For collection data:

```text
products:all
```

This naming structure makes Redis keys easier to identify and manage.

---

## 25. Memory and Eviction Architecture

Redis stores the project's cached data in memory.

The project inspected Redis memory using:

```text
INFO memory
```

The observed configuration included:

```text
used_memory_human:828.39K
maxmemory_human:8.00G
maxmemory_policy:noeviction
```

The project also studied Redis eviction policies such as:

```text
noeviction
allkeys-lru
volatile-lru
allkeys-lfu
volatile-lfu
allkeys-random
volatile-random
volatile-ttl
```

The purpose of eviction policies is to determine how Redis behaves when its configured memory limit is reached.

---

## 26. SCAN and Key Management

Redis keys were inspected using:

```text
SCAN 0
```

Pattern matching was also practiced:

```text
SCAN 0 MATCH product:*
```

Other examples:

```text
SCAN 0 MATCH lock:*
```

```text
SCAN 0 MATCH *:not_found
```

The project uses `SCAN` for incremental key inspection rather than relying on a large blocking key lookup.

---

## 27. Complete Read Architecture

The complete read architecture is:

```text
                         GET Request
                              │
                              ▼
                           Django
                              │
                              ▼
                           Redis
                              │
                     ┌────────┴────────┐
                     │                 │
                    HIT               MISS
                     │                 │
                     ▼                 ▼
                 Response         PostgreSQL
                                       │
                                       ▼
                                     Redis
                                       │
                                       ▼
                                   Response
```

For an individual product, additional Redis mechanisms may participate:

```text
Product Cache
     +
Negative Cache
     +
Redis Lock
     +
TTL
```

depending on the request state.

---

## 28. Complete Write Architecture

For POST, PUT, and DELETE:

```text
                     Write Request
                           │
                           ▼
                        Django
                           │
                           ▼
                      PostgreSQL
                           │
                           ▼
                  Cache Invalidation
                           │
                           ▼
                       Response
```

The database is updated first.

The affected cache is then invalidated.

---

## 29. Complete Single-Product Architecture

The individual product request combines several Redis concepts.

```text
GET /products/<id>/
          │
          ▼
   Check Negative Cache
          │
     ┌────┴────┐
     │         │
    HIT       MISS
     │         │
     ▼         ▼
    404    Check Product Cache
                 │
            ┌────┴────┐
            │         │
           HIT       MISS
            │         │
            ▼         ▼
         Response   Acquire Lock
                       │
                       ▼
                 Check Cache Again
                       │
                  ┌────┴────┐
                  │         │
                 HIT       MISS
                  │         │
                  ▼         ▼
               Response  PostgreSQL
                             │
                             ▼
                           Redis
                             │
                             ▼
                          Response
```

This flow combines:

```text
Redis Hash
Cache HIT / MISS
TTL
Redis Lock
Negative Cache
PostgreSQL
Fallback
```

---

## 30. Complete Project Architecture

The final project architecture can be represented as:

```text
                         CLIENT
                       / POSTMAN
                           │
                           │ HTTP
                           ▼
                  ┌──────────────────┐
                  │      DJANGO      │
                  │    PRODUCT API   │
                  └────────┬─────────┘
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
        ┌───────────┐              ┌────────────┐
        │   REDIS   │              │ PostgreSQL │
        │   CACHE   │              │   SOURCE   │
        │           │              │ OF TRUTH   │
        └───────────┘              └────────────┘
             │
      ┌──────┼───────────────────────┐
      │      │          │            │
      ▼      ▼          ▼            ▼
   Cache   Hashes    Counters      Locks
      │
      ├── products:all
      ├── product:<id>
      ├── product:<id>:views
      ├── product:<id>:not_found
      └── lock:product:<id>
```

---

## 31. Architecture Principles

The project follows these main principles:

### PostgreSQL is the Source of Truth

```text
PostgreSQL
     ↓
Permanent application data
```

### Redis is the Performance Layer

```text
Redis
  ↓
Fast temporary / derived data
```

### Reads Prefer Redis

```text
Request
   ↓
Redis
   ↓
HIT → Response
```

### Cache MISS Uses PostgreSQL

```text
Redis MISS
    ↓
PostgreSQL
    ↓
Redis
    ↓
Response
```

### Writes Update PostgreSQL

```text
POST / PUT / DELETE
        ↓
PostgreSQL
```

### Changed Cache Data Is Invalidated

```text
Database Change
       ↓
Cache Invalidation
```

### TTL Provides Automatic Expiration

```text
Cache
  ↓
Time passes
  ↓
TTL expires
  ↓
Key removed
```

### Redis Locks Protect Cache Rebuilding

```text
Multiple MISS
      ↓
Redis Lock
      ↓
One request rebuilds cache
```

### Negative Caching Protects Against Repeated Missing Requests

```text
Not Found
    ↓
Negative Cache
    ↓
Repeated request
    ↓
Negative Cache HIT
```

---

## 32. Final Architecture Mental Model

The entire project can be remembered using this model:

```text
                         CLIENT
                           │
                           ▼
                        DJANGO
                           │
                    ┌──────┴──────┐
                    │             │
                    ▼             ▼
                  REDIS       POSTGRESQL
                  CACHE       SOURCE OF
                               TRUTH
                    │             │
              ┌─────┴─────┐       │
              │           │       │
             HIT         MISS     │
              │           │       │
              │           ▼       │
              │       PostgreSQL ──┘
              │           │
              │           ▼
              │         Redis
              │           │
              └─────┬─────┘
                    ▼
                 RESPONSE
```

The complete architectural relationship is:

```text
Client
  ↓
Django API
  ↓
Redis Cache
  ↓
PostgreSQL Source of Truth
```

with Redis additionally providing:

```text
Caching
   +
TTL
   +
Hashes
   +
Counters
   +
Locks
   +
Negative Caching
   +
Failure-aware fallback
```

This architecture represents the final structure of the Redis Learning Project.

# Redis Learning Project — Learning Outcomes

## 1. What This Document Contains

This document summarizes the knowledge and practical skills gained from completing the Redis Learning Project.

The project was designed to understand Redis by implementing it inside a real Django backend rather than learning Redis only through theory.

The major learning areas were:

```text id="z6j3q1"
Redis Fundamentals
Redis Commands
Caching
Cache-Aside
Cache Invalidation
TTL
Redis Hashes
Counters
Cache Stampede
Redis Locks
Cache Penetration
Negative Caching
Redis Failure Handling
Key Naming
SCAN
Memory
Eviction
API Integration
Testing
Debugging
```

---

# 2. Core Redis Understanding

The most important understanding gained from the project is that Redis is an **in-memory data store** that can be used as a fast supporting layer for backend applications.

The project architecture is:

```text id="f4m8x2"
Client
  ↓
Django
  ↓
Redis
  ↓
PostgreSQL
```

But PostgreSQL remains the source of truth.

```text id="q9c5v7"
PostgreSQL
    =
Source of Truth

Redis
    =
Cache / Performance Layer
```

---

# 3. Redis as a Cache

The project demonstrated why Redis is useful for caching.

Without caching:

```text id="p6k2r8"
Request
   ↓
Django
   ↓
PostgreSQL
   ↓
Response
```

With Redis:

```text id="w3n7m1"
Request
   ↓
Django
   ↓
Redis
   ↓
HIT
   ↓
Response
```

The database does not need to be accessed for every cache-hit request.

---

# 4. Cache-Aside Pattern

The project implemented the Cache-Aside pattern.

The complete flow is:

```text id="s8q4v2"
Request
   ↓
Check Redis
   ↓
 ┌──────────────┐
 │              │
HIT            MISS
 │              │
 ↓              ↓
Return       PostgreSQL
               ↓
           Redis SET
               ↓
            Response
```

This became the main caching pattern used throughout the project.

---

# 5. Cache HIT and MISS

A **Cache HIT** occurs when the requested data already exists in Redis.

```text id="c7m2x9"
Request
  ↓
Redis
  ↓
HIT
  ↓
Response
```

A **Cache MISS** occurs when the requested data is not available in Redis.

```text id="r4k8p1"
Request
  ↓
Redis
  ↓
MISS
  ↓
PostgreSQL
  ↓
Redis
  ↓
Response
```

Understanding this distinction is fundamental to understanding caching.

---

# 6. Cache Invalidation

The project demonstrated that cached data can become stale after a database modification.

Therefore:

```text id="n5v9c3"
POST
PUT
DELETE
```

can require cache invalidation.

General pattern:

```text id="x2m7q6"
Database Change
      ↓
Affected Cache
      ↓
Invalidate
      ↓
Next Read
      ↓
Cache MISS
      ↓
Fresh Database Data
      ↓
Redis Rebuild
```

---

# 7. TTL

TTL means **Time To Live**.

It determines how long a Redis key should remain before automatic expiration.

The project used different TTL values for different purposes.

```text id="a8r3w5"
Product cache       → 60 seconds
List cache          → 60 seconds
Negative cache      → 30 seconds
Redis lock          → 10 seconds
View counter        → No TTL
```

The project also learned:

```text id="g6p1z4"
TTL > 0
→ Key exists and has expiration

TTL -1
→ Key exists without expiration

TTL -2
→ Key does not exist
```

---

# 8. Redis Hashes

Individual products were represented using Redis Hashes.

Example:

```text id="u4m8q2"
product:1
├── id
├── name
├── price
└── stock
```

Commands practiced included:

```text id="r7x3n9"
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

This demonstrated how Redis can represent structured object-like data.

---

# 9. Redis Counters

The project used Redis counters for product views.

Example key:

```text id="j5c9v2"
product:1:views
```

Commands practiced:

```text id="s3m7x8"
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT
```

The project demonstrated that Redis can efficiently maintain numeric counters.

---

# 10. Cache Stampede

A cache stampede occurs when a popular cache entry expires and many requests simultaneously attempt to rebuild it.

Without protection:

```text id="k8q2m5"
Request 1 → Database
Request 2 → Database
Request 3 → Database
Request 4 → Database
```

This can create unnecessary database load.

The project used Redis locking to coordinate cache rebuilding.

---

# 11. Redis Locks

The project used:

```text id="p3v7x1"
lock:product:<id>
```

Example:

```text id="h6m2q8"
lock:product:1
```

The basic operation was:

```text id="y9c4r6"
SET lock:product:1 1 NX EX 10
```

The important concepts learned were:

```text id="w2n8m5"
NX
→ Create only if the key does not exist.

EX
→ Give the lock an expiration.
```

The lock ensures that one request can take responsibility for rebuilding a missing cache while other requests wait or retry.

---

# 12. Cache Penetration

Cache penetration occurs when requests repeatedly target data that does not exist.

Example:

```text id="f7k3p9"
GET /products/999/
```

Without protection:

```text id="z2m6x4"
Request
 ↓
Redis MISS
 ↓
PostgreSQL
 ↓
Not Found
```

Repeated requests could repeatedly reach PostgreSQL.

---

# 13. Negative Caching

The project solved repeated nonexistent-product requests using negative caching.

Key:

```text id="q5v8n1"
product:999:not_found
```

Value:

```text id="t3x7m4"
NOT_FOUND
```

TTL:

```text id="c8r2p6"
30 seconds
```

Flow:

```text id="y1m9q3"
First Request
    ↓
PostgreSQL
    ↓
Not Found
    ↓
Negative Cache

Next Request
    ↓
Negative Cache HIT
    ↓
404
```

This reduces repeated database lookups for the same missing resource.

---

# 14. Redis Failure Handling

The project demonstrated that Redis should not be treated as the permanent source of truth.

When Redis was stopped:

```text id="u7k4m2"
Redis request
   ↓
Connection failure
   ↓
PostgreSQL fallback
   ↓
Response
```

The observed error was:

```text id="b3n8x5"
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

After restarting Memurai:

```text id="n6q2r8"
memurai-cli ping
```

returned:

```text id="v4m1x7"
PONG
```

The cache could then be rebuilt normally.

---

# 15. Redis as a Replaceable Layer

One of the most important architectural lessons was:

```text id="s5c9m3"
Redis data can disappear.
```

The application should still be able to obtain the real data from PostgreSQL.

Therefore:

```text id="j8x2p6"
PostgreSQL
      ↓
Permanent data

Redis
      ↓
Temporary cached representation
```

If Redis is empty:

```text id="r4m7n1"
PostgreSQL
   ↓
Rebuild Redis
```

---

# 16. Key Naming Strategy

The project developed a structured Redis key naming convention.

Examples:

```text id="c7x3m9"
products:all

product:1

product:1:views

product:999:not_found

lock:product:1
```

General patterns:

```text id="p2n8v4"
<resource>:<id>

<resource>:<id>:<purpose>

lock:<resource>:<id>
```

This makes Redis keys easier to understand and manage.

---

# 17. SCAN and Key Management

The project practiced:

```text id="m6q1x8"
SCAN
MATCH
COUNT
```

Example:

```text id="w3r7k2"
SCAN 0 MATCH product:*
```

This helped inspect related keys.

The project also compared key inspection approaches and learned why incremental scanning is preferable to blindly using large keyspace operations on production systems.

---

# 18. Memory and Eviction

Redis stores data in memory.

The project inspected memory configuration using:

```text id="x8c4m7"
CONFIG GET maxmemory
```

Observed:

```text id="n5q2p9"
8589934592
```

approximately:

```text id="s1v6r3"
8 GB
```

The configured eviction policy was:

```text id="g7m3k5"
noeviction
```

Memory information was inspected using:

```text id="u9r4x2"
INFO memory
```

Important concepts studied included:

```text id="c6p8n1"
LRU
LFU
allkeys
volatile
```

---

# 19. Redis Command Knowledge

The project provided practical experience with the following command groups.

### Basic

```text id="q2m7x4"
SET
GET
EXISTS
DEL
```

### Expiration

```text id="j5r9c3"
EXPIRE
TTL
PERSIST
```

### Hashes

```text id="v8n1k6"
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

```text id="p4x7m2"
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT
```

### Locks

```text id="n9c3r5"
SET NX
SET NX EX
```

### Key Management

```text id="k6m2v8"
SCAN
MATCH
COUNT
```

### Configuration

```text id="x3q7p1"
CONFIG GET
CONFIG SET
INFO memory
PING
```

---

# 20. Django + Redis Integration

The project demonstrated how Redis can be integrated into a normal Django application.

The main Redis client is located at:

```text id="m8r4c2"
config/redis_client.py
```

The API layer uses the Redis client when reading and managing cached data.

The architecture is:

```text id="y5n9p3"
Django View
    ↓
Redis Client
    ↓
Redis / Memurai
```

PostgreSQL remains connected through Django's normal database layer.

---

# 21. API Understanding

The project implemented:

```text id="z7x2m4"
GET     /products/
GET     /products/<id>/
POST    /products/
PUT     /products/<id>/
DELETE  /products/<id>/
```

The important learning was not only how to create these endpoints, but how Redis changes the internal behavior of the read and write operations.

---

# 22. Read Path

The project's read path can be summarized as:

```text id="c4p8m1"
Client
  ↓
Django
  ↓
Redis
  ↓
 ┌───────────┐
 │           │
 HIT        MISS
 │           │
 ↓           ↓
Response  PostgreSQL
             ↓
           Redis
             ↓
          Response
```

This is the main Cache-Aside lifecycle.

---

# 23. Write Path

The write path is:

```text id="r6x3k9"
Client
  ↓
Django
  ↓
PostgreSQL
  ↓
Cache Invalidation
  ↓
Response
```

The next read can rebuild the affected cache.

---

# 24. Testing and Debugging Skills

The project also developed a practical debugging workflow.

When something did not behave as expected:

```text id="n2v7c5"
1. Check Django response
2. Check Django console
3. Inspect Redis key
4. Check TTL
5. Check PostgreSQL data
6. Repeat the request
7. Compare Redis and database state
```

This is especially useful when debugging caching because an API response alone does not reveal where the data came from.

---

# 25. Performance Understanding

The project observed a request latency difference during cache testing:

```text id="k5m8x1"
Initial request ≈ 209 ms
Subsequent request ≈ 4 ms
```

These values are environment-dependent.

The important lesson is:

```text id="p3q7r2"
Database work
    ↓
More expensive

Cached memory access
    ↓
Much faster
```

The actual performance improvement depends on the application, database, network, Redis configuration, and workload.

---

# 26. Production Considerations Learned

The project is primarily a learning implementation.

Several areas would require stronger production-grade implementations.

### Redis failure handling

The project has a fallback for the implemented single-product GET path.

A production application would need consistent Redis failure handling across all Redis operations.

### Lock ownership

The learning implementation uses a Redis lock with expiration.

Production distributed locking requires careful lock ownership and safe release.

### Error handling

Production code should generally catch specific Redis exceptions rather than relying on broad exception handling.

### Security

The local learning project focuses on Redis concepts rather than production security hardening.

---

# 27. What Can Now Be Explained

After completing the project, the following questions can be explained using the actual implementation.

### What is Redis?

An in-memory data store used in the project as a fast supporting layer.

### Why use Redis?

To reduce repeated database work and improve read performance.

### What is Cache-Aside?

Check Redis first, query the database on a miss, then populate Redis.

### What is cache invalidation?

Removing stale cached data after the underlying database data changes.

### What is TTL?

The lifetime assigned to a Redis key before automatic expiration.

### What is a cache stampede?

Many requests simultaneously rebuilding the same missing cache.

### How can Redis locks help?

They allow one request to rebuild the cache while coordinating other concurrent requests.

### What is cache penetration?

Repeated requests for data that does not exist.

### How does negative caching help?

It temporarily stores the fact that a requested resource does not exist.

### What happens if Redis fails?

The application can fall back to PostgreSQL for the implemented fallback path.

---

# 28. Complete Project Knowledge Map

The entire project can now be represented as:

```text id="v9m4x2"
                    REDIS
                      │
       ┌──────────────┼──────────────┐
       │              │              │
     Caching       Data Types     Operations
       │              │              │
       │           Hashes          SET / GET
       │           Counters        DEL
       │                           TTL
       │
 ┌─────┼─────────────────────────────┐
 │     │                             │
HIT   MISS                     Invalidation
 │     │                             │
 │   Database                        │
 │     │                             │
 │   Cache                          POST
 │   Populate                        PUT
 │                                    DELETE
 │
 └──────────────┬─────────────────────┘
                │
        Advanced Problems
                │
      ┌─────────┼─────────┐
      │         │         │
  Stampede  Penetration Failure
      │         │         │
    Locks   Negative    Fallback
             Cache
```

---

# 29. Final Architecture Understanding

The project ultimately established this mental model:

```text id="k3x8p5"
                    CLIENT
                       │
                       ▼
                  DJANGO API
                       │
             ┌─────────┴─────────┐
             │                   │
             ▼                   ▼
           REDIS             POSTGRESQL
           CACHE             SOURCE OF
                               TRUTH
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
                    RESPONSE
```

Redis improves performance.

PostgreSQL stores the authoritative application data.

Django coordinates the interaction.

The client communicates through the API.

---

# 30. Final Learning Outcome

The main outcome of this project is not simply knowing Redis commands.

The main outcome is understanding the complete lifecycle:

```text id="q7m2x9"
Problem
  ↓
Redis Concept
  ↓
Redis Command
  ↓
Django Integration
  ↓
API Request
  ↓
Redis Behavior
  ↓
PostgreSQL Interaction
  ↓
Cache Update / Invalidation
  ↓
Testing
  ↓
Failure Handling
```

This provides a practical foundation for using Redis in backend applications.

---

# 31. Project Completion Summary

The major project topics completed were:

```text id="x5r8n3"
✓ Redis Fundamentals
✓ Basic Commands
✓ Cache-Aside
✓ Cache HIT / MISS
✓ Cache Invalidation
✓ TTL
✓ Redis Hashes
✓ Redis Counters
✓ Cache Stampede
✓ Redis Locks
✓ Cache Penetration
✓ Negative Caching
✓ Redis Failure / Fallback
✓ Redis Recovery
✓ Key Naming Strategy
✓ SCAN
✓ Memory
✓ Eviction Concepts
✓ API Integration
✓ Postman Testing
✓ Redis CLI Testing
✓ Debugging
✓ Project Documentation
```

The Redis Learning Project can therefore serve as a practical reference for understanding how Redis is integrated into a Django backend and how common caching problems are handled.

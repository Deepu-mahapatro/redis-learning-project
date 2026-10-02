# Redis Learning Project — Cache Strategies

## 1. Caching Architecture

The project uses Redis as a caching layer between Django and PostgreSQL.

```text id="2u5xhl"
                    Client
                      │
                      ▼
                   Django
                  ↙      ↘
               Redis    PostgreSQL
               Cache    Source of Truth
```

The main principle is:

```text id="8f7y5c"
PostgreSQL → authoritative data
Redis      → fast temporary data
```

Redis improves read performance while PostgreSQL remains responsible for persistent product data.

---

# 2. Cache-Aside Pattern

The main caching strategy implemented in the project is **Cache-Aside**.

The application checks Redis first. If the requested data is available, it returns the cached data. If not, it reads from PostgreSQL and then stores the result in Redis.

```text id="0k9u2a"
Request
   ↓
Django
   ↓
Redis
 ┌─┴───────┐
HIT       MISS
 ↓          ↓
Return   PostgreSQL
             ↓
          Redis SET
             ↓
          Response
```

The application, rather than Redis itself, controls when data is read from or written to the cache.

---

# 3. Cache HIT

A **Cache HIT** occurs when the requested data already exists in Redis.

Example:

```text id="d9x3q1"
GET /products/
```

Flow:

```text id="v6p8ec"
Request
   ↓
Django
   ↓
Redis
   ↓
products:all exists
   ↓
CACHE HIT
   ↓
Return cached data
```

The database does not need to be queried for that request.

For an individual product:

```text id="j9z1ke"
GET /products/1/
```

Redis checks:

```text id="kj2j7h"
product:1
```

If the hash exists and contains the required fields, the cached product can be returned.

---

# 4. Cache MISS

A **Cache MISS** occurs when the requested data is not present in Redis.

Example:

```text id="n5y6b3"
GET /products/
```

Flow:

```text id="g4h0xm"
Request
   ↓
Redis
   ↓
MISS
   ↓
PostgreSQL
   ↓
Retrieve products
   ↓
Store in Redis
   ↓
Return response
```

The next request can then use the newly populated cache.

---

# 5. Cache Population

Cache population means placing database data into Redis after a cache miss.

For the product collection:

```text id="x5o3md"
PostgreSQL
    ↓
Product data
    ↓
Redis
    ↓
products:all
```

For an individual product:

```text id="g7f2p9"
PostgreSQL
    ↓
Product
    ↓
Redis Hash
    ↓
product:<id>
```

The cache therefore becomes populated as the application receives requests.

---

# 6. Cache Invalidation

Cached data can become stale when the underlying PostgreSQL data changes.

For example:

```text id="x5r0qw"
PostgreSQL
product:1 price = 55000

Redis
product:1 price = 55000
```

If PostgreSQL changes:

```text id="6c9j2k"
PostgreSQL
product:1 price = 60000
```

but Redis still contains:

```text id="w5h8r4"
product:1 price = 55000
```

Redis now contains stale data.

The solution implemented is **cache invalidation**.

```text id="v2q4z7"
Database changes
       ↓
Delete relevant Redis cache
       ↓
Next GET
       ↓
Cache MISS
       ↓
PostgreSQL
       ↓
Rebuild cache
```

---

# 7. POST Cache Invalidation

When a new product is created:

```text id="3x7nq0"
POST /products/
```

the product is first created in PostgreSQL.

The all-products cache may now be outdated.

Therefore:

```text id="m5b9p2"
POST
 ↓
PostgreSQL INSERT
 ↓
Invalidate products:all
```

The next:

```text id="y1c4r8"
GET /products/
```

causes:

```text id="k2f6v0"
Redis MISS
 ↓
PostgreSQL
 ↓
Rebuild products:all
```

---

# 8. PUT Cache Invalidation

When a product is updated:

```text id="z8p3k1"
PUT /products/1/
```

the PostgreSQL record is updated.

Relevant cached data must then be invalidated.

The project invalidates the individual product cache and collection cache.

The negative cache for that product is also removed:

```text id="m9q4s2"
product:<id>
products:all
product:<id>:not_found
```

The next read rebuilds the correct cache from PostgreSQL.

---

# 9. DELETE Cache Invalidation

When a product is deleted:

```text id="q7h2x9"
DELETE /products/4/
```

the PostgreSQL record is removed.

The corresponding cached data must also be invalidated.

Conceptually:

```text id="c5n8p0"
DELETE
 ↓
PostgreSQL DELETE
 ↓
Invalidate Redis cache
 ↓
Future GET
 ↓
Redis MISS
 ↓
PostgreSQL
 ↓
Product not found
```

---

# 10. TTL Strategy

TTL provides automatic expiration for cached data.

The project uses different TTL values based on the purpose of the key.

```text id="q3m7k9"
product:<id>           → 60 seconds
products:all            → 60 seconds
product:<id>:not_found  → 30 seconds
lock:product:<id>       → 10 seconds
product:<id>:views      → no TTL
```

This demonstrates that not every Redis key needs the same lifetime.

### Why?

A product cache can remain useful for a short period:

```text id="x6r2k8"
60 seconds
```

A negative cache should expire sooner because the product could be created later:

```text id="h1p5s7"
30 seconds
```

A lock should be short-lived to prevent a stuck lock:

```text id="a4m9q2"
10 seconds
```

A view counter was kept without a TTL in this learning project.

---

# 11. Cache Invalidation vs TTL

These are different mechanisms.

### Invalidation

Triggered by a known data change:

```text id="1m8f4s"
PUT product
 ↓
Delete cache
```

### TTL

Triggered by time:

```text id="j6q2v9"
Cache created
 ↓
60 seconds
 ↓
Expires
```

The project uses both:

```text id="w7c3p1"
Known data change
       ↓
Invalidation

Time passes
       ↓
TTL expiration
```

---

# 12. Cache Stampede

A cache stampede can happen when a popular cache entry expires and many requests arrive at nearly the same time.

Example:

```text id="b5z8x2"
Popular cache expires
       ↓
100 requests
       ↓
100 Redis MISS
       ↓
100 PostgreSQL queries
```

This can suddenly create a large database load.

---

# 13. Redis Lock as Stampede Protection

The project uses a Redis lock to ensure that only one request rebuilds the cache.

The lock uses:

```text id="x2n7m4"
SET lock:product:<id> 1 NX EX 10
```

`NX` ensures that only one request can successfully create the lock.

The expiration prevents a lock from remaining forever.

---

# 14. Cache Stampede Flow

The implemented flow is:

```text id="p8v3k1"
Request A ──┐
Request B ──┤
Request C ──┤
             ↓
        Redis Cache MISS
             ↓
        Try Redis Lock
             ↓
       ┌─────┴─────┐
       │           │
    Lock Holder  Others
       │           │
       ▼           ▼
 PostgreSQL      Wait/Retry
       │           │
       ▼           │
  Rebuild Redis   │
       │           │
       └─────┬─────┘
             ▼
        Redis HIT
             ↓
          Response
```

The lock holder:

1. Acquires the lock.
2. Rechecks Redis.
3. Queries PostgreSQL if the cache is still missing.
4. Rebuilds the cache.
5. Releases the lock.

Waiting requests check Redis again and can use the rebuilt cache.

---

# 15. Cache Penetration

Cache penetration occurs when requests repeatedly ask for data that does not exist.

Example:

```text id="x8k2m5"
GET /products/999/
```

If Product 999 does not exist:

```text id="q6n4p1"
Redis MISS
    ↓
PostgreSQL
    ↓
Not Found
    ↓
404
```

Without protection, every repeated request can repeat the database query.

---

# 16. Negative Caching

The project solves this using negative caching.

When PostgreSQL confirms that the product does not exist, Redis stores:

```text id="c7v1x9"
product:999:not_found = NOT_FOUND
```

with a 30-second TTL.

The flow becomes:

```text id="n2m6q8"
First request
    ↓
Redis MISS
    ↓
PostgreSQL MISS
    ↓
Store NOT_FOUND
    ↓
404
```

Next request:

```text id="r5k9z3"
Request
    ↓
Redis
    ↓
Negative Cache HIT
    ↓
404
```

PostgreSQL does not need to be queried again while the negative cache exists.

---

# 17. Why Negative Cache Uses TTL

Negative caching must not exist forever.

Suppose Product 999 doesn't exist now:

```text id="f8k3m2"
product:999 → NOT_FOUND
```

Later, someone creates Product 999.

If the negative cache never expired:

```text id="q1v7s4"
Redis → NOT_FOUND
```

the application could incorrectly continue returning 404.

Therefore:

```text id="a6m9p2"
Negative Cache
     ↓
Short TTL
     ↓
Expires
     ↓
Future request checks PostgreSQL again
```

The project uses:

```text id="h3x8k5"
EX 30
```

for the negative cache.

---

# 18. Redis Failure / Fallback

Redis is an optimization layer, so the application should not depend entirely on Redis for the authoritative product data.

During testing, Memurai was stopped.

The application encountered:

```text id="t5p2x8"
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine
actively refused it.
```

For the implemented single-product read path, the application handled the Redis failure by reading directly from PostgreSQL.

```text id="c9m4v7"
Request
   ↓
Redis unavailable
   ↓
PostgreSQL
   ↓
Product data
   ↓
Response
```

This preserves access to the source-of-truth data even when Redis is unavailable.

---

# 19. Redis Recovery

After Memurai was restarted:

```text id="w8q3n1"
Redis
 ↓
PONG
```

the normal cache-aside behavior became available again.

If the cache was missing:

```text id="p6v2k9"
Request
 ↓
Redis MISS
 ↓
PostgreSQL
 ↓
Rebuild Redis
 ↓
Response
```

The next request could then use the Redis cache.

```text id="m4x7c2"
Next request
 ↓
Redis HIT
 ↓
Response
```

---

# 20. Combined Single-Product Strategy

The single-product API combines several strategies into one request path.

```text id="z7m2q5"
GET /products/<id>/
          ↓
   Negative Cache Check
          ↓
   Product Cache Check
          ↓
      ┌───┴───┐
     HIT     MISS
      │         │
      │       Lock
      │         │
      │    Recheck Cache
      │         │
      │      PostgreSQL
      │         │
      │    ┌────┴────┐
      │   Found    Missing
      │     │          │
      │   Redis    Negative Cache
      │     │          │
      └─────┴──────────┘
             ↓
          Response
```

The flow therefore combines:

- Cache HIT/MISS
- Redis Hash
- TTL
- Negative caching
- Redis lock
- PostgreSQL fallback
- View counter

---

# 21. Strategy-to-API Mapping

| API | Caching Strategy |
|---|---|
| `GET /products/` | Cache-Aside + TTL |
| `GET /products/<id>/` | Cache-Aside + Hash + TTL + Lock + Negative Cache + Counter + Fallback |
| `POST /products/` | PostgreSQL write + Cache Invalidation |
| `PUT /products/<id>/` | PostgreSQL update + Cache Invalidation |
| `DELETE /products/<id>/` | PostgreSQL delete + Cache Invalidation |

---

# 22. Complete Caching Lifecycle

The overall lifecycle implemented in the project is:

```text id="u6y3p8"
                  REQUEST
                     │
                     ▼
                   Redis
                     │
             ┌───────┴────────┐
             │                │
            HIT              MISS
             │                │
             │          Check special cases
             │                │
             │        ┌───────┴────────┐
             │        │                │
             │      Negative          Lock
             │       Cache             │
             │        │                │
             │       HIT             PostgreSQL
             │        │                │
             │       404          Rebuild Cache
             │                         │
             └───────────┬─────────────┘
                         ▼
                     RESPONSE
```

For writes:

```text id="j4n8c2"
POST / PUT / DELETE
          ↓
      PostgreSQL
          ↓
    Invalidate Cache
          ↓
      Future GET
          ↓
       Cache MISS
          ↓
      Rebuild Cache
```

---

# 23. Key Lessons

The project demonstrated that Redis caching is not simply:

```text id="s5k2v7"
Database → Redis
```

A reliable caching design also needs to consider:

```text id="g8q3m1"
Cache HIT/MISS
      ↓
Invalidation
      ↓
Expiration
      ↓
Concurrent requests
      ↓
Nonexistent data
      ↓
Redis failure
      ↓
Recovery
      ↓
Key management
```

The main principle learned from the project is:

> **Redis improves performance, but application logic must determine how cached data is created, invalidated, expired, protected, and recovered.**


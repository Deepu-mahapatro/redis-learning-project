# Redis Learning Project — Testing

## 1. What This Document Contains

This document records the testing performed during the Redis Learning Project.

The purpose of testing was not only to verify that the APIs work, but also to verify that Redis behaves correctly in each important scenario.

The testing covered:

- Redis commands
- Django APIs
- Cache HIT/MISS
- TTL
- Cache invalidation
- Redis Hashes
- Counters
- Cache stampede protection
- Redis locks
- Negative caching
- Redis failure and fallback
- Redis recovery
- Memory and eviction concepts
- Redis key inspection

---

# 2. Testing Environment

The project uses:

```text
Python
Django
PostgreSQL
Redis-compatible Memurai
Postman
Redis CLI
```

Main components:

```text
Postman
   ↓
Django
   ↓
Redis / Memurai
   ↓
PostgreSQL
```

---

# 3. Redis Connectivity Test

Before testing the application, Redis availability was verified.

Command:

```text id="7o3k1n"
memurai-cli ping
```

Observed output:

```text id="x5c8m2"
PONG
```

### Meaning

Redis/Memurai was running and accepting connections.

---

# 4. Basic Redis Command Testing

Basic Redis operations were tested manually before integrating Redis with Django.

## SET

```text id="k3v7p1"
SET test_key "hello_redis"
```

Expected:

```text id="w8m2q5"
OK
```

## GET

```text id="n4c9r6"
GET test_key
```

Expected:

```text id="p2x7s1"
"hello_redis"
```

## EXISTS

```text id="d6y1m8"
EXISTS test_key
```

Expected:

```text id="j5k3v9"
(integer) 1
```

## DELETE

```text id="r8q2w4"
DEL test_key
```

Expected:

```text id="m1c6z7"
(integer) 1
```

These tests confirmed the basic Redis storage lifecycle.

---

# 5. Django-to-Redis Connectivity Test

Redis was also tested from the Django environment.

The project used the Redis client configured in:

```text id="f7p3k9"
config/redis_client.py
```

The test performed:

```text id="c2x8m5"
redis_client.set("test_key", "hello_redis")
redis_client.get("test_key")
```

Observed results:

```text id="v6n1q4"
True
'hello_redis'
```

This confirmed that Django could communicate with Redis.

---

# 6. TTL Testing

TTL behavior was tested using:

```text id="a4m8x2"
TTL <key>
```

Three important results were verified.

## Positive TTL

```text id="h9p3w6"
TTL cache:test
```

A positive value means:

```text
The key exists and has an expiration.
```

---

## TTL `-1`

```text id="s2k7n5"
(integer) -1
```

Meaning:

```text
The key exists but has no expiration.
```

---

## TTL `-2`

```text id="q8c4r1"
(integer) -2
```

Meaning:

```text
The key does not exist.
```

This distinction was important throughout the project.

---

# 7. Cache-Aside Testing

The main caching strategy was tested using:

```text id="y5v9k3"
GET /products/
```

The collection cache key is:

```text id="m2x7p4"
products:all
```

---

# 8. Cache MISS Test

When:

```text id="b6n1w8"
products:all
```

did not exist:

```text id="r3q8z5"
GET /products/
```

caused the application to:

```text
Redis MISS
    ↓
PostgreSQL
    ↓
Retrieve products
    ↓
Store products in Redis
    ↓
Return response
```

This verified the cache population flow.

---

# 9. Cache HIT Test

After the cache was populated, the same request was sent again:

```text id="g7m2c9"
GET /products/
```

The second request could read the cached data.

Flow:

```text id="x4p8v1"
GET /products/
      ↓
Redis
      ↓
HIT
      ↓
Response
```

This verified the main purpose of the cache.

---

# 10. Cache Performance Observation

During testing, request latency was observed to change from approximately:

```text id="s6w2k8"
209 ms
```

for an initial request to approximately:

```text id="j1q5r7"
4 ms
```

for subsequent cached requests.

The exact latency depends on the local environment, but the observation demonstrated the intended performance benefit of avoiding repeated database work.

---

# 11. Cache Invalidation Testing

Cache invalidation was tested after write operations.

The main collection cache is:

```text id="v8n3m6"
products:all
```

When product data changes, the cache must no longer contain stale information.

---

# 12. POST Invalidation Test

A product was created through the API.

Example:

```text id="e2k7p4"
POST /products/
```

After the database change, the collection cache was invalidated.

Flow:

```text id="c9r1x5"
POST
 ↓
PostgreSQL CREATE
 ↓
DEL products:all
 ↓
Response
```

The next GET rebuilt the cache using the updated database data.

---

# 13. PUT Invalidation Test

A product was updated.

Example project change:

```text id="q4m8z2"
Product 1
Price: 55000 → 60000
```

The application invalidated the relevant cache entries.

Flow:

```text id="w7p2n5"
PUT
 ↓
PostgreSQL UPDATE
 ↓
Invalidate product cache
 ↓
Invalidate list cache
 ↓
Response
```

The next GET rebuilt the cache with the updated product information.

---

# 14. DELETE Invalidation Test

A product was deleted.

The project deleted the Monitor product during CRUD testing.

Flow:

```text id="k5x9c3"
DELETE
 ↓
PostgreSQL DELETE
 ↓
Invalidate product cache
 ↓
Invalidate list cache
 ↓
Response
```

The next list request returned the current database state.

---

# 15. Redis Hash Testing

Individual products use Redis Hashes.

Example key:

```text id="m8v2q6"
product:1
```

Hash fields:

```text
id
name
price
stock
```

Commands practiced included:

```text id="f3k7p1"
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

The main application read operation uses the Hash representation of the product.

---

# 16. Product Hash Inspection

The product cache was inspected using:

```text id="x9c4m2"
HGETALL product:1
```

This allowed the cached representation of the product to be directly inspected in Redis.

This was useful for verifying that the Redis data matched the product information returned by the API.

---

# 17. Counter Testing

The project uses:

```text id="p6w3n8"
product:1:views
```

for a Redis-based view counter.

The counter was tested with:

```text id="t2m7k5"
INCR product:1:views
```

Repeated increments demonstrated that Redis can maintain a lightweight numeric counter.

Other counter commands were also practiced:

```text id="a8q4v1"
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT
```

---

# 18. Cache Stampede Testing

Cache stampede was studied by considering multiple requests arriving after the same cache entry becomes unavailable.

The problematic flow is:

```text id="r5c9x2"
Cache expires
     ↓
Multiple requests
     ↓
Redis MISS
     ↓
Multiple database queries
```

The project implemented Redis locking to prevent this behavior.

---

# 19. Redis Lock Testing

The lock key follows:

```text id="n7p3m6"
lock:product:<id>
```

Example:

```text id="v4x8q1"
lock:product:1
```

The lock was tested using:

```text id="c2k9w5"
SET lock:product:1 1 NX
```

The first request could acquire the lock.

A second attempt while the lock existed did not acquire it.

The expiration form was also tested:

```text id="m6r1z8"
SET lock:product:1 1 NX EX 10
```

The lock TTL could then be checked with:

```text id="y3q7p4"
TTL lock:product:1
```

---

# 20. Negative Caching Test

A non-existing product was requested:

```text id="h8m2c5"
GET /products/999/
```

The first request followed:

```text id="v1p6x9"
Redis MISS
   ↓
PostgreSQL
   ↓
Product does not exist
   ↓
Negative cache created
   ↓
404
```

Negative-cache key:

```text id="r4k8n2"
product:999:not_found
```

Value:

```text id="q7m3w5"
NOT_FOUND
```

TTL:

```text id="x2c9p6"
30 seconds
```

---

# 21. Negative Cache HIT Test

The same missing product was requested again before the negative cache expired.

Flow:

```text id="j5v8m1"
GET /products/999/
      ↓
Negative cache
      ↓
HIT
      ↓
404
```

The purpose was to prevent repeated database queries for the same nonexistent product.

---

# 22. Redis Failure Testing

Redis failure behavior was explicitly tested.

Memurai was stopped.

Then the following request was sent:

```text id="b7x3q9"
GET /products/1/
```

The application attempted to access Redis and received:

```text id="n4m8c2"
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

The implemented fallback then used PostgreSQL.

Flow:

```text id="w6p2k5"
Request
   ↓
Redis
   ↓
Connection failure
   ↓
PostgreSQL
   ↓
Product response
```

This demonstrated that Redis is treated as a supporting cache rather than the source of truth.

---

# 23. Redis Recovery Testing

After the failure test, Memurai was restarted.

Command:

```text id="c9r4x7"
memurai-cli ping
```

Observed:

```text id="a2m6v8"
PONG
```

The application could then use Redis again.

The next request could rebuild the cache, followed by normal cache HIT behavior.

---

# 24. Key Naming Testing

The project followed a consistent naming pattern.

Examples:

```text id="y7p3m1"
products:all
product:1
product:1:views
product:999:not_found
lock:product:1
```

The naming structure makes the purpose of each key easy to identify.

---

# 25. SCAN Testing

Redis keys were inspected using:

```text id="f8n2c6"
SCAN 0
```

Pattern matching was also practiced:

```text id="k4x7q1"
SCAN 0 MATCH product:*
```

Other examples:

```text id="m3v9p5"
SCAN 0 MATCH lock:*
```

and:

```text id="r6w2z8"
SCAN 0 MATCH *:not_found
```

This helped inspect related keys without relying on a large blocking key lookup.

---

# 26. Memory Testing

Redis memory configuration was inspected with:

```text id="t8c3m7"
CONFIG GET maxmemory
```

Observed:

```text id="q5v1x9"
8589934592
```

This corresponds to approximately:

```text
8 GB
```

The eviction policy was checked using:

```text id="j2m6p4"
CONFIG GET maxmemory-policy
```

Observed:

```text id="n7x3c8"
noeviction
```

---

# 27. Redis Memory Information

The following command was used:

```text id="w4k9q2"
INFO memory
```

Important observed values included:

```text id="s6m1v8"
used_memory_human:828.39K
maxmemory_human:8.00G
maxmemory_policy:noeviction
```

This provided a view of actual memory usage and configuration.

---

# 28. Eviction Concept Testing

Different eviction policies were studied, including:

```text id="p9c5x2"
noeviction
allkeys-lru
volatile-lru
allkeys-lfu
volatile-lfu
allkeys-random
volatile-random
volatile-ttl
```

The important concepts were:

```text
LRU
→ Least Recently Used

LFU
→ Least Frequently Used

allkeys
→ Any Redis key can be considered

volatile
→ Only keys with TTL can be considered
```

The purpose was to understand what happens when Redis reaches its configured memory limit.

---

# 29. TTL Strategy Verification

The project used different TTLs for different purposes.

| Redis Key | TTL |
|---|---:|
| `product:<id>` | 60 seconds |
| `products:all` | 60 seconds |
| `product:<id>:not_found` | 30 seconds |
| `lock:product:<id>` | 10 seconds |
| `product:<id>:views` | No TTL |

This demonstrates that TTL should be selected according to the purpose of the key.

---

# 30. Invalidation vs TTL Testing

Both mechanisms were verified conceptually and through the application.

### TTL

```text id="u5x8m2"
Cache
 ↓
Time passes
 ↓
TTL reaches 0
 ↓
Key expires
```

### Invalidation

```text id="g3k7p1"
Database changes
 ↓
Cache becomes stale
 ↓
Application deletes cache
 ↓
Next request rebuilds cache
```

The project uses both because they solve different problems.

---

# 31. Testing Summary

The project testing verified the following:

```text id="v8q2m5"
✓ Redis connectivity
✓ Basic Redis commands
✓ Django → Redis connectivity
✓ Cache HIT
✓ Cache MISS
✓ Cache population
✓ Cache invalidation
✓ Redis Hashes
✓ Redis counters
✓ Cache stampede protection
✓ Redis locks
✓ Negative caching
✓ TTL behavior
✓ Redis failure fallback
✓ Redis recovery
✓ Key naming
✓ SCAN
✓ Memory inspection
✓ Eviction concepts
```

---

# 32. Final Testing Model

The testing approach can be summarized as:

```text id="c6m9x3"
          API Request
               ↓
        Observe Response
               ↓
        Inspect Redis
               ↓
       Check PostgreSQL
               ↓
       Verify Cache State
               ↓
        Verify Next Request
```
The important principle was:

Do not only check whether the API returns the correct response. Also verify what happened inside Redis.

That approach made it possible to understand the actual interaction between:

Django
  ↕
Redis
  ↕
PostgreSQL

and confirmed the major Redis concepts implemented in the project

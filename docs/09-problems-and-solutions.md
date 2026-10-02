# Redis Learning Project — Problems and Solutions

## 1. What This Document Contains

This document records the important problems encountered while building and learning through the Redis Learning Project.

The purpose is to document not only the final implementation, but also the problems that helped explain **why Redis features are needed**.

The main areas covered are:

```text
Django + Redis Setup
Redis Connectivity
Cache Misses
Stale Cache
Cache Invalidation
Cache Stampede
Redis Locks
Cache Penetration
Negative Caching
Redis Failure
TTL
Key Management
Memory & Eviction
Testing
```

---

# 2. Redis Connection Problem

## Problem

The Django application could not communicate with Redis when Memurai was not running.

The observed error was:

```text
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

## Cause

Redis-compatible Memurai was not accepting connections on:

```text
localhost:6379
```

## Solution

Memurai was started again.

Connectivity was verified using:

```text
memurai-cli ping
```

Output:

```text
PONG
```

## Lesson

Always verify that Redis is running before testing Redis-dependent functionality.

```text
Django
  ↓
Redis connection
  ↓
Redis must be available
```

---

# 3. Django Redis Client Setup

## Problem

The Django project needed a reusable Redis connection instead of creating Redis configuration repeatedly inside views.

## Solution

A dedicated Redis client was created:

```text
config/redis_client.py
```

The project uses:

```python
import redis

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)
```

## Lesson

Keeping Redis configuration in one location makes the project easier to maintain.

---

# 4. Cache Miss

## Problem

When a requested item is not present in Redis, Django cannot return it from the cache.

Example:

```text
product:1
```

does not exist.

## Solution

Use the Cache-Aside pattern:

```text
Redis MISS
    ↓
PostgreSQL
    ↓
Get product
    ↓
Store in Redis
    ↓
Return response
```

## Lesson

A cache miss is not an error.

It is a normal part of cache-aside caching.

---

# 5. Stale Cache

## Problem

Suppose PostgreSQL contains:

```text
Product 1
Price = 55000
```

Redis contains:

```text
Product 1
Price = 55000
```

Then PostgreSQL is updated:

```text
Price = 60000
```

If Redis still contains:

```text
55000
```

the API could return old data.

This is stale cache.

## Solution

Invalidate affected cache entries after database writes.

For example:

```text
PUT
 ↓
PostgreSQL UPDATE
 ↓
DEL product:1
 ↓
DEL products:all
```

## Lesson

Whenever cached data depends on data being modified, the corresponding cache must be considered for invalidation.

---

# 6. Cache Invalidation Problem

## Problem

Creating, updating, or deleting a product changes the database state.

The Redis cache may still contain the old state.

## Solution

### POST

Invalidate:

```text
products:all
```

### PUT

Invalidate:

```text
product:<id>
products:all
product:<id>:not_found
```

### DELETE

Invalidate the affected product and collection cache entries.

## Result

The next read produces a cache miss and rebuilds the cache from PostgreSQL.

## Lesson

The database is updated first.

Redis is then invalidated.

```text
Database
   ↓
Cache invalidation
```

---

# 7. Cache Stampede

## Problem

Suppose:

```text
product:1
```

expires.

Many clients request product 1 at almost the same time.

Without protection:

```text
Request A → DB
Request B → DB
Request C → DB
Request D → DB
```

All requests experience a cache miss and hit PostgreSQL.

This is a cache stampede.

## Solution

Use a Redis lock.

Lock key:

```text
lock:product:1
```

The lock is created using:

```text
SET lock:product:1 1 NX EX 10
```

## New flow

```text
Multiple Requests
       ↓
    Redis MISS
       ↓
   Try Lock
       ↓
 ┌─────┴─────┐
 │           │
Lock       No Lock
Holder       │
 │           ↓
 ↓         Wait / Retry
Database     │
 ↓           │
Redis        │
 ↓           │
 └─────┬─────┘
       ↓
    Response
```

## Lesson

A Redis lock can coordinate concurrent cache rebuilding.

---

# 8. Lock Expiration Problem

## Problem

A lock should not remain forever if the process holding it crashes.

For example:

```text
Request
  ↓
Acquire lock
  ↓
Application crashes
```

If the lock has no expiration:

```text
lock:product:1
```

could remain indefinitely.

## Solution

Give the lock a TTL:

```text
SET lock:product:1 1 NX EX 10
```

The lock automatically expires after the configured period.

## Lesson

Locks should have a safety mechanism against abandoned locks.

---

# 9. Lock Release Consideration

The project releases the lock after the cache-building operation.

Conceptually:

```text
Acquire Lock
     ↓
Database
     ↓
Redis
     ↓
Release Lock
```

A production-grade locking implementation should also ensure that a request only releases the lock that it actually owns.

A simple unconditional:

```text
DEL lock:product:1
```

can become unsafe if the original lock expires and another request acquires a new lock before the original request attempts to delete it.

## Lesson

The project demonstrates the Redis locking concept, while production-grade distributed locking requires stronger ownership handling.

---

# 10. Cache Penetration

## Problem

A client repeatedly requests a product that does not exist.

Example:

```text
GET /products/999/
```

Without protection:

```text
Request 1 → Redis MISS → DB → Not Found
Request 2 → Redis MISS → DB → Not Found
Request 3 → Redis MISS → DB → Not Found
```

The same nonexistent record repeatedly reaches PostgreSQL.

## Solution

Use negative caching.

Store:

```text
product:999:not_found
```

with:

```text
NOT_FOUND
```

and a short TTL.

The project uses:

```text
30 seconds
```

## New flow

```text
First Request
     ↓
Redis MISS
     ↓
PostgreSQL
     ↓
Not Found
     ↓
Negative Cache
     ↓
404
```

Next request:

```text
Request
   ↓
Negative Cache HIT
   ↓
404
```

## Lesson

Negative caching prevents repeated database queries for known nonexistent resources.

---

# 11. Why Negative Cache Needs Expiration

## Problem

Suppose product `999` does not exist.

A negative cache is created:

```text
product:999:not_found
```

Later the product is created.

If the negative cache remains forever, the application could continue returning:

```text
404 Product not found
```

even though the product now exists.

## Solution

Use a short TTL:

```text
30 seconds
```

After expiration:

```text
Negative cache disappears
        ↓
New request
        ↓
PostgreSQL checked again
```

## Lesson

Negative caching should normally be temporary.

---

# 12. Redis Failure

## Problem

Redis is a cache, but the application should not treat it as the permanent source of truth.

If Redis becomes unavailable, the application may otherwise fail even though PostgreSQL is still available.

## Solution

For the implemented single-product GET path:

```text
Redis failure
     ↓
Catch Redis error
     ↓
Query PostgreSQL
     ↓
Return product
```

This provides a fallback path.

## Lesson

The project's architectural principle is:

```text
PostgreSQL
    ↓
Source of Truth

Redis
    ↓
Performance Layer
```

---

# 13. Redis Recovery

## Problem

After Redis goes down and later comes back, previously cached data may no longer be available.

## Solution

Allow the normal cache-aside process to rebuild the cache.

```text
Redis restarted
      ↓
Request
      ↓
Cache MISS
      ↓
PostgreSQL
      ↓
Redis SET
      ↓
Response
```

The next request can then become a cache HIT.

## Lesson

Cache data is disposable.

The application should be able to rebuild it from the source of truth.

---

# 14. TTL Confusion

## Problem

It can be confusing to understand what different TTL values mean.

The project verified:

```text
TTL > 0
```

means:

```text
Key exists and has expiration.
```

```text
TTL -1
```

means:

```text
Key exists but has no expiration.
```

```text
TTL -2
```

means:

```text
Key does not exist.
```

## Lesson

TTL is not simply a timer value.

It also provides information about the current state of the key.

---

# 15. TTL vs Cache Invalidation

## Problem

TTL and invalidation can appear to solve the same problem, but they serve different purposes.

### TTL

Handles time-based expiration:

```text
Cache
  ↓
Time passes
  ↓
Expires
```

### Invalidation

Handles data changes:

```text
Database changes
  ↓
Cache becomes stale
  ↓
Delete cache
```

## Project Strategy

The project uses both:

```text
TTL
+
Explicit Invalidation
```

This provides two mechanisms for preventing stale cache data.

---

# 16. Key Naming Problem

## Problem

Redis can contain many keys.

Without a consistent naming system, it becomes difficult to understand what a key represents.

## Solution

The project uses structured key names.

Examples:

```text
products:all
product:1
product:1:views
product:999:not_found
lock:product:1
```

The general patterns are:

```text
<resource>:<id>

<resource>:<id>:<purpose>

lock:<resource>:<id>
```

## Lesson

A predictable key naming strategy makes Redis easier to inspect and maintain.

---

# 17. Unrelated Keys During Learning

## Problem

During manual Redis command practice, additional test keys were created.

Examples included:

```text
test_key
product:test
product:10:category
product:11:category
product:11:name
```

These were created while learning and testing Redis commands.

## Solution

Use `SCAN` to inspect the current Redis keyspace.

Example:

```text
SCAN 0
```

or:

```text
SCAN 0 MATCH product:*
```

## Lesson

During learning, temporary keys are normal, but real applications should maintain clear key organization.

---

# 18. `KEYS` vs `SCAN`

## Problem

A developer may want to quickly find Redis keys.

A simple approach is:

```text
KEYS *
```

However, scanning the entire keyspace with `KEYS` can be expensive on large Redis instances because it performs a broad operation.

## Solution

Use:

```text
SCAN
```

with patterns when inspecting keys.

Example:

```text
SCAN 0 MATCH product:*
```

## Lesson

`SCAN` is the safer approach for incremental keyspace inspection in larger environments.

---

# 19. Memory Limit Problem

## Problem

Redis stores data in memory.

Memory is finite.

If the Redis instance reaches its configured memory limit, Redis needs a defined policy for handling new writes.

## Project Configuration

The project observed:

```text
maxmemory: 8 GB
```

and:

```text
maxmemory-policy: noeviction
```

## Solution / Concept

Redis provides different eviction policies, including:

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

## Lesson

Redis memory configuration and eviction policy are important parts of production cache design.

---

# 20. Cache Data Type Mismatch

## Problem

Different Redis data structures require different commands.

For example:

```text
products:all
```

is treated as a cached collection value.

Whereas:

```text
product:1
```

is a Hash.

Therefore commands must match the stored data type.

For example:

```text
HGETALL product:1
```

is appropriate for a Hash.

## Lesson

Before running a Redis command, understand what data type the key contains.

---

# 21. Source of Truth Confusion

## Problem

A common mistake when learning caching is to think:

```text
Redis = Main Database
```

That is not the architecture of this project.

## Correct Architecture

```text
PostgreSQL
    ↓
Permanent application data

Redis
    ↓
Temporary cached representation
```

If Redis data disappears:

```text
PostgreSQL
    ↓
Rebuild Redis
```

## Lesson

Cache data should be treated as replaceable.

---

# 22. Development Environment Problem

The project uses Redis-compatible Memurai on Windows.

Therefore the Redis commands were executed through:

```text
memurai-cli
```

rather than relying on a Linux Redis installation.

The Redis command model remains the same for the commands used in the project.

---

# 23. API Testing vs Redis Testing

## Problem

An API returning `200 OK` does not necessarily prove that the Redis implementation is working correctly.

For example:

```text
GET /products/1/
```

could return the correct product even if PostgreSQL was queried every time.

## Solution

Testing was performed at two levels.

### API level

Check:

```text
Response
Status code
JSON data
```

### Redis level

Check:

```text
Key exists?
TTL?
Cached value?
Counter?
Lock?
Negative cache?
```

## Lesson

Redis projects should test both the **external API behavior** and the **internal cache behavior**.

---

# 24. Main Problems and Solutions Summary

| Problem | Solution |
|---|---|
| Redis unavailable | PostgreSQL fallback for implemented GET path |
| Cache MISS | Query PostgreSQL and populate Redis |
| Stale cache | Explicit invalidation |
| Cache expiration | TTL |
| Cache stampede | Redis lock |
| Abandoned lock | Lock TTL |
| Cache penetration | Negative caching |
| Permanent negative result | Negative-cache TTL |
| Difficult key inspection | `SCAN` |
| Unclear key purpose | Structured key naming |
| Redis memory limit | Eviction policies |
| API works but cache uncertain | Inspect Redis directly |
| Redis restart | Rebuild cache from PostgreSQL |

---

# 25. What These Problems Taught

Each problem introduced a specific Redis concept:

```text
Problem
   ↓
Why does it happen?
   ↓
Redis feature
   ↓
Implementation
   ↓
Testing
```

The project therefore connected Redis features to real backend problems instead of learning them as isolated commands.

The major mappings are:

```text
Cache Miss
    → Cache-Aside

Stale Data
    → Cache Invalidation + TTL

Cache Stampede
    → Redis Lock

Cache Penetration
    → Negative Cache

Redis Failure
    → Database Fallback

Large Keyspace
    → SCAN

Memory Limit
    → Eviction Policy
```

---

# 26. Final Problem-Solving Model

The overall problem-solving approach used in the project was:

```text
Application Problem
        ↓
Understand Why It Happens
        ↓
Identify Redis Feature
        ↓
Practice Redis Command
        ↓
Implement in Django
        ↓
Test Through API
        ↓
Inspect Redis
        ↓
Verify Final Flow
```

This approach is the main learning outcome of the project.

The goal was not simply to add Redis to Django.

The goal was to understand:

```text
WHY Redis is needed
        ↓
WHEN Redis should be used
        ↓
HOW Redis behaves
        ↓
HOW Django interacts with Redis
        ↓
HOW the system behaves when Redis fails
```

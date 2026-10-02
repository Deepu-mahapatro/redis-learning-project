# Redis Learning Project — Redis Concepts

## 1. Redis Fundamentals

Redis is an **in-memory data store**. It keeps frequently accessed data in memory, allowing applications to access that data much faster than repeatedly reading it from a database.

In this project, Redis is used primarily as a **cache and performance layer**, while PostgreSQL remains the source of truth.

```text id="w1m4be"
PostgreSQL
    ↓
Persistent application data

Redis
    ↓
Fast temporary/cache data
```

---

## 2. Redis Key-Value Model

The basic Redis model is:

```text id="d8f34g"
KEY → VALUE
```

Example:

```text id="g3c8qk"
SET product:test "Laptop"
```

Retrieve it:

```text id="7z1p5v"
GET product:test
```

Result:

```text id="xj2b1k"
" Laptop "
```

The key identifies the stored value.

Redis keys in this project follow a structured naming convention.

---

# 3. Basic Redis Commands

The fundamental commands practiced in the project are:

### `SET`

Stores a value.

```text
SET key value
```

Example:

```text
SET product:test "Laptop"
```

### `GET`

Retrieves a value.

```text
GET product:test
```

### `EXISTS`

Checks whether a key exists.

```text
EXISTS product:test
```

Possible results:

```text
(integer) 1
```

or:

```text
(integer) 0
```

### `DEL`

Deletes a key.

```text
DEL product:test
```

These commands formed the foundation for understanding Redis storage and cache behavior.

---

# 4. Redis Expiration and TTL

Redis can automatically expire keys.

The main commands studied were:

```text
EXPIRE
TTL
PERSIST
```

### `EXPIRE`

Sets an expiration time in seconds.

```text
SET cache:test "hello"
EXPIRE cache:test 60
```

The key will expire after approximately 60 seconds.

### `TTL`

Checks the remaining lifetime.

```text
TTL cache:test
```

### `PERSIST`

Removes the expiration from a key.

```text
PERSIST cache:test
```

---

## 5. Understanding TTL Results

Three important TTL results were practiced:

```text
TTL > 0
```

The key exists and has that many seconds remaining.

```text
TTL -1
```

The key exists but has **no expiration**.

```text
TTL -2
```

The key does **not exist**.

This distinction was important when debugging cache behavior.

---

# 6. Redis Hashes

A Redis Hash stores multiple fields under a single Redis key.

Instead of:

```text
product:1:name
product:1:price
product:1:stock
```

we can use:

```text
product:1
```

with fields:

```text
product:1
├── id
├── name
├── price
└── stock
```

This was used for caching individual Product objects.

### Hash commands studied

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

Example:

```text
HSET product:1 name "Laptop"
HSET product:1 price "60000"
```

Read the complete hash:

```text
HGETALL product:1
```

---

# 7. Redis Counters

Redis can efficiently maintain numeric counters.

The project practiced:

```text
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT
```

The Product API uses a view counter:

```text
product:1:views
```

Conceptually:

```text
GET /products/1/
       ↓
INCR product:1:views
       ↓
Counter increases
```

The counter is separate from the product cache.

---

# 8. Redis Locks

A Redis lock allows multiple requests to coordinate access to a shared operation.

The project used:

```text
SET lock:product:1 1 NX
```

`NX` means the key should only be created if it does not already exist.

A lock can also have an expiration:

```text
SET lock:product:1 1 NX EX 10
```

This creates a lock with a 10-second expiration.

Conceptually:

```text
Request A
   ↓
Gets lock
   ↓
Rebuilds cache

Request B
   ↓
Lock already exists
   ↓
Waits / retries
```

The lock was introduced to protect the application from cache stampede during cache rebuilding.

---

# 9. Negative Caching

Negative caching means temporarily caching the fact that requested data does not exist.

For example:

```text
product:999:not_found
```

can contain:

```text
NOT_FOUND
```

with a short TTL.

Example:

```text
SET product:999:not_found NOT_FOUND EX 30
```

Then repeated requests for the nonexistent product can be answered from Redis instead of repeatedly querying PostgreSQL.

```text
First request
    ↓
Redis MISS
    ↓
PostgreSQL → Not Found
    ↓
Store NOT_FOUND
    ↓
404

Next request
    ↓
Negative Cache HIT
    ↓
404
```

---

# 10. Redis Failure and Fallback

Redis is not the authoritative database in this project.

The architecture is:

```text
PostgreSQL
    ↓
Source of Truth

Redis
    ↓
Cache / Performance Layer
```

Therefore, if Redis becomes unavailable, the application can use PostgreSQL for the implemented fallback read path.

The tested failure produced a connection error similar to:

```text
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine
actively refused it.
```

The implemented fallback allowed the single-product read path to retrieve the product from PostgreSQL.

---

# 11. Redis Key Naming

Redis keys were organized using structured names.

The main patterns are:

```text
<resource>:<id>
<resource>:<id>:<purpose>
```

Examples from the project:

```text
products:all
product:1
product:1:views
product:999:not_found
lock:product:1
```

The naming structure makes it easier to understand what each key represents.

---

# 12. SCAN and Key Management

Redis provides `SCAN` for iterating through keys.

Basic command:

```text
SCAN 0
```

The result contains:

```text
1) cursor
2) keys
```

The returned cursor is used to continue scanning.

Example:

```text
SCAN 0
```

```text
SCAN <returned-cursor>
```

The scan is complete when the cursor returns to:

```text
0
```

---

## `MATCH`

Keys can be filtered using a pattern.

Example:

```text
SCAN 0 MATCH product:*
```

This searches for keys beginning with:

```text
product:
```

---

## `COUNT`

A rough iteration size can be requested:

```text
SCAN 0 MATCH product:* COUNT 10
```

`COUNT` is a hint rather than an exact number of returned keys.

---

# 13. Redis Memory

Redis stores data in memory, so available memory is an important consideration.

The project examined Redis memory using:

```text
INFO memory
```

The actual environment showed:

```text
used_memory_human:828.39K
maxmemory_human:8.00G
maxmemory_policy:noeviction
```

This demonstrated that the running Redis instance was using significantly less memory than its configured maximum.

---

# 14. `maxmemory`

`maxmemory` defines the configured memory limit for Redis.

The project inspected it using:

```text
CONFIG GET maxmemory
```

The configured value was:

```text
8589934592 bytes
```

which corresponds to approximately:

```text
8 GB
```

The setting controls the memory boundary at which Redis's configured eviction behavior becomes relevant.

---

# 15. Eviction

Eviction is different from normal TTL expiration.

### TTL

```text
Remove this key because its lifetime has expired.
```

### Eviction

```text
Memory is under pressure.
Redis needs to decide which keys can be removed
according to the configured policy.
```

The project inspected the policy using:

```text
CONFIG GET maxmemory-policy
```

The original project configuration was:

```text
noeviction
```

---

# 16. Eviction Policies

The main policies studied were:

| Policy | Meaning |
|---|---|
| `noeviction` | Do not automatically evict keys |
| `allkeys-lru` | Evict least recently used keys |
| `volatile-lru` | LRU among keys with TTL |
| `allkeys-lfu` | Evict least frequently used keys |
| `volatile-lfu` | LFU among keys with TTL |
| `allkeys-random` | Randomly evict from all keys |
| `volatile-random` | Randomly evict from TTL keys |
| `volatile-ttl` | Prefer keys with shorter remaining TTL |

### Important terminology

**LRU — Least Recently Used**

```text
Which key has not been used recently?
```

**LFU — Least Frequently Used**

```text
Which key has been accessed the least?
```

**allkeys**

```text
All keys can be considered.
```

**volatile**

```text
Only keys with an expiration can be considered.
```

---

# 17. TTL vs Eviction

These concepts were intentionally distinguished during the project.

```text
TTL
 ↓
Time-based expiration
```

```text
Eviction
 ↓
Memory-pressure-based removal
```

For example:

```text
product:1
TTL = 60 seconds
```

means the key is designed to expire based on time.

An eviction policy becomes relevant when Redis reaches its configured memory boundary.

---

# 18. Important Redis Concepts in This Project

The major concepts can be grouped as follows:

```text
Redis Fundamentals
├── Key-Value Storage
├── SET / GET
├── EXISTS / DEL
└── TTL / Expiration

Data Structures
├── Hashes
└── Counters

Caching
├── Cache HIT
├── Cache MISS
├── Cache-Aside
└── Cache Invalidation

Reliability
├── Cache Stampede Protection
├── Redis Locks
├── Cache Penetration
├── Negative Caching
└── Redis Failure / Fallback

Key Management
├── Key Naming
├── SCAN
├── MATCH
└── COUNT

Memory
├── maxmemory
├── maxmemory-policy
└── Eviction
```

---

# 19. Concept-to-Project Mapping

| Redis Concept | Project Usage |
|---|---|
| Key-Value | Basic Redis operations |
| TTL | Cache expiration |
| Hash | Individual product cache |
| Counter | Product views |
| Lock | Cache rebuild protection |
| Negative Cache | Nonexistent products |
| Key Naming | Structured Redis keyspace |
| SCAN | Key inspection |
| Memory | Redis resource management |
| Eviction | Memory-pressure behavior |

The detailed implementation of these concepts, including their complete request flows and API-specific behavior, is documented in the following sections of the project documentation.

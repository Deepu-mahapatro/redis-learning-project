# Redis Learning Project — Request Flows

## 1. What This Document Contains

This document explains how requests travel through the Redis Learning Project.

The main goal is to understand the **actual flow**, not just individual Redis commands.

The project follows:

```text id="8n5w3d"
Client / Postman
       ↓
     Django
       ↓
     Redis
       ↓
 PostgreSQL
```

Redis is used as a performance layer, while PostgreSQL remains the source of truth.

---

# 2. Overall Request Architecture

The general architecture is:

```text id="xw6yup"
                    Client
                      │
                      ▼
                   Django
                      │
             ┌────────┴────────┐
             │                 │
             ▼                 ▼
           Redis          PostgreSQL
           Cache          Source of Truth
             │                 │
             └────────┬────────┘
                      │
                      ▼
                   Response
```

For most read operations, Redis is checked first.

For write operations, PostgreSQL is updated first and the affected cache is invalidated.

---

# 3. GET All Products — Cache HIT

Endpoint:

```text id="e8y6i1"
GET /products/
```

Suppose Redis already contains:

```text id="t9x6kg"
products:all
```

## Flow

```text id="qwmfnb"
Client
  │
  │ GET /products/
  ▼
Django
  │
  │ Check products:all
  ▼
Redis
  │
  │ HIT
  ▼
Cached Product List
  │
  ▼
Django
  │
  ▼
JSON Response
```

### Important point

PostgreSQL does not need to be queried for the normal cache-hit path.

---

# 4. GET All Products — Cache MISS

Suppose:

```text id="39p0xh"
products:all
```

does not exist in Redis.

## Flow

```text id="7kjd6b"
Client
  │
  │ GET /products/
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
  │ Query products
  ▼
Django
  │
  ├──────────────► Redis
  │                SET products:all
  │
  ▼
JSON Response
```

The database supplies the data and Redis becomes populated for subsequent requests.

---

# 5. GET Single Product — Cache HIT

Endpoint:

```text id="avk7qk"
GET /products/1/
```

Redis key:

```text id="4h7t9n"
product:1
```

This key is a Redis Hash.

## Flow

```text id="6w8znp"
Client
  │
  │ GET /products/1/
  ▼
Django
  │
  │ HGETALL product:1
  ▼
Redis
  │
  │ HIT
  ▼
Product Hash
  │
  ▼
Django
  │
  ▼
JSON Response
```

The product is returned from Redis.

---

# 6. GET Single Product — Cache MISS

Suppose:

```text id="8k6xk5"
product:1
```

does not exist.

The application needs to rebuild the cache.

## Flow

```text id="d0k8oz"
Client
   ↓
Django
   ↓
Redis
   ↓
MISS
   ↓
Acquire Lock
   ↓
Check Redis Again
   ↓
PostgreSQL
   ↓
Product Found
   ↓
Store Product in Redis
   ↓
Release Lock
   ↓
Response
```

The second Redis check after obtaining the lock is important.

Another request may have populated the cache before the current request acquired the lock.

---

# 7. Why the Lock Is Needed

Imagine a product cache expires.

At almost the same time:

```text id="3l7v2s"
Request A
Request B
Request C
Request D
```

all request the same product.

Without protection:

```text id="f2tq3v"
A ──→ PostgreSQL
B ──→ PostgreSQL
C ──→ PostgreSQL
D ──→ PostgreSQL
```

All requests see the same cache MISS.

This is a **cache stampede**.

---

# 8. Cache Stampede — Protected Flow

The project uses:

```text id="r2u8ct"
lock:product:1
```

The flow becomes:

```text id="6j8g7z"
             Multiple Requests
                    │
                    ▼
                 Redis
                    │
                  MISS
                    │
                    ▼
              Try to acquire
                  lock
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
     Lock Holder        Other Requests
          │                   │
          ▼                   ▼
     PostgreSQL          Wait / Retry
          │                   │
          ▼                   │
      Redis SET              │
          │                   │
          └─────────┬─────────┘
                    ▼
                 Response
```

Only the lock holder performs the cache rebuild.

---

# 9. Redis Lock Flow

The lock is created using the equivalent Redis operation:

```text id="h5v8n0"
SET lock:product:1 1 NX EX 10
```

Meaning:

```text id="fr2j4s"
NX
→ Create only if the lock does not already exist.

EX 10
→ Automatically expire the lock after 10 seconds.
```

## Lock lifecycle

```text id="y4t6o1"
Lock does not exist
       ↓
Request acquires lock
       ↓
Lock exists
       ↓
Database query
       ↓
Cache rebuild
       ↓
Lock released
```

The expiration provides protection against a lock remaining indefinitely if something goes wrong.

---

# 10. Second Cache Check

After acquiring the lock, the application checks Redis again.

Why?

Because another request may have populated the cache between:

```text id="4axk6q"
Initial MISS
```

and:

```text id="2g0w0v"
Lock acquisition
```

Therefore:

```text id="oj8y0q"
Initial Redis check
      ↓
MISS
      ↓
Acquire lock
      ↓
Check Redis AGAIN
      ↓
 ┌──────────────┐
 │              │
HIT            MISS
 │              │
 ↓              ↓
Return      Query DB
```

This avoids unnecessary database work.

---

# 11. Non-Existing Product — First Request

Example:

```text id="3t4v1b"
GET /products/999/
```

Suppose product `999` does not exist.

Flow:

```text id="7h3r5w"
Request
   ↓
Django
   ↓
Redis product:999
   ↓
MISS
   ↓
Check negative cache
   ↓
MISS
   ↓
PostgreSQL
   ↓
Product does not exist
   ↓
Store negative cache
   ↓
404 Response
```

Negative-cache key:

```text id="1b6t9x"
product:999:not_found
```

Value:

```text id="s4j7p2"
NOT_FOUND
```

TTL:

```text id="9s0l4z"
30 seconds
```

---

# 12. Negative Cache — Second Request

The same request arrives again:

```text id="o9q2fj"
GET /products/999/
```

Now Redis contains:

```text id="7yn3zv"
product:999:not_found
```

## Flow

```text id="e6m3d0"
Request
   ↓
Django
   ↓
Check negative cache
   ↓
NEGATIVE CACHE HIT
   ↓
404 Response
```

PostgreSQL does not need to be queried again during the negative-cache period.

---

# 13. Why Negative Cache Has a TTL

A product that does not exist now might be created later.

For example:

```text id="y3u5g7"
10:00
Product 999 does not exist
```

Negative cache is stored.

Later:

```text id="0r8f2d"
10:01
Product 999 is created
```

If the negative cache remained forever, Redis could incorrectly say:

```text id="7e6b0f"
Product does not exist
```

Therefore the project uses:

```text id="7j3k4z"
product:999:not_found
TTL = 30 seconds
```

After expiration, the application can check PostgreSQL again.

---

# 14. POST — Create Product

Endpoint:

```text id="5t8j3q"
POST /products/
```

Example:

```json id="a8e6x4"
{
    "name": "Monitor",
    "price": 12000,
    "stock": 15
}
```

## Flow

```text id="v3n9a7"
Client
   ↓
Django
   ↓
Create Product
   ↓
PostgreSQL
   ↓
Product Created
   ↓
Delete products:all
   ↓
Response
```

Why delete the list cache?

Because the cached list no longer represents the database.

---

# 15. POST Cache Invalidation

Before POST:

```text id="e1k3d8"
products:all
    ↓
Laptop
Keyboard
Mouse
```

After creating:

```text id="9j4t6s"
Monitor
```

the previous cached list is stale.

Therefore:

```text id="m8g5w2"
DEL products:all
```

Next request:

```text id="q6r8y1"
GET /products/
```

causes:

```text id="f0x5z9"
Cache MISS
   ↓
PostgreSQL
   ↓
New list
   ↓
Redis
```

---

# 16. PUT — Update Product

Endpoint:

```text id="z5s2k1"
PUT /products/1/
```

Example:

```text id="u1r6x3"
Price: 55000 → 60000
```

## Flow

```text id="q8y4t0"
Client
   ↓
Django
   ↓
Update PostgreSQL
   ↓
Invalidate product cache
   ↓
Invalidate list cache
   ↓
Clear related negative cache
   ↓
Response
```

Relevant keys:

```text id="h3j9p5"
product:1
products:all
product:1:not_found
```

---

# 17. Why PUT Invalidates Multiple Keys

The product appears in two different cached representations.

Individual product:

```text id="n2w7k4"
product:1
```

Product collection:

```text id="r6p1x8"
products:all
```

If the database changes but these caches remain unchanged, they may contain stale information.

Therefore both are invalidated.

---

# 18. DELETE — Delete Product

Endpoint:

```text id="s6c3v9"
DELETE /products/4/
```

## Flow

```text id="m4n8q2"
Client
   ↓
Django
   ↓
Delete Product
   ↓
PostgreSQL
   ↓
Invalidate Product Cache
   ↓
Invalidate List Cache
   ↓
Clear Related Negative Cache
   ↓
Response
```

The goal is to prevent deleted data from remaining available through Redis.

---

# 19. Cache Invalidation Lifecycle

The general write strategy is:

```text id="x7p3b5"
Database Changes
       ↓
Affected Cache Becomes Stale
       ↓
Delete Cache
       ↓
Next Read
       ↓
Cache MISS
       ↓
Read Fresh Database Data
       ↓
Rebuild Cache
```

This is the main cache invalidation pattern used in the project.

---

# 20. Redis Failure Flow

Redis is not the source of truth.

Suppose Memurai stops running.

A request arrives:

```text id="w5q1k7"
GET /products/1/
```

Flow:

```text id="n8c2v4"
Client
   ↓
Django
   ↓
Redis operation
   ↓
Connection Error
   ↓
Fallback
   ↓
PostgreSQL
   ↓
Product returned
```

The observed connection error was:

```text id="3d7m9p"
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

The API could still retrieve the product through PostgreSQL for the implemented fallback path.

---

# 21. Redis Recovery Flow

After Memurai is restarted:

```text id="z4y8m1"
memurai-cli ping
```

returns:

```text id="q2w6e9"
PONG
```

The system can use Redis again.

The next product request may rebuild the missing cache:

```text id="s8k3r5"
Request
   ↓
Redis available
   ↓
Cache MISS
   ↓
PostgreSQL
   ↓
Redis SET
   ↓
Response
```

A later request can then produce:

```text id="j5n1x7"
Request
   ↓
Redis
   ↓
Cache HIT
   ↓
Response
```

---

# 22. Complete Single-Product Lifecycle

The complete lifecycle combines several Redis concepts:

```text id="v9c2m6"
                GET /products/1/
                       │
                       ▼
                  Check Redis
                       │
              ┌────────┴────────┐
              │                 │
             HIT               MISS
              │                 │
              ▼                 ▼
          Response          Check negative
                                │
                         ┌──────┴──────┐
                         │             │
                        HIT           MISS
                         │             │
                         ▼             ▼
                       404        Acquire lock
                                      │
                                      ▼
                               Check Redis again
                                      │
                               ┌──────┴──────┐
                               │             │
                              HIT           MISS
                               │             │
                               ▼             ▼
                           Response      PostgreSQL
                                             │
                                             ▼
                                         Redis SET
                                             │
                                             ▼
                                         Response
```

This is one of the most important flows in the entire project.

---

# 23. Complete Write Lifecycle

For POST, PUT, and DELETE:

```text id="g8m4p1"
Client
  ↓
Django
  ↓
PostgreSQL
  ↓
Database changed
  ↓
Invalidate affected Redis keys
  ↓
Response
```

The next read:

```text id="k2r7v5"
GET
 ↓
Redis MISS
 ↓
PostgreSQL
 ↓
Fresh data
 ↓
Redis
 ↓
Cache rebuilt
```

---

# 24. Redis Key Lifecycle

## Product Cache

```text id="u5c8n2"
product:1
    ↓
Created after cache MISS
    ↓
Used for subsequent reads
    ↓
TTL expires OR cache is invalidated
    ↓
Key disappears
    ↓
Next request rebuilds it
```

---

## List Cache

```text id="p3y6t9"
products:all
    ↓
Created after list cache MISS
    ↓
Used for GET /products/
    ↓
TTL expires OR write invalidates it
    ↓
Next GET rebuilds it
```

---

## Negative Cache

```text id="r7m2x5"
product:999:not_found
    ↓
Product does not exist
    ↓
Negative cache stored
    ↓
30-second TTL
    ↓
Expires
    ↓
Future request checks PostgreSQL again
```

---

## Lock

```text id="c4k8n1"
lock:product:1
    ↓
Cache rebuild begins
    ↓
Lock acquired
    ↓
Database queried
    ↓
Cache rebuilt
    ↓
Lock released
```

The lock also has an expiration as protection against an abandoned lock.

---

# 25. Complete Project Flow

The entire Redis Learning Project can be summarized as:

```text id="q7x3m8"
                    CLIENT
                      │
                      ▼
                  DJANGO API
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
        REDIS                 POSTGRESQL
       CACHE                  SOURCE OF
          │                     TRUTH
          │                       │
          └───────────┬───────────┘
                      │
                      ▼
                   RESPONSE
```

### Read

```text id="n5c9r2"
Request
  ↓
Redis
  ↓
HIT → Response

MISS
  ↓
PostgreSQL
  ↓
Redis
  ↓
Response
```

### Write

```text id="x8m4k6"
POST / PUT / DELETE
       ↓
PostgreSQL
       ↓
Invalidate Cache
       ↓
Response
```

### Stampede

```text id="b3v7q1"
Multiple MISS
     ↓
Redis Lock
     ↓
One request rebuilds cache
     ↓
Other requests reuse result
```

### Penetration

```text id="f6y2p9"
Non-existing ID
      ↓
Negative Cache
      ↓
Repeated request
      ↓
Redis negative-cache HIT
      ↓
404
```

### Redis Failure

```text id="d1k5s8"
Redis unavailable
      ↓
Fallback
      ↓
PostgreSQL
      ↓
Response
```

---

# 26. Final Mental Model

The most important mental model from this project is:

```text id="m9r4x2"
              READ
               │
               ▼
             REDIS
            /     \
          HIT     MISS
          │         │
          │         ▼
          │      DATABASE
          │         │
          │         ▼
          │       REDIS
          │         │
          └────┬────┘
               ▼
            RESPONSE
```

For writes:

```text id="v2n7c5"
            WRITE
              │
              ▼
          DATABASE
              │
              ▼
      CACHE INVALIDATION
              │
              ▼
          RESPONSE
```

Therefore:

```text id="k6p3w8"
PostgreSQL = Source of Truth

Redis = Fast Supporting Layer

Django = Logic / Coordination Layer

Client = API Consumer
```

Understanding these flows is more important than memorizing individual Redis commands because the flows explain **why each Redis feature exists and when it should be used**.

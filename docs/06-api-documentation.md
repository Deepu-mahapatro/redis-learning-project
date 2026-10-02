# Redis Learning Project — API Documentation

## 1. What This Document Contains

This document describes the REST-style Product APIs implemented using Django.

It covers:

- Available endpoints
- HTTP methods
- Request and response formats
- PostgreSQL and Redis involvement
- Cache HIT/MISS behavior
- Cache invalidation
- Error responses
- Status codes
- Postman testing
- Request flow

The project uses normal Django views with `JsonResponse`.

**Django REST Framework (DRF) is not used.**

---

# 2. API Architecture

The client communicates with Django through HTTP.

```text
Client / Postman
       ↓
     Django
       ↓
 ┌─────┴─────┐
 ↓           ↓
Redis     PostgreSQL
Cache     Source of Truth
```

Redis is used to improve read performance and reduce unnecessary database queries.

PostgreSQL remains the source of truth.

---

# 3. Base API URL

During local development:

```text
http://127.0.0.1:8000/products/
```

The API endpoints are:

```text
GET     /products/
GET     /products/<id>/
POST    /products/
PUT     /products/<id>/
DELETE  /products/<id>/
```

---

# 4. Product Model

The Product model contains:

```text
id
name
price
stock
```

Example product:

```json
{
    "id": 1,
    "name": "Laptop",
    "price": 60000.0,
    "stock": 10
}
```

---

# 5. GET All Products

## Endpoint

```text
GET /products/
```

## Purpose

Retrieves all products.

---

## Request

No request body is required.

Example:

```text
GET http://127.0.0.1:8000/products/
```

---

## Redis Flow

The API uses the collection cache:

```text
products:all
```

The flow is:

```text
Request
   ↓
Django
   ↓
Redis GET products:all
   ↓
 ┌───────────────┐
 │               │
HIT             MISS
 │               │
 ↓               ↓
Return       PostgreSQL
cached          ↓
data         Redis SET
                ↓
             Response
```

---

## Cache HIT

If `products:all` exists:

```text
Redis
  ↓
Cached products
  ↓
Django
  ↓
JSON response
```

The database does not need to be queried for the list.

---

## Cache MISS

If `products:all` does not exist:

```text
Redis MISS
    ↓
PostgreSQL query
    ↓
Products retrieved
    ↓
Redis cache populated
    ↓
Response returned
```

---

## Example Response

```json
[
    {
        "id": 1,
        "name": "Laptop",
        "price": 60000.0,
        "stock": 10
    },
    {
        "id": 2,
        "name": "Mechanical Keyboard",
        "price": 2500.0,
        "stock": 15
    }
]
```

---

# 6. GET Single Product

## Endpoint

```text
GET /products/<id>/
```

Example:

```text
GET /products/1/
```

---

## Purpose

Retrieves one product.

This endpoint demonstrates several Redis concepts together:

- Redis Hash
- Cache HIT/MISS
- TTL
- Cache stampede protection
- Redis locking
- Negative caching
- Redis failure fallback

---

# 7. Single Product Cache

The Redis key follows:

```text
product:<id>
```

For product 1:

```text
product:1
```

The product is stored as a Redis Hash.

Example:

```text
product:1
├── id
├── name
├── price
└── stock
```

---

# 8. Single Product — Cache HIT

Request:

```text
GET /products/1/
```

If:

```text
product:1
```

exists in Redis:

```text
Request
   ↓
Django
   ↓
Redis HGETALL
   ↓
Cache HIT
   ↓
Return product
```

PostgreSQL is not required for the normal cache-hit path.

---

# 9. Single Product — Cache MISS

If:

```text
product:1
```

does not exist:

```text
Request
   ↓
Django
   ↓
Redis MISS
   ↓
Acquire Redis lock
   ↓
Check cache again
   ↓
PostgreSQL
   ↓
Store product in Redis
   ↓
Release lock
   ↓
Return response
```

The product cache is given a TTL.

The project uses:

```text
60 seconds
```

for the product cache.

---

# 10. Cache Stampede Protection

If a popular product cache expires, multiple requests could arrive at almost the same time.

Without protection:

```text
Request 1 ──→ PostgreSQL
Request 2 ──→ PostgreSQL
Request 3 ──→ PostgreSQL
Request 4 ──→ PostgreSQL
```

This creates unnecessary database load.

The project uses a Redis lock:

```text
lock:product:<id>
```

Example:

```text
lock:product:1
```

Flow:

```text
Multiple Requests
       ↓
 Redis MISS
       ↓
 ┌───────────────┐
 │ One request   │ → Gets lock
 └───────────────┘
       ↓
 PostgreSQL
       ↓
 Redis
       ↓
 Other requests read cache
```

The lock itself has an expiration to prevent an abandoned lock from remaining forever.

---

# 11. Non-Existing Product

Example:

```text
GET /products/999/
```

If product `999` does not exist in PostgreSQL, the application stores a negative-cache entry.

Key:

```text
product:999:not_found
```

Value:

```text
NOT_FOUND
```

TTL:

```text
30 seconds
```

---

# 12. Negative Cache Flow

First request:

```text
GET /products/999/
```

Flow:

```text
Redis
  ↓
No product cache
  ↓
PostgreSQL
  ↓
Product does not exist
  ↓
Store:
product:999:not_found
  ↓
404 response
```

Second request:

```text
GET /products/999/
```

Flow:

```text
Redis
  ↓
Negative Cache HIT
  ↓
404 response
```

The database does not need to be queried again during the negative-cache period.

---

# 13. Single Product Response

For an existing product:

```json
{
    "id": 1,
    "name": "Laptop",
    "price": 60000.0,
    "stock": 10
}
```

For a missing product:

```json
{
    "error": "Product not found"
}
```

Status:

```text
404 Not Found
```

---

# 14. POST — Create Product

## Endpoint

```text
POST /products/
```

## Purpose

Creates a new product in PostgreSQL.

---

## Request Body

Example:

```json
{
    "name": "Monitor",
    "price": 12000,
    "stock": 15
}
```

---

# 15. POST Flow

The database is updated first.

```text
POST Request
     ↓
Django
     ↓
Validate request
     ↓
Create Product
     ↓
PostgreSQL
     ↓
Invalidate products:all
     ↓
Response
```

The list cache is invalidated because the collection has changed.

---

## Why Invalidate the Cache?

Suppose Redis contains:

```text
products:all
```

with:

```text
Laptop
Keyboard
Mouse
```

A new product is created:

```text
Monitor
```

The old cache is now stale.

Therefore:

```text
DEL products:all
```

The next:

```text
GET /products/
```

will cause a cache MISS and rebuild the list cache.

---

# 16. POST Response

Example:

```json
{
    "id": 4,
    "name": "Monitor",
    "price": 12000.0,
    "stock": 15
}
```

Successful creation normally returns:

```text
201 Created
```

---

# 17. PUT — Update Product

## Endpoint

```text
PUT /products/<id>/
```

Example:

```text
PUT /products/1/
```

---

## Request Body

Example:

```json
{
    "name": "Laptop",
    "price": 60000,
    "stock": 10
}
```

---

# 18. PUT Flow

```text
PUT Request
     ↓
Django
     ↓
Find Product
     ↓
Update PostgreSQL
     ↓
Invalidate product cache
     ↓
Invalidate products:all
     ↓
Response
```

The individual product cache must be removed because the cached version is now stale.

Example:

```text
DEL product:1
```

The list cache is also invalidated:

```text
DEL products:all
```

The negative cache for the product is also cleared:

```text
DEL product:1:not_found
```

This ensures that an old negative-cache entry cannot incorrectly claim that the product does not exist.

---

# 19. PUT Response

Example:

```json
{
    "id": 1,
    "name": "Laptop",
    "price": 60000.0,
    "stock": 10
}
```

Successful update:

```text
200 OK
```

---

# 20. DELETE — Delete Product

## Endpoint

```text
DELETE /products/<id>/
```

Example:

```text
DELETE /products/4/
```

---

# 21. DELETE Flow

```text
DELETE Request
      ↓
Django
      ↓
Delete from PostgreSQL
      ↓
Delete product cache
      ↓
Delete list cache
      ↓
Response
```

Relevant Redis keys may include:

```text
product:4
products:all
product:4:not_found
```

The application invalidates the relevant cache data.

---

# 22. DELETE Response

Example:

```json
{
    "message": "Product deleted successfully"
}
```

Successful deletion:

```text
204 No Content
```

or the project's configured successful response if the view returns a JSON confirmation.

---

# 23. API Status Codes

The project uses HTTP status codes to communicate request results.

| Status | Meaning |
|---|---|
| `200` | Successful request |
| `201` | Product successfully created |
| `204` | Successful deletion with no response body |
| `400` | Invalid request data |
| `404` | Product not found |
| `500` | Unexpected server-side error |

The exact response body should be checked against the current Django view implementation when documenting a specific test.

---

# 24. Redis Failure Scenario

Redis is a performance layer, not the source of truth.

If Redis becomes unavailable, the application can fall back to PostgreSQL for the implemented single-product GET path.

Flow:

```text
Request
   ↓
Django
   ↓
Redis unavailable
   ↓
Redis error
   ↓
PostgreSQL
   ↓
Return product
```

This preserves the ability to retrieve product data even when Redis is unavailable.

The project tested this by stopping Memurai.

The observed Redis connection error was:

```text
Error 10061 connecting to localhost:6379.
No connection could be made because the target machine actively refused it.
```

The product GET still returned successfully through PostgreSQL.

---

# 25. Redis Recovery

After Redis/Memurai was restarted:

```text
memurai-cli ping
```

returned:

```text
PONG
```

The next request could rebuild the cache.

The flow becomes:

```text
Redis restarted
      ↓
Request
      ↓
Cache MISS
      ↓
PostgreSQL
      ↓
Redis cache rebuilt
      ↓
Next request
      ↓
Cache HIT
```

---

# 26. Product View Counter

The project also uses a Redis counter:

```text
product:<id>:views
```

Example:

```text
product:1:views
```

Each view can increment the counter using:

```text
INCR product:1:views
```

This demonstrates how Redis can maintain lightweight counters without storing the counter as part of the cached product object.

---

# 27. Postman Testing

The APIs were tested using Postman.

Typical testing sequence:

```text
1. Start PostgreSQL
2. Start Memurai/Redis
3. Start Django server
4. Open Postman
5. Send API request
6. Observe response
7. Inspect Redis
8. Verify cache behavior
```

Example:

```text
GET http://127.0.0.1:8000/products/
```

Then inspect:

```text
SCAN 0 MATCH products:*
```

or:

```text
GET products:all
```

depending on the stored data type.

---

# 28. Complete API-to-Redis Mapping

| API | PostgreSQL | Redis | Main Redis Concept |
|---|---|---|---|
| `GET /products/` | Read on MISS | `products:all` | Cache-Aside |
| `GET /products/<id>/` | Read on MISS/fallback | `product:<id>` | Hash + Cache |
| `POST /products/` | Create | Invalidate `products:all` | Cache Invalidation |
| `PUT /products/<id>/` | Update | Invalidate product/list caches | Cache Invalidation |
| `DELETE /products/<id>/` | Delete | Invalidate product/list caches | Cache Invalidation |

Additional Redis features:

```text
product:<id>:views
        ↓
Counter

product:<id>:not_found
        ↓
Negative Cache

lock:product:<id>
        ↓
Cache Stampede Protection
```

---

# 29. Complete Request Lifecycle

The overall project can be understood through this flow:

```text
                    CLIENT / POSTMAN
                           │
                           ▼
                         DJANGO
                           │
             ┌─────────────┴─────────────┐
             │                           │
             ▼                           ▼
           REDIS                    POSTGRESQL
          CACHE                   SOURCE OF TRUTH
             │                           │
             └─────────────┬─────────────┘
                           │
                           ▼
                        RESPONSE
```

For reads:

```text
Request
   ↓
Check Redis
   ↓
 ┌───────────────┐
 │               │
HIT             MISS
 │               │
 ↓               ↓
Response      PostgreSQL
                 ↓
              Redis SET
                 ↓
              Response
```

For writes:

```text
POST / PUT / DELETE
        ↓
   PostgreSQL
        ↓
Cache Invalidation
        ↓
     Response
```

---

# 30. Main API Learning Outcomes

After implementing these APIs, the project demonstrates how Redis interacts with a real backend application.

The important understanding is:

```text
Redis does not replace PostgreSQL.
```

Instead:

```text
PostgreSQL
    =
Source of Truth

Redis
    =
Fast Cache / Supporting Layer
```

The API layer connects both:

```text
Client
  ↓
Django API
  ↓
Redis
  ↓
PostgreSQL when necessary
```

This is the core architecture of the Redis learning project.

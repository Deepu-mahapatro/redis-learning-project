# Redis Learning Project

## 1. Project Overview

This project is a practical Redis learning and implementation project built with **Django and PostgreSQL**.

The main purpose is to understand how Redis works as a **caching and performance layer** in a backend application, rather than using Redis only as a theoretical technology.

The project uses a simple **Product API** to demonstrate Redis concepts through real API requests, Redis CLI commands, PostgreSQL operations, and application-level testing.

---

## 2. Problem Statement

A backend application may repeatedly query PostgreSQL for data that does not change frequently.

For example:

```text
Client
   ↓
Django
   ↓
PostgreSQL
   ↓
Response
```

Repeated database queries can increase database load and response time.

Redis is introduced as a fast in-memory cache:

```text
Client
   ↓
Django
  ↙   ↘
Redis  PostgreSQL
Cache  Source of Truth
```

The project demonstrates how to use Redis while keeping PostgreSQL as the authoritative source of application data.

---

## 3. Project Objectives

The project was designed to understand and implement:

- Redis fundamentals and commands
- Cache-Aside pattern
- Cache HIT and MISS
- Cache invalidation
- Redis Hashes
- Redis counters
- TTL and expiration
- Cache stampede protection
- Redis locks
- Cache penetration
- Negative caching
- Redis failure and PostgreSQL fallback
- Redis key naming
- SCAN and key management
- Memory and eviction concepts
- Practical Redis testing

---

## 4. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Django | API/backend framework |
| PostgreSQL | Primary database / source of truth |
| Redis / Memurai | Cache and Redis operations |
| Postman | API testing |
| Redis CLI | Manual Redis command practice |
| Git | Version control |
| GitHub | Project repository |
| `.env` | Environment configuration |

---

## 5. Project Scope

The project focuses on a small **Product API** rather than a complete e-commerce application.

The main product fields are:

```text
id
name
price
stock
```

The application provides:

```text
GET    /products/
GET    /products/<id>/
POST   /products/
PUT    /products/<id>/
DELETE /products/<id>/
```

Redis is introduced only where it helps demonstrate the concepts being studied.

---

## 6. Redis Features Implemented

The project includes the following practical Redis features:

```text
Cache-Aside
Cache Invalidation
Redis Hashes
Counters
Cache Stampede Protection
Redis Locks
Cache Penetration Protection
Negative Caching
Redis Failure / Fallback
Key Naming Strategy
TTL Strategy
Memory & Eviction
SCAN & Key Management
```

These features were implemented and tested through the Product API and Redis CLI.

---

## 7. Core Architecture

The main application architecture is:

```text
                    Client / Postman
                           │
                           ▼
                     Django API
                      ↙       ↘
                     ↓         ↓
                  Redis    PostgreSQL
                  Cache    Source of Truth
```

### Responsibility of each component

- **Client/Postman** — sends HTTP requests.
- **Django** — processes API requests and controls application logic.
- **Redis** — provides caching, counters, locks, and temporary data.
- **PostgreSQL** — stores the authoritative product data.

---

## 8. Learning Approach

The project follows a practical learning cycle:

```text
Understand Concept
       ↓
Practice Redis Command
       ↓
Inspect Redis
       ↓
Integrate with Django
       ↓
Test API with Postman
       ↓
Inspect Redis Again
       ↓
Understand Request Flow
       ↓
Test Failure / Edge Cases
```

This approach was used to understand not only **what Redis commands do**, but also **where and why they are used inside a real backend application**.

---

## 9. Project Outcome

At the end of the project, Redis was integrated into a Django + PostgreSQL Product API as a practical caching and performance layer.

The project demonstrates how to:

- Reduce repeated database reads using caching.
- Keep cached data synchronized through invalidation.
- Cache individual objects using Redis Hashes.
- Track values using Redis counters.
- Protect cache rebuilding with Redis locks.
- Prevent repeated database queries for nonexistent data.
- Handle Redis unavailability through PostgreSQL fallback for the implemented read path.
- Manage TTLs and Redis keys.
- Understand Redis memory limits and eviction behavior.
- Inspect and manage Redis keys using `SCAN`.

The detailed implementation, commands, API behavior, request flows, testing results, and problems encountered are documented in the remaining files under `docs/`.

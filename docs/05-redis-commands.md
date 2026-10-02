# Redis Learning Project — Redis Commands

## 1. Command Reference Overview

This document contains the Redis commands practiced and used during the project.

The commands are grouped according to their purpose:

```text
Basic Operations
    ↓
Expiration
    ↓
Hashes
    ↓
Counters
    ↓
Locks
    ↓
Key Management
    ↓
Configuration & Memory
```

---

# 2. Basic Redis Commands

## 2.1 `SET`

### Purpose

Stores a value against a Redis key.

### Syntax

```text
SET <key> <value>
```

### Example

```text
SET product:test "Laptop"
```

### Expected output

```text
OK
```

### Read the value

```text
GET product:test
```

Expected:

```text
"Laptop"
```

### Project usage

`SET` is used conceptually when populating cache values and negative-cache values.

---

## 2.2 `GET`

### Purpose

Retrieves the value stored under a key.

### Syntax

```text
GET <key>
```

### Example

```text
GET product:test
```

Expected:

```text
"Laptop"
```

If the key does not exist:

```text
(nil)
```

### Project usage

Used to inspect simple Redis values and negative-cache values.

---

## 2.3 `EXISTS`

### Purpose

Checks whether a Redis key exists.

### Syntax

```text
EXISTS <key>
```

### Example

```text
EXISTS product:1
```

Expected:

```text
(integer) 1
```

Possible result:

```text
(integer) 0
```

means the key does not exist.

### Project usage

Used while checking whether cache keys exist.

---

## 2.4 `DEL`

### Purpose

Deletes a Redis key.

### Syntax

```text
DEL <key>
```

### Example

```text
DEL product:test
```

Expected:

```text
(integer) 1
```

`1` means one key was deleted.

If the key does not exist:

```text
(integer) 0
```

### Project usage

Used for:

- Cache invalidation
- Lock release
- Removing temporary test keys

---

# 3. Expiration Commands

## 3.1 `EXPIRE`

### Purpose

Sets a TTL on an existing key.

### Syntax

```text
EXPIRE <key> <seconds>
```

### Example

```text
SET cache:test "hello"
EXPIRE cache:test 60
```

Expected:

```text
OK
(integer) 1
```

The key is designed to expire after approximately 60 seconds.

### Project usage

Used to apply TTLs to cached data such as product hashes.

---

## 3.2 `TTL`

### Purpose

Checks how many seconds remain before a key expires.

### Syntax

```text
TTL <key>
```

### Example

```text
TTL cache:test
```

Possible result:

```text
(integer) 57
```

The value decreases as time passes.

### Important results

```text
TTL > 0
→ Key exists and has expiration.

TTL -1
→ Key exists but has no expiration.

TTL -2
→ Key does not exist.
```

### Project usage

Used to verify:

- Product cache TTL
- Collection cache TTL
- Negative-cache TTL
- Lock TTL

---

## 3.3 `PERSIST`

### Purpose

Removes the expiration from a key.

### Syntax

```text
PERSIST <key>
```

### Example

```text
PERSIST cache:test
```

Expected:

```text
(integer) 1
```

Afterward:

```text
TTL cache:test
```

returns:

```text
(integer) -1
```

if the key still exists.

---

# 4. Redis Hash Commands

The project uses a Redis Hash for an individual product.

Example:

```text
product:1
```

Conceptually:

```text
product:1
├── id
├── name
├── price
└── stock
```

---

## 4.1 `HSET`

### Purpose

Creates or updates fields inside a Redis Hash.

### Syntax

```text
HSET <key> <field> <value>
```

### Example

```text
HSET product:1 name "Laptop"
```

Expected:

```text
(integer) 1
```

Multiple fields can also be stored:

```text
HSET product:1 id 1 name "Laptop" price 60000 stock 10
```

### Project usage

Used when building the individual product cache.

---

## 4.2 `HGET`

### Purpose

Retrieves one field from a Hash.

### Syntax

```text
HGET <key> <field>
```

### Example

```text
HGET product:1 name
```

Expected:

```text
"Laptop"
```

---

## 4.3 `HGETALL`

### Purpose

Retrieves all fields and values from a Hash.

### Syntax

```text
HGETALL <key>
```

### Example

```text
HGETALL product:1
```

Possible output:

```text
1) "id"
2) "1"
3) "name"
4) "Laptop"
5) "price"
6) "60000"
7) "stock"
8) "10"
```

### Project usage

This is important for:

```text
GET /products/<id>/
```

because the application reads the cached product Hash.

---

## 4.4 `HEXISTS`

### Purpose

Checks whether a field exists inside a Hash.

### Syntax

```text
HEXISTS <key> <field>
```

### Example

```text
HEXISTS product:1 name
```

Expected:

```text
(integer) 1
```

---

## 4.5 `HDEL`

### Purpose

Deletes a field from a Hash.

### Syntax

```text
HDEL <key> <field>
```

### Example

```text
HDEL product:1 stock
```

Expected:

```text
(integer) 1
```

---

## 4.6 `HMGET`

### Purpose

Retrieves multiple fields from a Hash.

### Syntax

```text
HMGET <key> <field1> <field2>
```

### Example

```text
HMGET product:1 name price
```

Possible output:

```text
1) "Laptop"
2) "60000"
```

---

## 4.7 `HINCRBY`

### Purpose

Increases an integer field inside a Hash.

### Syntax

```text
HINCRBY <key> <field> <amount>
```

### Example

```text
HINCRBY product:1 stock 5
```

If stock was `10`:

```text
(integer) 15
```

---

## 4.8 `HINCRBYFLOAT`

### Purpose

Increases a numeric Hash field by a floating-point amount.

### Syntax

```text
HINCRBYFLOAT <key> <field> <amount>
```

### Example

```text
HINCRBYFLOAT product:1 price 500.50
```

---

## 4.9 `HKEYS`

### Purpose

Returns all field names in a Hash.

### Example

```text
HKEYS product:1
```

Possible output:

```text
1) "id"
2) "name"
3) "price"
4) "stock"
```

---

## 4.10 `HVALS`

### Purpose

Returns all values stored in a Hash.

### Example

```text
HVALS product:1
```

Possible output:

```text
1) "1"
2) "Laptop"
3) "60000"
4) "10"
```

---

# 5. Counter Commands

The project uses:

```text
product:1:views
```

as a product view counter.

---

## 5.1 `INCR`

### Purpose

Increases a numeric value by `1`.

### Example

```text
INCR product:1:views
```

Possible output:

```text
(integer) 1
```

Run again:

```text
INCR product:1:views
```

Result:

```text
(integer) 2
```

---

## 5.2 `DECR`

Decreases a numeric value by `1`.

```text
DECR product:1:views
```

---

## 5.3 `INCRBY`

Increases a value by a specified amount.

```text
INCRBY product:1:views 10
```

If the value was `2`:

```text
(integer) 12
```

---

## 5.4 `DECRBY`

Decreases a value by a specified amount.

```text
DECRBY product:1:views 5
```

---

## 5.5 `INCRBYFLOAT`

Increases a numeric value by a floating-point amount.

```text
INCRBYFLOAT price:test 10.5
```

---

# 6. Redis Lock Commands

The project uses Redis locks for cache stampede protection.

## 6.1 `SET ... NX`

### Purpose

Create a key only if it does not already exist.

### Example

```text
SET lock:product:1 1 NX
```

First request:

```text
OK
```

Second request while the lock exists:

```text
(nil)
```

This allows the application to identify the lock holder.

---

## 6.2 `SET ... NX EX`

A safer learning implementation adds expiration:

```text
SET lock:product:1 1 NX EX 10
```

Meaning:

```text
NX
→ Only create if the key doesn't exist.

EX 10
→ Automatically expire the lock after 10 seconds.
```

Check it:

```text
TTL lock:product:1
```

Possible:

```text
(integer) 9
```

---

# 7. Key Management Commands

## 7.1 `SCAN`

### Purpose

Iterates through Redis keys incrementally.

### Syntax

```text
SCAN <cursor>
```

Start:

```text
SCAN 0
```

Example result:

```text
1) "0"
2) 1) "product:1"
   2) "product:2"
```

The first value is the cursor.

When the cursor eventually returns to `0`, the scan is complete.

---

## 7.2 `MATCH`

Filters keys according to a pattern.

Example:

```text
SCAN 0 MATCH product:*
```

This can find keys such as:

```text
product:1
product:1:views
product:2
product:999:not_found
```

---

## 7.3 `COUNT`

Provides a rough requested iteration size.

Example:

```text
SCAN 0 MATCH product:* COUNT 10
```

`COUNT` is a hint, not an exact number of returned keys.

---

# 8. Configuration Commands

## 8.1 `CONFIG GET`

Reads Redis configuration.

Example:

```text
CONFIG GET maxmemory
```

Actual project configuration:

```text
1) "maxmemory"
2) "8589934592"
```

This is approximately:

```text
8 GB
```

Check the eviction policy:

```text
CONFIG GET maxmemory-policy
```

Actual project configuration:

```text
1) "maxmemory-policy"
2) "noeviction"
```

---

## 8.2 `CONFIG SET`

Changes a Redis configuration at runtime.

During the memory/eviction learning experiment, we temporarily changed the configuration.

Example:

```text
CONFIG SET maxmemory 1mb
```

and:

```text
CONFIG SET maxmemory-policy allkeys-lru
```

The purpose was to understand eviction behavior in a controlled environment.

The original project configuration was restored afterward:

```text
CONFIG SET maxmemory 8gb
CONFIG SET maxmemory-policy noeviction
```

---

# 9. Memory Inspection

## `INFO memory`

### Purpose

Displays Redis memory information.

Command:

```text
INFO memory
```

Important values observed in the project included:

```text
used_memory_human:828.39K
maxmemory_human:8.00G
maxmemory_policy:noeviction
```

This was used to understand:

- Current Redis memory usage
- Configured memory limit
- Current eviction policy

---

# 10. Project Redis Keys

The main Redis keys used in the project are:

| Key | Purpose |
|---|---|
| `products:all` | All-products cache |
| `product:<id>` | Individual product Hash |
| `product:<id>:views` | Product view counter |
| `product:<id>:not_found` | Negative cache |
| `lock:product:<id>` | Cache rebuild lock |

Example:

```text
product:1
product:1:views
product:999:not_found
lock:product:1
products:all
```

---

# 11. Command-to-Feature Mapping

| Redis Command | Project Feature |
|---|---|
| `SET` | Basic storage / cache values |
| `GET` | Reading values |
| `EXISTS` | Key existence checks |
| `DEL` | Cache invalidation / lock release |
| `EXPIRE` | TTL |
| `TTL` | TTL inspection |
| `PERSIST` | Remove expiration |
| `HSET` | Product Hash |
| `HGET` | Hash field retrieval |
| `HGETALL` | Product cache retrieval |
| `HEXISTS` | Hash field check |
| `HDEL` | Hash field deletion |
| `HMGET` | Multiple Hash fields |
| `HINCRBY` | Integer Hash increment |
| `HINCRBYFLOAT` | Floating-point increment |
| `HKEYS` | Hash fields |
| `HVALS` | Hash values |
| `INCR` | Product view counter |
| `DECR` | Counter decrement |
| `INCRBY` | Counter increment |
| `DECRBY` | Counter decrement |
| `INCRBYFLOAT` | Floating-point increment |
| `SET NX` | Redis locking |
| `SET NX EX` | Expiring Redis lock |
| `SCAN` | Key inspection |
| `MATCH` | Key filtering |
| `COUNT` | Scan iteration hint |
| `CONFIG GET` | Configuration inspection |
| `CONFIG SET` | Configuration changes |
| `INFO memory` | Memory inspection |

---

# 12. Command Usage Principle

Redis commands were not learned only as isolated commands.

The project followed this learning process:

```text
Redis Command
      ↓
Understand Behavior
      ↓
Practice Manually
      ↓
Inspect Output
      ↓
Connect to Django
      ↓
Use Through API
      ↓
Verify Redis State
```

This approach helped connect individual Redis commands with their actual purpose inside a backend application.

---

# 13. Important Command Groups

For quick revision:

```text
Basic
SET
GET
EXISTS
DEL

Expiration
EXPIRE
TTL
PERSIST

Hashes
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

Counters
INCR
DECR
INCRBY
DECRBY
INCRBYFLOAT

Locks
SET NX
SET NX EX

Key Management
SCAN
MATCH
COUNT

Memory / Configuration
CONFIG GET
CONFIG SET
INFO memory
```

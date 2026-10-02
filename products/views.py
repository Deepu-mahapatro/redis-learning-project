import json
import time

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Product
from config.redis_client import redis_client


@csrf_exempt
def product_list(request, product_id=None):

    # =========================================================
    # GET /products/<id>/
    #
    # Purpose:
    # Retrieve a single product using Redis Hash caching.
    #
    # Cache flow:
    # Redis HIT  → Return product from Redis Hash
    # Redis MISS → Redis Lock → PostgreSQL → Store in Redis Hash
    #
    # Cache Stampede protection:
    # If multiple requests get a CACHE MISS at the same time,
    # only ONE request is allowed to query PostgreSQL.
    #
    # Cache Penetration protection:
    # If a product does not exist, temporarily store NOT_FOUND
    # in Redis so repeated invalid requests do not hit PostgreSQL.
    # =========================================================

    if request.method == "GET" and product_id is not None:

        # -----------------------------------------------------
        # STEP 1: Create Redis keys
        # -----------------------------------------------------

        # Product Hash
        # Example:
        # product_id = 1
        # Redis key  = product:1
        cache_key = f"product:{product_id}"

        # Negative cache
        # Stores information that a product does not exist.
        #
        # Example:
        # product:999:not_found → NOT_FOUND
        negative_cache_key = f"product:{product_id}:not_found"

        # -----------------------------------------------------
        # STEP 2: Check Redis Hash for cached product
        # -----------------------------------------------------

        try:
            # TRY TO READ THE PRODUCT FROM REDIS
            cached_product = redis_client.hgetall(cache_key)

            print("REDIS HASH CHECK:", cached_product)

        except Exception as e:

            # REDIS IS UNAVAILABLE
            print("REDIS ERROR:", e)

            # -------------------------------------------------
            # REDIS FAILURE FALLBACK
            #
            # Redis is unavailable.
            # Therefore, bypass Redis completely and use
            # PostgreSQL as the source of truth.
            # -------------------------------------------------

            try:

                product = Product.objects.get(
                    id=product_id
                )

            except Product.DoesNotExist:

                return JsonResponse(
                    {"error": "Product not found"},
                    status=404
                )

            # Return PostgreSQL data directly.
            #
            # We do NOT try to store the product in Redis
            # because Redis is currently unavailable.

            return JsonResponse({
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock,
            })

        # -----------------------------------------------------
        # STEP 3: CACHE HIT
        #
        # Redis already contains this product.
        # PostgreSQL is not queried.
        # -----------------------------------------------------

        if cached_product:

            view_count = redis_client.incr(
                f"product:{product_id}:views"
            )

            return JsonResponse({
                "id": product_id,
                "name": cached_product["name"],
                "price": float(cached_product["price"]),
                "stock": int(cached_product["stock"]),
                "views": view_count,
            })

        # -----------------------------------------------------
        # STEP 4: CHECK NEGATIVE CACHE
        #
        # Redis may remember that this product does not exist.
        #
        # If found:
        #     Do NOT query PostgreSQL.
        #     Immediately return 404.
        # -----------------------------------------------------

        negative_cache = redis_client.get(
            negative_cache_key
        )

        print("NEGATIVE CACHE CHECK:", negative_cache)

        if negative_cache == "NOT_FOUND":

            print("NEGATIVE CACHE HIT")

            return JsonResponse(
                {"error": "Product not found"},
                status=404
            )

        # -----------------------------------------------------
        # STEP 5: CACHE MISS
        #
        # Product is not in Redis and we don't have a
        # negative-cache entry.
        #
        # Try to acquire a Redis lock so that multiple
        # requests don't query PostgreSQL simultaneously.
        # -----------------------------------------------------

        lock_key = f"lock:product:{product_id}"

        lock_acquired = redis_client.set(
            lock_key,
            "1",
            nx=True,
            ex=10
        )

        print("LOCK ACQUIRED:", lock_acquired)

        # =====================================================
        # STEP 6: REQUEST GOT THE LOCK
        # =====================================================

        if lock_acquired:

            try:

                # -------------------------------------------------
                # Recheck Redis after acquiring the lock.
                #
                # Another request may have populated the cache
                # before this request acquired the lock.
                # -------------------------------------------------

                cached_product = redis_client.hgetall(
                    cache_key
                )

                if cached_product:

                    view_count = redis_client.incr(
                        f"product:{product_id}:views"
                    )

                    return JsonResponse({
                        "id": product_id,
                        "name": cached_product["name"],
                        "price": float(cached_product["price"]),
                        "stock": int(cached_product["stock"]),
                        "views": view_count,
                    })

                # -------------------------------------------------
                # Recheck negative cache after acquiring the lock.
                # -------------------------------------------------

                negative_cache = redis_client.get(
                    negative_cache_key
                )

                if negative_cache == "NOT_FOUND":

                    print("NEGATIVE CACHE FOUND AFTER LOCK")

                    return JsonResponse(
                        {"error": "Product not found"},
                        status=404
                    )

                # -------------------------------------------------
                # Get product from PostgreSQL
                # -------------------------------------------------

                try:

                    product = Product.objects.get(
                        id=product_id
                    )

                except Product.DoesNotExist:

                    # -------------------------------------------------
                    # CACHE PENETRATION PROTECTION
                    #
                    # Product does not exist.
                    #
                    # Store NOT_FOUND in Redis for 30 seconds.
                    #
                    # This is called NEGATIVE CACHING.
                    # -------------------------------------------------

                    redis_client.set(
                        negative_cache_key,
                        "NOT_FOUND",
                        ex=30
                    )

                    print(
                        "NEGATIVE CACHE CREATED:",
                        negative_cache_key
                    )

                    return JsonResponse(
                        {"error": "Product not found"},
                        status=404
                    )

                # -----------------------------------------------------
                # STEP 7: STORE PRODUCT IN REDIS HASH
                # -----------------------------------------------------

                redis_client.hset(
                    cache_key,
                    mapping={
                        "name": product.name,
                        "price": str(product.price),
                        "stock": str(product.stock),
                    }
                )
                
                #Give the product cache a TTL of 60 seconds 
                redis_client.expire(
                    cache_key,60
                )

                # -----------------------------------------------------
                # STEP 8: Increase product view counter
                # -----------------------------------------------------

                view_count = redis_client.incr(
                    f"product:{product_id}:views"
                )

                # -----------------------------------------------------
                # STEP 9: Return product data
                # -----------------------------------------------------

                return JsonResponse({
                    "id": product.id,
                    "name": product.name,
                    "price": float(product.price),
                    "stock": product.stock,
                    "views": view_count,
                })

            finally:

                # -------------------------------------------------
                # RELEASE THE LOCK
                # -------------------------------------------------

                redis_client.delete(lock_key)

        # =====================================================
        # STEP 10: REQUEST DID NOT GET THE LOCK
        #
        # Another request is currently rebuilding the cache.
        # Wait briefly and check Redis again.
        # =====================================================

        for _ in range(20):

            time.sleep(0.1)

            # Check product cache
            cached_product = redis_client.hgetall(
                cache_key
            )

            print(
                "WAITING FOR CACHE:",
                cached_product
            )

            if cached_product:

                view_count = redis_client.incr(
                    f"product:{product_id}:views"
                )

                return JsonResponse({
                    "id": product_id,
                    "name": cached_product["name"],
                    "price": float(cached_product["price"]),
                    "stock": int(cached_product["stock"]),
                    "views": view_count,
                })

            # Check negative cache
            negative_cache = redis_client.get(
                negative_cache_key
            )

            if negative_cache == "NOT_FOUND":

                print("NEGATIVE CACHE HIT WHILE WAITING")

                return JsonResponse(
                    {"error": "Product not found"},
                    status=404
                )

        # -----------------------------------------------------
        # STEP 11: FALLBACK
        # -----------------------------------------------------

        try:

            product = Product.objects.get(
                id=product_id
            )

        except Product.DoesNotExist:

            return JsonResponse(
                {"error": "Product not found"},
                status=404
            )

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
            "views": redis_client.incr(
                f"product:{product_id}:views"
            ),
        })

    # =========================================================
    # GET /products/
    #
    # Retrieve all products.
    # =========================================================

    if request.method == "GET":

        cached_products = redis_client.get(
            "products:all"
        )

        print("REDIS CHECK:", cached_products)

        if cached_products:

            products = json.loads(
                cached_products
            )

            return JsonResponse(
                products,
                safe=False
            )

        products = Product.objects.all()

        data = []

        for product in products:

            data.append({
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock,
            })

        redis_client.set(
            "products:all",
            json.dumps(data),
            ex=60
        )

        return JsonResponse(
            data,
            safe=False
        )

    # =========================================================
    # POST /products/
    #
    # Create a new product.
    # =========================================================

    if request.method == "POST":

        body = json.loads(
            request.body
        )

        product = Product.objects.create(
            name=body["name"],
            price=body["price"],
            stock=body["stock"],
        )

        # Invalidate product list cache
        redis_client.delete(
            "products:all"
        )

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
        }, status=201)

    # =========================================================
    # PUT /products/<id>/
    #
    # Update an existing product.
    # =========================================================

    if request.method == "PUT":

        body = json.loads(
            request.body
        )

        try:

            product = Product.objects.get(
                id=product_id
            )

        except Product.DoesNotExist:

            return JsonResponse(
                {"error": "Product not found"},
                status=404
            )

        product.name = body["name"]
        product.price = body["price"]
        product.stock = body["stock"]

        product.save()

        # Invalidate product list cache
        redis_client.delete(
            "products:all"
        )

        # Invalidate individual product cache
        redis_client.delete(
            f"product:{product_id}"
        )

        # If this product previously had a negative cache,
        # remove it because the product now exists.
        redis_client.delete(
            f"product:{product_id}:not_found"
        )

        return JsonResponse({
            "id": product.id,
            "name": product.name,
            "price": float(product.price),
            "stock": product.stock,
        })

    # =========================================================
    # DELETE /products/<id>/
    #
    # Delete an existing product.
    # =========================================================

    if request.method == "DELETE":

        try:

            product = Product.objects.get(
                id=product_id
            )

        except Product.DoesNotExist:

            return JsonResponse(
                {"error": "Product not found"},
                status=404
            )

        product.delete()

        # Invalidate product list cache
        redis_client.delete(
            "products:all"
        )

        # Invalidate individual product cache
        redis_client.delete(
            f"product:{product_id}"
        )

        return JsonResponse({
            "message": "Product deleted successfully"
        })

    # =========================================================
    # UNSUPPORTED HTTP METHOD
    # =========================================================

    return JsonResponse(
        {"error": "Method not allowed"},
        status=405
    )


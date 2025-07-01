import redis
from decimal import Decimal
from django.conf import settings
from .models import Product


# Re-use a single Redis connection for the whole module
r = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,     # return Python str instead of bytes
    socket_timeout=5,          # fail fast if Redis is down
)


class Recommender:
    # ----------------------------------
    # internal helpers
    # ----------------------------------
    @staticmethod
    def _product_key(product_id: int) -> str:
        """Key pattern: product:<id>:purchased_with"""
        return f"product:{product_id}:purchased_with"

    # ----------------------------------
    # record a completed basket
    # ----------------------------------
    def products_bought(self, products):
        """
        `products` – iterable of Product instances.
        For every pair (A, B) in that basket: ZINCRBY 1 on key product:A:purchased_with, member B.
        """
        product_ids = [p.id for p in products]

        pipe = r.pipeline()
        for pid in product_ids:
            for other_id in product_ids:
                if pid == other_id:
                    continue
                pipe.zincrby(self._product_key(pid), 1, other_id)
        pipe.execute()

    # ----------------------------------
    # generate suggestions
    # ----------------------------------
    def suggest_products_for(self, products, *, max_results=6):
        """
        `products` – iterable of Product objects (or IDs).
        Returns a list of up to `max_results` Product instances, ordered by score.
        """
        if not products:
            return []

        product_ids = [p.id if isinstance(p, Product) else int(p) for p in products]

        # 1️⃣  Single product → read its set directly
        if len(product_ids) == 1:
            key = self._product_key(product_ids[0])
            ids = r.zrevrange(key, 0, max_results - 1)

        # 2️⃣  Multiple products → merge sets into a temporary key
        else:
            tmp_key = f"tmp_reco_{'_'.join(map(str, product_ids))}"
            keys = [self._product_key(pid) for pid in product_ids]

            r.zunionstore(tmp_key, keys)
            # Don’t recommend the products themselves
            r.zrem(tmp_key, *product_ids)

            ids = r.zrevrange(tmp_key, 0, max_results - 1)
            r.delete(tmp_key)

        # Fetch Product objects and preserve score order
        ids_int = list(map(int, ids))
        qs = Product.objects.filter(id__in=ids_int)
        products_map = {p.id: p for p in qs}
        return [products_map[i] for i in ids_int if i in products_map]

    # ----------------------------------
    # maintenance helper
    # ----------------------------------
    def clear_purchases(self):
        """
        Delete all product:<id>:purchased_with keys (useful for tests or dev reset).
        """
        for pid in Product.objects.values_list("id", flat=True):
            r.delete(self._product_key(pid))

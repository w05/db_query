"""Create demo tables and seed random data into local PostgreSQL."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

import asyncpg

URL = "postgresql://postgres:rzx1218@127.0.0.1:5432/postgres"

FIRST = [
    "Alice",
    "Bob",
    "Carol",
    "David",
    "Eve",
    "Frank",
    "Grace",
    "Helen",
    "Ivan",
    "Julia",
    "Kevin",
    "Linda",
    "Mike",
    "Nina",
    "Oscar",
]
LAST = ["Zhang", "Wang", "Li", "Chen", "Liu", "Yang", "Huang", "Zhao", "Wu", "Zhou"]
STATUSES = ["active", "inactive", "pending"]
PRODUCTS = [
    "Keyboard",
    "Mouse",
    "Monitor",
    "Headset",
    "Laptop",
    "USB Hub",
    "Webcam",
    "SSD",
]


async def main() -> None:
    conn = await asyncpg.connect(URL)
    try:
        await conn.execute("DROP TABLE IF EXISTS order_items CASCADE")
        await conn.execute("DROP TABLE IF EXISTS orders CASCADE")
        await conn.execute("DROP TABLE IF EXISTS products CASCADE")
        await conn.execute("DROP TABLE IF EXISTS users CASCADE")

        await conn.execute(
            """
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(200) UNIQUE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price NUMERIC(10, 2) NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id),
                total NUMERIC(12, 2) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE order_items (
                id SERIAL PRIMARY KEY,
                order_id INT NOT NULL REFERENCES orders(id),
                product_id INT NOT NULL REFERENCES products(id),
                quantity INT NOT NULL CHECK (quantity > 0)
            )
            """
        )

        product_ids: list[int] = []
        for name in PRODUCTS:
            pid = await conn.fetchval(
                "INSERT INTO products (name, price) VALUES ($1, $2) RETURNING id",
                name,
                round(random.uniform(29.9, 999.0), 2),
            )
            product_ids.append(pid)

        user_ids: list[int] = []
        for i in range(1, 31):
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            email = f"user{i}@example.com"
            status = random.choice(STATUSES)
            created = datetime.now() - timedelta(days=random.randint(0, 365))
            uid = await conn.fetchval(
                """
                INSERT INTO users (name, email, status, created_at)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                name,
                email,
                status,
                created,
            )
            user_ids.append(uid)

        for _ in range(50):
            uid = random.choice(user_ids)
            n_items = random.randint(1, 4)
            items: list[tuple[int, int]] = []
            total = 0.0
            for _ in range(n_items):
                pid = random.choice(product_ids)
                qty = random.randint(1, 5)
                price = await conn.fetchval(
                    "SELECT price FROM products WHERE id = $1", pid
                )
                total += float(price) * qty
                items.append((pid, qty))
            created = datetime.now() - timedelta(days=random.randint(0, 180))
            oid = await conn.fetchval(
                """
                INSERT INTO orders (user_id, total, created_at)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                uid,
                round(total, 2),
                created,
            )
            for pid, qty in items:
                await conn.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity)
                    VALUES ($1, $2, $3)
                    """,
                    oid,
                    pid,
                    qty,
                )

        counts = await conn.fetch(
            """
            SELECT 'users' AS t, COUNT(*)::int AS c FROM users
            UNION ALL SELECT 'products', COUNT(*)::int FROM products
            UNION ALL SELECT 'orders', COUNT(*)::int FROM orders
            UNION ALL SELECT 'order_items', COUNT(*)::int FROM order_items
            ORDER BY 1
            """
        )
        for row in counts:
            print(f"{row['t']}: {row['c']}")

        print("--- sample users ---")
        for row in await conn.fetch(
            "SELECT id, name, email, status FROM users ORDER BY id LIMIT 5"
        ):
            print(dict(row))
        print("DONE")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())

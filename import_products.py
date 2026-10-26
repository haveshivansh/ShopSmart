import requests

from app import app
from models import db, Product

API_URL = "https://dummyjson.com/products?limit=100"


def import_products():
    print("Connecting to product catalogue...")

    try:
        response = requests.get(API_URL, timeout=20)
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        print("Could not download products.")
        print("Error:", error)
        print("Check your internet connection and try again.")
        return

    products = data.get("products", [])

    if not products:
        print("No products received from the API.")
        return

    imported = 0
    updated = 0

    with app.app_context():
        for item in products:
            source_id = item.get("id")

            if not source_id:
                continue

            product = Product.query.filter_by(
                source_id=source_id
            ).first()

            if product is None:
                product = Product(source_id=source_id)
                db.session.add(product)
                imported += 1
            else:
                updated += 1

            product.name = item.get("title", "Unnamed Product")
            product.category = item.get("category", "Other").title()
            product.brand = item.get("brand") or "Generic"
            product.price = float(item.get("price") or 0)
            product.old_price = (
                float(item["price"]) * 1.15
                if item.get("price") is not None
                else None
            )
            product.rating = float(item.get("rating") or 0)
            product.image_url = item.get("thumbnail") or ""
            product.description = item.get("description", "")
            product.stock = max(0, int(item.get("stock") or 0))
            product.source = "DummyJSON"

        try:
            db.session.commit()

        except Exception:
            db.session.rollback()
            raise

    print("\nProduct import successful!")
    print("New products:", imported)
    print("Updated products:", updated)
    print("Products received:", len(products))


if __name__ == "__main__":
    import_products()
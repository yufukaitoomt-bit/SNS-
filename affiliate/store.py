"""商品データ(JSON)の読み書き。"""
import json
import re
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "products.json"


def load() -> dict:
    if not DATA_FILE.exists():
        return {"active": None, "products": []}
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save(data: dict) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def make_id(brand: str, name: str) -> str:
    slug = re.sub(r"[^0-9a-zA-Z]+", "-", f"{brand}-{name}".lower()).strip("-")
    return slug or f"item-{abs(hash(brand + name)) % 100000}"


def get(product_id: str = None) -> dict:
    data = load()
    pid = product_id or data.get("active")
    for p in data["products"]:
        if p["id"] == pid:
            return p
    raise KeyError(pid)


def upsert(product: dict, make_active: bool = False) -> dict:
    data = load()
    product["id"] = product.get("id") or make_id(product.get("brand", ""), product.get("name", ""))
    data["products"] = [p for p in data["products"] if p["id"] != product["id"]] + [product]
    if make_active or not data.get("active"):
        data["active"] = product["id"]
    save(data)
    return product


def delete(product_id: str) -> None:
    data = load()
    data["products"] = [p for p in data["products"] if p["id"] != product_id]
    if data.get("active") == product_id:
        data["active"] = data["products"][0]["id"] if data["products"] else None
    save(data)


def set_active(product_id: str) -> None:
    get(product_id)
    data = load()
    data["active"] = product_id
    save(data)

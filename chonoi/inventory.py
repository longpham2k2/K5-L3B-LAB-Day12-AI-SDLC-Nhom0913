"""File kho.

v1.2 (TICKET-03, đang dùng): {"items": [{"id", "kind", "fresh"}, ...]} — kho CÁ THỂ. Kho đếm -> mã 2.
  read_inventory(path) -> list cá thể nội bộ (fresh là Fraction, xem chonoi/items.py)
  write_inventory(path, items) -> ghi theo id, fresh float đầy đủ (đọc lại giữ nhánh ở ngưỡng 30), ghi nguyên tử.
  validate_item_list(raw) -> kiểm mảng cá thể (dùng cho scenario gather.hold / quan.stock).
v1.0–1.1 (cũ): {"items": {kind: số nguyên >= 0}} — `validate_items` còn dùng cho map đếm (vd. day_plan.ingredients).
"""

import json
import math
import os
import tempfile

from . import items as it
from .errors import BadInput
from .ids import id_key

KINDS = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")  # v1.1: 6 nguyên liệu
KINDS_P1 = KINDS  # tên cũ, giữ để không vỡ import


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


ITEM_KEYS = {"id", "kind", "fresh"}


def validate_item_list(raw, kinds=KINDS, name="items") -> list:
    """Mảng cá thể v1.2: id chuỗi khác rỗng duy nhất, kind thuộc danh mục, fresh hữu hạn trong [0, 100]."""
    if not isinstance(raw, list):
        raise BadInput(f"{name} phải là mảng cá thể {{id, kind, fresh}} (v1.2; kho đếm theo loại không còn hợp lệ)")
    seen = set()
    for i, x in enumerate(raw):
        if not isinstance(x, dict) or set(x) != ITEM_KEYS:
            raise BadInput(f"{name}[{i}] phải có đúng các khóa id, kind, fresh")
        if not isinstance(x["id"], str) or not x["id"]:
            raise BadInput(f"{name}[{i}].id phải là chuỗi khác rỗng")
        if x["id"] in seen:
            raise BadInput(f"{name}: id trùng {x['id']}")
        seen.add(x["id"])
        if x["kind"] not in kinds:
            raise BadInput(f"{name}[{i}].kind lạ: {x['kind']!r}")
        f = x["fresh"]
        if isinstance(f, bool) or not isinstance(f, (int, float)) or not math.isfinite(f) or not (0 <= f <= 100):
            raise BadInput(f"{name}[{i}].fresh phải là số hữu hạn trong [0, 100]")
    return raw


def read_inventory(path: str, kinds=KINDS) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return it.load(validate_item_list(data["items"], kinds))


def write_inventory(path: str, items: list):
    """Ghi kho cá thể theo id; fresh float đầy đủ (json repr), qua file tạm cùng thư mục rồi thay thế nguyên tử."""
    rows = [{"id": x["id"], "kind": x["kind"], "fresh": float(x["fresh"])} for x in sorted(items, key=lambda x: id_key(x["id"]))]
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": rows}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

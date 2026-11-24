from typing import Any, NoReturn

from flask import abort


def not_found(entity: None | str = None, detail: None | Any = None) -> NoReturn:
    # not_found("Order") -> "Order not found"
    # not_found("Product", [3, 9]) -> "Product not found: [3, 9]"
    message = f"{entity} not found" if entity else "There is no item"
    if detail is not None:
        message += f": {detail}"
    abort(404, description=message)

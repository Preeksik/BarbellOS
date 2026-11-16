"""Schemat Pydantic -> podzbiór JSON Schema, który przyjmują dostawcy modeli.

Pydantic generuje odwołania `$ref`/`$defs`, tytuły i wartości domyślne. Dostawcy
dokumentują węższy zestaw słów kluczowych, a zbyt złożony schemat odrzucają błędem 400.
Dlatego odwołania są rozwijane w miejscu, a ozdobniki usuwane.
"""

from pydantic import BaseModel

_DROPPED = ("title", "default")


def provider_schema(model: type[BaseModel]) -> dict:
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})
    return _simplify(schema, defs)


def _simplify(node, defs: dict):
    if isinstance(node, list):
        return [_simplify(item, defs) for item in node]
    if not isinstance(node, dict):
        return node
    if "$ref" in node:
        # Modele bez rekurencji: definicję można wstawić w miejsce odwołania.
        target = defs[node["$ref"].rsplit("/", 1)[-1]]
        node = {**target, **{k: v for k, v in node.items() if k != "$ref"}}

    out = {}
    for key, value in node.items():
        if key in _DROPPED:
            continue
        if key == "properties":
            # Klucze to nazwy pól, nie słowa kluczowe schematu: pole może nazywać się „title".
            out[key] = {name: _simplify(sub, defs) for name, sub in value.items()}
        else:
            out[key] = _simplify(value, defs)
    return _collapse_nullable(out)


def _collapse_nullable(node: dict) -> dict:
    """`anyOf: [X, null]` -> `type: [X, "null"]`, czyli zapis z dokumentacji dostawców.

    Wariant z listą dozwolonych wartości zostaje jako `anyOf`: po scaleniu lista `enum`
    wykluczałaby `null`.
    """
    variants = node.get("anyOf")
    if not isinstance(variants, list) or len(variants) != 2:
        return node
    others = [v for v in variants if v != {"type": "null"}]
    if len(others) != 1:
        return node
    (other,) = others
    if not isinstance(other.get("type"), str) or "enum" in other or "const" in other:
        return node
    rest = {k: v for k, v in node.items() if k != "anyOf"}
    return {**other, "type": [other["type"], "null"], **rest}

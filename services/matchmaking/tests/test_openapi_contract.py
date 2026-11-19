"""openapi.yaml must describe exactly the routes the code serves: no missing and no extra endpoints."""
import os
import re

import yaml

from app import create_app

SPEC = os.path.join(os.path.dirname(__file__), "..", "openapi.yaml")


def test_every_route_is_documented_and_every_documented_route_exists():
    routes = {
        (re.sub(r"<(?:int:)?(\w+)>", r"{\1}", rule.rule), method)
        for rule in create_app().url_map.iter_rules()
        if rule.endpoint != "static"
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }
    with open(SPEC, encoding="utf-8") as file:
        spec = yaml.safe_load(file)
    documented = {(path, method.upper()) for path, operations in spec["paths"].items() for method in operations}
    assert routes == documented

from collections.abc import Iterator
from typing import Any

from app.main import app
from tests.api.test_authorization_matrix import ROUTE_ACCESS, Access

COMPANY_ACCESS = {Access.AUTHENTICATED, Access.COMPANY, Access.COMPANY_PROFILE}
STAFF_ZONE_ROUTES = (
    "GET /api/kp/events/{event_id}/booth-zones",
    "GET /api/kp/events/{event_id}/bookings",
    "GET /api/kp/staff/bookings/{booking_id}/upgrade-waitlist",
)


def openapi() -> dict[str, Any]:
    return app.openapi()


def response_schemas(route: str) -> list[dict[str, Any]]:
    method, path = route.split(" ", 1)
    operation = openapi()["paths"][path][method.lower()]
    return [
        media["schema"]
        for response in operation["responses"].values()
        for media in response.get("content", {}).values()
    ]


def reachable_properties(schema: Any, seen: set[str]) -> Iterator[str]:
    if isinstance(schema, list):
        for item in schema:
            yield from reachable_properties(item, seen)
        return
    if not isinstance(schema, dict):
        return
    reference = schema.get("$ref")
    if isinstance(reference, str):
        name = reference.rsplit("/", 1)[-1]
        if name in seen:
            return
        seen.add(name)
        yield from reachable_properties(openapi()["components"]["schemas"][name], seen)
        return
    yield from schema.get("properties", {})
    for value in schema.values():
        yield from reachable_properties(value, seen)


def exposes_capacity(route: str) -> bool:
    return "capacity" in set(reachable_properties(response_schemas(route), set()))


def test_no_company_response_exposes_zone_capacity():
    company_routes = [
        route for route, access in ROUTE_ACCESS.items() if access in COMPANY_ACCESS
    ]

    assert company_routes
    assert [route for route in company_routes if exposes_capacity(route)] == []


def test_staff_zone_responses_keep_the_capacity():
    assert [route for route in STAFF_ZONE_ROUTES if not exposes_capacity(route)] == []

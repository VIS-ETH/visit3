import json
import sys
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

backend_dir = Path(__file__).resolve().parent.parent / "backend"

sys.path.append(str(backend_dir))

dotenv_path = backend_dir / ".env"
load_dotenv(dotenv_path)

from app.main import app

JsonObject = dict[str, object]


def _as_object(value: object) -> JsonObject | None:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return None


def _resolve_component_ref(ref: str) -> str | None:
    prefix = "#/components/schemas/"
    if not ref.startswith(prefix):
        return None
    return ref.removeprefix(prefix)


def _normalize_orval_file_uploads(openapi_schema: JsonObject) -> None:
    """Adapt FastAPI/Pydantic file schemas to the OpenAPI 3.0 shape Orval expects."""
    components = _as_object(openapi_schema.get("components"))
    if components is None:
        return
    schemas = _as_object(components.get("schemas"))
    if schemas is None:
        return

    paths = _as_object(openapi_schema.get("paths"))
    if paths is None:
        return

    for path_item in paths.values():
        path_item_object = _as_object(path_item)
        if path_item_object is None:
            continue
        for operation in path_item_object.values():
            operation_object = _as_object(operation)
            if operation_object is None:
                continue
            request_body = _as_object(operation_object.get("requestBody"))
            if request_body is None:
                continue
            content = _as_object(request_body.get("content"))
            if content is None:
                continue
            multipart = _as_object(content.get("multipart/form-data"))
            if multipart is None:
                continue
            request_schema = _as_object(multipart.get("schema"))
            if request_schema is None:
                continue
            schema_ref = request_schema.get("$ref")
            if not isinstance(schema_ref, str):
                continue
            schema_name = _resolve_component_ref(schema_ref)
            if schema_name is None:
                continue
            schema = _as_object(schemas.get(schema_name))
            if schema is None:
                continue
            properties = _as_object(schema.get("properties"))
            if properties is None:
                continue
            for property_schema in properties.values():
                property_schema_object = _as_object(property_schema)
                if property_schema_object is None:
                    continue
                if (
                    property_schema_object.get("contentMediaType")
                    != "application/octet-stream"
                ):
                    continue
                property_schema_object["format"] = "binary"
                property_schema_object.pop("contentMediaType", None)


def export_openapi(location: str) -> None:
    openapi_schema = cast(JsonObject, app.openapi())
    _normalize_orval_file_uploads(openapi_schema)
    with open(location, "w") as f:
        json.dump(openapi_schema, f, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./extract_docs.py <output_path>")
        sys.exit(1)
    export_openapi(sys.argv[1])

#!/usr/bin/env python3
"""Offline safeguards for the optional, unapplied Ninai Render example.

The example uses JSON-formatted YAML, which is valid YAML and can be parsed
without a runtime YAML dependency. This policy check is not proof of a live
Render account's configuration. --schema-file additionally validates against a
downloaded official Render JSON schema using optional jsonschema tooling.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SCHEMA = "https://render.com/schema/render.yaml.json"
PROTECTED_SETTINGS = {
    "NINAI_OAUTH_ISSUER", "NINAI_OAUTH_AUDIENCE", "NINAI_OAUTH_JWKS_URI",
    "NINAI_OAUTH_AUTHORIZATION_ENDPOINT", "NINAI_OAUTH_TOKEN_ENDPOINT",
    "NINAI_PUBLIC_RESOURCE_URL", "NINAI_OAUTH_CONTROL_CLIENT_ID", "NINAI_CONTROL_BASE_URL",
}


def validate_policy(document: dict) -> None:
    def require(condition, message):
        if not condition:
            raise ValueError(message)

    require(set(document) == {"previews", "services", "databases"}, "Review unexpected root resources before extending this example")
    require(document.get("previews") == {"generation": "off"}, "Example must not create automatic preview resources")
    require(len(document.get("services", [])) == 1 and len(document.get("databases", [])) == 1, "Expected one optional service and one database")
    service, database = document["services"][0], document["databases"][0]
    require(set(service) == {"type", "name", "runtime", "repo", "branch", "dockerfilePath", "dockerContext", "region", "plan", "numInstances", "autoDeployTrigger", "healthCheckPath", "envVars"}, "Review unexpected service options before extending this example")
    require(set(database) == {"name", "databaseName", "user", "region", "plan", "diskSizeGB", "postgresMajorVersion", "ipAllowList"}, "Review unexpected database options before extending this example")
    require(service.get("repo") == "https://github.com/HariDarshan2321/ninai" and service.get("branch") == "main", "Example must deploy the reviewed Ninai source branch")
    require(service.get("type") == "web" and service.get("runtime") == "docker", "Use the hosted Docker web service")
    require(service.get("name") == "ninai-cloud-example" and database.get("name") == "ninai-cloud-example-db", "Example names must not silently target existing production resources")
    require(service.get("dockerfilePath") == "./cloud/Dockerfile" and service.get("dockerContext") == "./cloud", "Docker paths must target the hosted package")
    require("rootDir" not in service, "Do not alter the example's Docker path interpretation with rootDir")
    require(service.get("plan") == "0.5c-512mb" and database.get("plan") == "0.1c-256mb", "Example must retain its explicit paid compute assumptions")
    require(type(service.get("numInstances")) is int and service["numInstances"] == 1 and "scaling" not in service, "Example must not silently create extra replicas")
    require(service.get("healthCheckPath") == "/ready", "Health must check database readiness")
    require(service.get("autoDeployTrigger") == "checksPass", "Deploy only after CI checks pass")
    require(service.get("region") == database.get("region") == "frankfurt", "Example service and database must use the same explicit region")
    require(database.get("postgresMajorVersion") == "16", "Example targets the PostgreSQL version exercised by CI, not an existing database upgrade")
    require(database.get("ipAllowList") == [], "Database must reject all external IPs")
    require("disk" not in service, "Hosted service must not mount a local memory vault")
    items = service.get("envVars", [])
    keys = [item.get("key") for item in items]
    require(len(keys) == len(set(keys)), "Environment variable keys must be unique")
    env = {item["key"]: item for item in items}
    require("NINAI_DATA_DIR" not in env, "Local memory storage must stay separate")
    require(env.get("DATABASE_URL") == {"key": "DATABASE_URL", "fromDatabase": {"name": database["name"], "property": "connectionString"}}, "Database URL must use the private managed reference, never a hardcoded credential")
    for key, value in {"HOST": "0.0.0.0", "PORT": "10000", "NINAI_AUTH_MODE": "oauth", "NINAI_OAUTH_ALLOW_PAT": "false", "NINAI_DATABASE_POOL_MIN_SIZE": "1", "NINAI_DATABASE_POOL_MAX_SIZE": "10"}.items():
        require(env.get(key) == {"key": key, "value": value}, f"Unexpected {key} example setting")
    for key in PROTECTED_SETTINGS:
        require(env.get(key) == {"key": key, "sync": False} and env[key].get("sync") is False, f"Enter {key} in protected service settings, not the repository")
    require(set(keys) == PROTECTED_SETTINGS | {"DATABASE_URL", "HOST", "PORT", "NINAI_AUTH_MODE", "NINAI_OAUTH_ALLOW_PAT", "NINAI_DATABASE_POOL_MIN_SIZE", "NINAI_DATABASE_POOL_MAX_SIZE"}, "Review unexpected environment settings before extending this example")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--example", type=Path, default=ROOT / "cloud" / "render.example.yaml")
    parser.add_argument("--schema-file", type=Path, help="Already-downloaded official Render JSON schema; no network request is made")
    args = parser.parse_args()
    try:
        document = json.loads(args.example.read_text())
        validate_policy(document)
        report = {"passed": True, "example_policy": "passed", "live_account_verified": False, "official_schema": "not_checked"}
        if args.schema_file:
            try:
                from jsonschema import Draft202012Validator
            except ImportError:
                raise ValueError("Use optional tooling: uv run --with jsonschema scripts/validate_render_example.py --schema-file /path/to/render-schema.json") from None
            data = args.schema_file.read_bytes()
            schema = json.loads(data)
            if schema.get("$id") != OFFICIAL_SCHEMA:
                raise ValueError("Expected the official Render schema URL as $id")
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(document)
            report.update(official_schema="passed", schema_sha256=hashlib.sha256(data).hexdigest())
        print(json.dumps(report, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({"passed": False, "reason": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

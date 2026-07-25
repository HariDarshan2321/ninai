#!/bin/sh
set -eu

# Fail the release before serving traffic if the database is unreachable or a
# migration cannot be applied. The migration runner serializes concurrent
# replicas with a PostgreSQL advisory transaction lock.
python -m ninai_cloud.migrations

exec "$@"

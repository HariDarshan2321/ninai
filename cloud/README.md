# Ninai hosted store

This package is the explicit opt-in PostgreSQL backend. It does not import,
inspect, or synchronize the local SQLite vault.

Apply migrations:

```bash
DATABASE_URL=postgresql://... python -m ninai_cloud.migrations
```

Run tests (integration tests require a disposable database):

```bash
python -m unittest discover -s tests -v
NINAI_TEST_DATABASE_URL=postgresql://... python -m unittest discover -s tests -v
```

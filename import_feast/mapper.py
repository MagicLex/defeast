"""Map a Feast repo (read through the Feast SDK registry) into a Hopsworks migration plan.
Reused by the dry-run planner and, later, the executor. Never parses the repo's .py files."""

from __future__ import annotations

import os

from .plan import (
    Backfill,
    ConnectorOp,
    FeatureGroupOp,
    FeatureViewOp,
    Join,
    MigrationPlan,
    Warning,
)

# Feast primitive type name -> Hopsworks offline (Hive) type.
_PRIM = {
    "Int32": "int",
    "Int64": "bigint",
    "Float32": "float",
    "Float64": "double",
    "String": "string",
    "Bytes": "binary",
    "Bool": "boolean",
    "UnixTimestamp": "timestamp",
}

# Warehouse source class -> Hopsworks storage connector type.
_CONNECTOR = {
    "BigQuerySource": "bigquery",
    "RedshiftSource": "redshift",
    "SnowflakeSource": "snowflake",
    "SparkSource": "jdbc",
    "TrinoSource": "jdbc",
    "PostgreSQLSource": "jdbc",
    "AthenaSource": "jdbc",
    "MsSqlServerSource": "jdbc",
    "ClickhouseSource": "jdbc",
}


def feast_type_to_hopsworks(dtype) -> tuple[str, Warning | None]:
    s = str(dtype)
    if s.startswith("Array(") and s.endswith(")"):
        inner, w = feast_type_to_hopsworks_name(s[len("Array(") : -1])
        return f"array<{inner}>", w
    return feast_type_to_hopsworks_name(s)


def feast_type_to_hopsworks_name(name: str) -> tuple[str, Warning | None]:
    if name in _PRIM:
        return _PRIM[name], None
    if name == "Decimal":
        return "string", Warning("", "type", "Decimal has no precision/scale in transit, stored as string")
    if name.startswith("Set("):
        inner = name[len("Set(") : -1]
        base = _PRIM.get(inner, "string")
        return f"array<{base}>", Warning("", "type", f"Set({inner}) degrades to array<{base}> (no Set in Hopsworks)")
    if name.startswith("Struct") or name in ("Json", "Map", "ScalarMap"):
        return "string", Warning("", "type", f"{name} has no clean Hopsworks type, stored as string")
    return "string", Warning("", "type", f"unknown Feast type {name}, defaulting to string")


def _entity_join_keys(fv, entities: dict) -> list[str]:
    keys: list[str] = []
    for name in fv.entities:
        if name == "__dummy":  # Feast's entityless placeholder
            continue
        ent = entities.get(name)
        keys.append(ent.join_key if ent is not None else name)
    return keys


def _source_ref(source) -> str:
    for attr in ("path", "table", "query", "topic"):
        v = getattr(source, attr, None)
        if v:
            return str(v)
    return getattr(source, "name", "?")


def _est_rows(path: str, repo_path: str) -> int | None:
    p = path if os.path.isabs(path) else os.path.join(repo_path, path)
    try:
        import pyarrow.parquet as pq

        return pq.ParquetFile(p).metadata.num_rows
    except Exception:
        try:
            import pyarrow.dataset as ds

            return ds.dataset(p).count_rows()
        except Exception:
            return None


def _map_batch_fv(fv, entities: dict, repo_path: str):
    src = fv.batch_source
    src_cls = type(src).__name__
    pk = _entity_join_keys(fv, entities)
    event_time = getattr(src, "timestamp_field", None)

    features: list[tuple[str, str]] = []
    warnings: list[Warning] = []
    for f in fv.features:
        htype, w = feast_type_to_hopsworks(f.dtype)
        features.append((f.name, htype))
        if w is not None:
            warnings.append(Warning(fv.name, w.kind, f"{f.name}: {w.message}"))
    # entity columns carry their own types too
    for f in getattr(fv, "entity_columns", []):
        htype, _ = feast_type_to_hopsworks(f.dtype)
        if f.name not in [c[0] for c in features]:
            features.insert(0, (f.name, htype))
    # the event-time column is part of the FG schema; carry it so the executor can
    # declare the schema explicitly instead of letting parquet inference decide.
    if event_time and event_time not in [c[0] for c in features]:
        features.append((event_time, "timestamp"))

    conn = None
    if src_cls == "FileSource":
        external = False
        # Resolve to an absolute path so the plan is self-contained: the executor runs
        # in a separate env with a different CWD and cannot resolve a repo-relative path.
        ref = _source_ref(src)
        ref = ref if os.path.isabs(ref) else os.path.join(repo_path, ref)
        backfill = Backfill("file", ref, _est_rows(ref, repo_path))
    elif src_cls in _CONNECTOR:
        external = True
        backfill = Backfill("external", _source_ref(src))
        conn = ConnectorOp(
            name=f"{src_cls.replace('Source', '').lower()}_conn",
            connector_type=_CONNECTOR[src_cls],
            for_source=getattr(src, "name", src_cls),
            warnings=[Warning(fv.name, "credentials", f"{src_cls} credentials must be recreated as a Hopsworks storage connector")],
        )
    else:
        external = True
        backfill = Backfill("external", _source_ref(src))
        warnings.append(Warning(fv.name, "unsupported", f"source {src_cls} has no mapped connector, review by hand"))

    ttl = None
    if getattr(fv, "ttl", None) and fv.ttl.total_seconds() > 0:
        ttl = str(fv.ttl)
        warnings.append(Warning(fv.name, "ttl", f"TTL {ttl}: online expiry transfers, the historical-join lookback bound does not"))

    if getattr(src, "created_timestamp_column", None):
        warnings.append(Warning(fv.name, "dedup", f"created_timestamp_column '{src.created_timestamp_column}' is not carried: rows sharing a key and event time keep the last write"))
    if getattr(src, "field_mapping", None):
        backfill.field_mapping = dict(src.field_mapping)
        warnings.append(Warning(fv.name, "type", f"source field_mapping {dict(src.field_mapping)} applied during backfill"))

    fg = FeatureGroupOp(
        name=fv.name,
        version=1,
        primary_key=pk,
        event_time=event_time,
        online_enabled=bool(getattr(fv, "online", False)),
        features=features,
        external=external,
        backfill=backfill,
        ttl=ttl,
        warnings=warnings,
    )
    return fg, conn


def _map_feature_service(svc, batch_fv_by_name: dict, entities: dict):
    projs = svc.feature_view_projections
    warnings: list[Warning] = []
    selects: dict[str, list[str]] = {}
    joins: list[Join] = []
    serving: list[str] = []
    base_fg = None

    for i, proj in enumerate(projs):
        fg_name = proj.name
        if fg_name not in batch_fv_by_name:
            warnings.append(Warning(svc.name, "unsupported", f"projection '{fg_name}' is not a batch feature view (on-demand or stream), not joined here"))
            continue
        selects[fg_name] = [f.name for f in proj.features]
        keys = _entity_join_keys(batch_fv_by_name[fg_name], entities)
        for k in keys:
            if k not in serving:
                serving.append(k)
        if base_fg is None:
            base_fg = fg_name
        else:
            on = list(getattr(proj, "join_key_map", {}).values()) or keys
            prefix = getattr(proj, "name_alias", None)
            joins.append(Join(right_fg=fg_name, on=on, prefix=prefix))
        if getattr(proj, "join_key_map", None):
            warnings.append(Warning(svc.name, "type", f"projection '{fg_name}' join_key_map {dict(proj.join_key_map)} -> explicit join-on"))

    return FeatureViewOp(
        name=svc.name,
        base_fg=base_fg or "?",
        selects=selects,
        joins=joins,
        serving_keys=serving,
        warnings=warnings,
    )


def build_plan(store, repo_path: str) -> MigrationPlan:
    entities = {e.name: e for e in store.list_entities()}
    batch_fvs = store.list_batch_feature_views()
    batch_fv_by_name = {fv.name: fv for fv in batch_fvs}

    plan = MigrationPlan(project=store.project, repo_path=repo_path)

    seen_conn: dict[str, ConnectorOp] = {}
    for fv in batch_fvs:
        fg, conn = _map_batch_fv(fv, entities, repo_path)
        if conn is not None and conn.name not in seen_conn:
            seen_conn[conn.name] = conn
            plan.connectors.append(conn)
        plan.feature_groups.append(fg)

    n_odfv = 0
    try:
        for odfv in store.list_on_demand_feature_views():
            n_odfv += 1
            plan.warnings.append(Warning(odfv.name, "udf", "on-demand feature view: translate the UDF body_text to a Hopsworks @udf; on-demand (FG) vs model-dependent (FV) placement is a manual choice"))
    except Exception as e:
        plan.warnings.append(Warning("*", "udf", f"could not read on-demand feature views ({e}); re-run with a matching Feast/Python or skip_udf"))

    n_sfv = 0
    try:
        for sfv in store.list_stream_feature_views():
            n_sfv += 1
            plan.warnings.append(Warning(sfv.name, "stream", "stream feature view: maps to a stream=True FG; window aggregations must be regenerated as a Spark job"))
    except Exception as e:
        plan.warnings.append(Warning("*", "stream", f"could not read stream feature views ({e})"))

    # Label views (Feast 0.66+) hold training labels; the bridge does not replay them yet.
    for lv in getattr(store, "list_label_views", lambda: [])():
        plan.warnings.append(Warning(lv.name, "unsupported", "label view: not replayed, write the labels to a feature group by hand"))

    services = store.list_feature_services()
    for svc in services:
        plan.feature_views.append(_map_feature_service(svc, batch_fv_by_name, entities))

    plan.stats = {
        "entities": len(entities),
        "batch_feature_views": len(batch_fvs),
        "on_demand_feature_views": n_odfv,
        "stream_feature_views": n_sfv,
        "feature_services": len(services),
        "data_sources": len(store.list_data_sources()),
    }
    return plan

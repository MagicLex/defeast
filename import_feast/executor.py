"""Executor: run a migration plan against Hopsworks via hsfs. Consumes the plan dict
(produced by the Feast reader in a separate environment) and reads FileSource backfill
parquet directly with pandas, so it needs hsfs but not feast."""

from __future__ import annotations

# Hopsworks (Hive) type -> numpy dtype, to coerce the backfill dataframe to the plan's
# declared schema before insert. A Feast Int32 feature is commonly stored as parquet
# int64; without coercion hsfs rejects the insert (declared 'int' vs derived 'bigint').
# Only primitives are cast; string/binary/timestamp/array/decimal are left as read.
_HIVE_TO_PANDAS = {
    "tinyint": "int8",
    "smallint": "int16",
    "int": "int32",
    "bigint": "int64",
    "float": "float32",
    "double": "float64",
    "boolean": "bool",
}


def execute(plan: dict, host: str, port: int, project: str, api_key: str, no_statistics: bool = False) -> dict:
    import hopsworks
    import pandas as pd
    from hsfs.feature import Feature

    result = {"connectors_manual": [], "feature_groups": [], "feature_views": [], "skipped": []}

    def log(m):
        print(f"[import-feast] {m}", flush=True)

    proj = hopsworks.login(host=host, port=port, project=project, api_key_value=api_key)
    fs = proj.get_feature_store()
    log(f"connected to {project}")

    # Connectors carry credentials that never migrate: they must be created by hand.
    for c in plan.get("connectors", []):
        log(f"connector {c['name']} ({c['connector_type']}): create by hand with credentials, then link the external FG")
        result["connectors_manual"].append(c["name"])

    for fg in plan.get("feature_groups", []):
        if fg["external"]:
            log(f"external FG {fg['name']}: needs its storage connector, skipped (create by hand)")
            result["skipped"].append(fg["name"])
            continue
        # Declare the schema from the plan's mapped Hopsworks types, so migration
        # fidelity (Int32->int, Decimal->string, Set->array) is honored instead of
        # being re-inferred from the backfill parquet at insert time.
        kwargs = dict(
            name=fg["name"],
            version=fg["version"],
            primary_key=fg["primary_key"],
            event_time=fg["event_time"],
            online_enabled=fg["online_enabled"],
            features=[Feature(name=n, type=t) for n, t in fg["features"]],
        )
        if no_statistics:
            kwargs["statistics_config"] = {"enabled": False}
        g = fs.get_or_create_feature_group(**kwargs)

        bf = fg["backfill"]
        df = pd.read_parquet(bf["ref"])
        if bf.get("field_mapping"):
            df = df.rename(columns=bf["field_mapping"])
        # Coerce to the plan's declared types so migrated fidelity holds and hsfs
        # schema-compat passes. Feast guarantees values fit the declared type; a cast
        # that overflows means the source Feast schema is itself inconsistent, so let it raise.
        for fname, htype in fg["features"]:
            if fname in df.columns and htype in _HIVE_TO_PANDAS and str(df[fname].dtype) != _HIVE_TO_PANDAS[htype]:
                df[fname] = df[fname].astype(_HIVE_TO_PANDAS[htype])
        cols: list[str] = []
        wanted = list(fg["primary_key"]) + ([fg["event_time"]] if fg["event_time"] else []) + [f[0] for f in fg["features"]]
        for c in wanted:
            if c not in cols and c in df.columns:
                cols.append(c)
        g.insert(df[cols], write_options={"wait_for_job": True})
        log(f"FG {fg['name']}: created + backfilled {len(df)} rows, {len(cols)} columns")
        result["feature_groups"].append(fg["name"])

    for fv in plan.get("feature_views", []):
        base = fs.get_feature_group(fv["base_fg"], 1)
        q = base.select(fv["selects"].get(fv["base_fg"], []))
        for i, j in enumerate(fv["joins"]):
            right = fs.get_feature_group(j["right_fg"], 1)
            # A prefix avoids event-time / non-key column collisions across joined groups.
            prefix = j.get("prefix") or f"r{i}_"
            q = q.join(right.select(fv["selects"].get(j["right_fg"], [])), on=j["on"], prefix=prefix)
        fs.get_or_create_feature_view(name=fv["name"], version=1, query=q)
        log(f"FV {fv['name']}: created ({len(fv['selects'])} groups)")
        result["feature_views"].append(fv["name"])

    log(
        f"done: {len(result['feature_groups'])} FGs, {len(result['feature_views'])} FVs, "
        f"{len(result['skipped'])} skipped, {len(result['connectors_manual'])} connectors to wire by hand"
    )
    return result

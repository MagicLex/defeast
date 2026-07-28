"""import-feast: read a Feast repo and print the Hopsworks migration plan it would run.
Slice 0 is dry-run only, nothing is written to Hopsworks."""

from __future__ import annotations

import argparse
import sys

from .mapper import build_plan
from .plan import MigrationPlan


def _load_store(repo: str):
    from feast import FeatureStore

    return FeatureStore(repo_path=repo)


def _fmt_features(features: list[tuple[str, str]], limit: int = 6) -> str:
    shown = ", ".join(f"{n}:{t}" for n, t in features[:limit])
    extra = f", +{len(features) - limit} more" if len(features) > limit else ""
    return f"{shown}{extra} ({len(features)})"


def _short_select(feats: list[str], limit: int = 3) -> str:
    if len(feats) <= limit:
        return str(feats)
    return f"[{', '.join(feats[:limit])}, +{len(feats) - limit}]"


def print_plan(plan: MigrationPlan) -> None:
    s = plan.stats
    print("import-feast plan")
    print(f"  project: {plan.project}")
    print(f"  repo:    {plan.repo_path}")
    print(
        f"  objects: {s['entities']} entities, {s['batch_feature_views']} batch FVs, "
        f"{s['on_demand_feature_views']} on-demand, {s['stream_feature_views']} stream, "
        f"{s['feature_services']} services, {s['data_sources']} sources"
    )

    print(f"\n[1] storage connectors ({len(plan.connectors)})")
    for c in plan.connectors:
        print(f"    {c.name} ({c.connector_type})  <- source {c.for_source}")

    print(f"\n[2] feature groups ({len(plan.feature_groups)})   create before feature views")
    for fg in plan.feature_groups:
        kind = "external" if fg.external else "cached"
        print(
            f"    {fg.name} v{fg.version}  [{kind}]  online={fg.online_enabled}  "
            f"pk={fg.primary_key}  event_time={fg.event_time}"
        )
        print(f"        features: {_fmt_features(fg.features)}")
        if fg.backfill:
            rows = f" (~{fg.backfill.est_rows} rows)" if fg.backfill.est_rows is not None else ""
            print(f"        backfill: {fg.backfill.kind} {fg.backfill.ref}{rows}")
        if fg.ttl:
            print(f"        ttl: {fg.ttl}")
        for w in fg.warnings:
            print(f"      ! {w.kind}: {w.message}")

    print(f"\n[3] feature views ({len(plan.feature_views)})")
    for fv in plan.feature_views:
        nfeat = sum(len(v) for v in fv.selects.values())
        print(f"    {fv.name}  serving_keys={fv.serving_keys}  ({len(fv.selects)} groups, {nfeat} features)")
        q = f"{fv.base_fg}.select({_short_select(fv.selects.get(fv.base_fg, []))})"
        for j in fv.joins:
            pfx = f", prefix={j.prefix!r}" if j.prefix else ""
            q += f"\n            .join({j.right_fg}.select({_short_select(fv.selects.get(j.right_fg, []))}), on={j.on}{pfx})"
        print(f"        query: {q}")
        for w in fv.warnings:
            print(f"      ! {w.kind}: {w.message}")

    warns = plan.all_warnings()
    print(f"\nwarnings ({len(warns)} total)")
    for w in warns:
        print(f"  [{w.kind}] {w.obj}: {w.message}")

    print("\ndry run, nothing written to Hopsworks.")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="import-feast",
        description="Replay a Feast feature repo into Hopsworks. Slice 0: print the migration plan (dry run).",
    )
    ap.add_argument("repo", help="path to a Feast feature repo (a directory with feature_store.yaml)")
    ap.add_argument("--dry-run", action="store_true", default=True, help="print the plan without writing (the only mode in slice 0)")
    args = ap.parse_args(argv)

    try:
        store = _load_store(args.repo)
    except Exception as e:
        print(f"error: could not load Feast repo at {args.repo}: {e}", file=sys.stderr)
        return 2

    plan = build_plan(store, args.repo)
    print_plan(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

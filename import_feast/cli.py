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


def _cmd_plan(args) -> int:
    from . import plan as plan_mod

    try:
        store = _load_store(args.repo)
    except Exception as e:
        print(f"error: could not load Feast repo at {args.repo}: {e}", file=sys.stderr)
        return 2
    plan = build_plan(store, args.repo)
    print_plan(plan)
    if args.out:
        plan_mod.dump(plan, args.out)
        print(f"\nplan written to {args.out} (run: import-feast execute {args.out} ...)")
    return 0


def _cmd_execute(args) -> int:
    import os

    from . import plan as plan_mod
    from .executor import execute

    api_key = args.api_key or (open(args.api_key_file).read().strip() if args.api_key_file else os.environ.get("HOPSWORKS_API_KEY"))
    if not api_key:
        print("error: no API key (pass --api-key, --api-key-file, or set HOPSWORKS_API_KEY)", file=sys.stderr)
        return 2
    plan = plan_mod.load(args.plan)
    execute(plan, host=args.host, port=args.port, project=args.project, api_key=api_key, no_statistics=args.no_statistics)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="import-feast",
        description="Replay a Feast feature repo into Hopsworks feature groups and feature views.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="read a Feast repo and print (optionally save) the migration plan. Needs the feast package.")
    p.add_argument("repo", help="path to a Feast feature repo (a directory with feature_store.yaml)")
    p.add_argument("-o", "--out", help="save the plan as JSON for the executor")
    p.set_defaults(func=_cmd_plan)

    e = sub.add_parser("execute", help="run a saved plan against Hopsworks. Needs hsfs, not feast.")
    e.add_argument("plan", help="a plan JSON produced by 'import-feast plan -o'")
    e.add_argument("--host", required=True)
    e.add_argument("--port", type=int, default=443)
    e.add_argument("--project", required=True)
    e.add_argument("--api-key")
    e.add_argument("--api-key-file")
    e.add_argument("--no-statistics", action="store_true", help="disable FG statistics jobs (lighter on the cluster)")
    e.set_defaults(func=_cmd_execute)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

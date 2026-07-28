"""Migration plan model. A plan is what the bridge would do to replay a Feast repo
into Hopsworks: storage connectors, feature groups (with a backfill), feature views.
The dry-run planner builds and prints it; the executor (later slice) runs it."""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Warning:
    obj: str  # feast object the warning is about
    kind: str  # ttl | udf | stream | credentials | dedup | type | request | unsupported
    message: str


@dataclass
class ConnectorOp:
    name: str
    connector_type: str  # snowflake | bigquery | redshift | s3 | kafka | jdbc ...
    for_source: str
    warnings: list[Warning] = field(default_factory=list)


@dataclass
class Backfill:
    kind: str  # "file" (read + insert into cached FG) | "external" (lazy, external FG)
    ref: str  # path, or table/query
    est_rows: Optional[int] = None
    field_mapping: dict = field(default_factory=dict)  # source column -> feature name


@dataclass
class FeatureGroupOp:
    name: str
    version: int
    primary_key: list[str]
    event_time: Optional[str]
    online_enabled: bool
    features: list[tuple[str, str]]  # (feature_name, hopsworks_type)
    external: bool  # external FG (lazy) vs cached FG (+ backfill)
    backfill: Optional[Backfill]
    ttl: Optional[str] = None
    warnings: list[Warning] = field(default_factory=list)


@dataclass
class Join:
    right_fg: str
    on: list[str]
    prefix: Optional[str]


@dataclass
class FeatureViewOp:
    name: str
    base_fg: str
    selects: dict[str, list[str]]  # fg_name -> selected feature names
    joins: list[Join]
    serving_keys: list[str]
    warnings: list[Warning] = field(default_factory=list)


@dataclass
class MigrationPlan:
    project: str
    repo_path: str
    connectors: list[ConnectorOp] = field(default_factory=list)
    feature_groups: list[FeatureGroupOp] = field(default_factory=list)
    feature_views: list[FeatureViewOp] = field(default_factory=list)
    warnings: list[Warning] = field(default_factory=list)  # global (unsupported objects)
    stats: dict = field(default_factory=dict)

    def all_warnings(self) -> list[Warning]:
        w = list(self.warnings)
        for c in self.connectors:
            w += c.warnings
        for fg in self.feature_groups:
            w += fg.warnings
        for fv in self.feature_views:
            w += fv.warnings
        return w


def dump(plan: MigrationPlan, path: str) -> None:
    """Serialize a plan to JSON. The plan is the interface between the Feast reader
    (needs the feast package) and the Hopsworks executor (needs hsfs); the two have
    conflicting dependencies and run in separate environments."""
    with open(path, "w") as f:
        json.dump(dataclasses.asdict(plan), f, indent=2)


def load(path: str) -> dict:
    with open(path) as f:
        return json.load(f)

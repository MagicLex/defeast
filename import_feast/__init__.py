"""import-feast: one-shot bridge that replays a Feast repo into Hopsworks feature groups
and feature views. Slice 0 is the dry-run planner (reader + mapper); later slices add the
executor (writer + data backfill). See docs/import-feast-scoping.md."""

from .mapper import build_plan
from .plan import MigrationPlan

__all__ = ["build_plan", "MigrationPlan"]

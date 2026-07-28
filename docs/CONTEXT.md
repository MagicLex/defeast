# Project Glossary

Shared language for this project. The agent (and new humans) read this to decode jargon consistently. Add a term when it appears in conversation more than twice.

## Terms

**Feature Group (FG)**
Hopsworks unit of feature storage and compute. Has a primary key, an event time, an online flag, and a set of typed features. Data is inserted into it. Cached FGs materialize their data; external FGs read from a storage connector.

**Feature View (Hopsworks)**
A query over one or more feature groups (select plus join) used for serving and training. Serving keys come from the joined groups' primary keys. This is what the app calls `get_feature_vector` against.

**Feature View (Feast)**
A Feast definition binding a schema to a data source. It maps to a Hopsworks feature group, not a Hopsworks feature view. See Flagged ambiguities.

**Feature Service (Feast)**
A Feast selection of features across feature views for one model. It maps to a Hopsworks feature view. See Flagged ambiguities.

**Entity**
The join key of a feature record. In Feast a first-class object; in Hopsworks it dissolves into the primary-key columns of a feature group.

**Online store / Offline store**
Online is the low-latency key-value serving store (Redis for Feast, RonDB for Hopsworks). Offline is the historical store for training data (parquet or a warehouse for Feast, Hudi or Delta for Hopsworks).

**Point-in-time (PIT)**
Joining features as of a label's event time so no future value leaks into training. Both stores do it; the benchmark verified neither leaks.

**Backfill**
Loading a Feast source's data into a Hopsworks feature group during migration. The bridge reads the FileSource parquet and inserts it.

**Plan / Execute**
The two bridge steps. `plan` reads the Feast repo and produces a JSON migration plan. `execute` runs that plan against Hopsworks. The plan is the interface between them.

**RonDB**
Hopsworks online store, the key-value engine behind `get_feature_vector`.

**Arrow Flight**
Hopsworks Python engine's offline query service (DuckDB-backed). Fast for moderate data, hits a temp-directory limit on very large joins where the Spark engine takes over.

## Relationships

- A **Feast FeatureView** maps to one **Hopsworks FeatureGroup** (plus a serving FeatureView).
- A **Feast FeatureService** maps to one **Hopsworks FeatureView** whose query joins the groups.
- A **FeatureGroup** holds many features; a **FeatureView** selects features across many groups.
- An **Entity** is a first-class Feast object; in Hopsworks it is the primary-key column set of a feature group.

## Flagged ambiguities

- **"Feature View" means different things in Feast and Hopsworks.** A Feast FeatureView is a schema over a source and maps to a Hopsworks FeatureGroup. A Feast FeatureService maps to a Hopsworks FeatureView. Always qualify which store when the term is loose. The bridge's mapper encodes this mapping.
- **"Batch" was ambiguous.** In this project it settled on offline training-data retrieval (`get_historical_features` vs `get_batch_data`), not online batch requests and not materialization.

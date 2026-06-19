# Geotech AI — Graph Schema v3

Modelled on the real Maryvale investigation data (pile tests, DPSH, boreholes,
test pits, lab + aggressivity + thermal testing). All locations and tests live
inside a `Zone`; every `Zone` lives inside a `Site`.

Units are documented per property below. Neo4j does not enforce units — store the
value in the stated unit and keep it consistent at ingestion.

## Hierarchy & one design change

`Site` → `Zone` → location nodes → test nodes.

The one change from the supplied layout: `GroundModel`'s `Soil 1 … Soil n` flat
fields become a **one-to-many** — a `GroundModel` has many ordered `GroundLayer`
nodes, each pointing to a shared `SoilType`. This lets a profile have any number
of layers (the 2-layer `BH02` vs the 4-layer `SS BH01`) and makes per-layer
queries possible, instead of fixed `Soil1/Soil2/…` columns.

---

## Nodes

### Site
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | `SITE-MARYVALE` |
| name | string | | |
| address | string | | optional |
| coordinate_system | string | | e.g. `GDA2020 MGA Zone 55` |

### Zone  (block / PCU)
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | `ZONE-1.1` |
| name | string | | |
| pre_drill_decision | string | | `Pre-Drill` \| `Driven` (block-level) |
| trackers_4string / _3string / _2string | int | | optional, from pre-drill sheet |

### PileTestLocation
A pile that was tested/installed, spatially located.
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| driving_type | string | `Driven` \| `PreDrilled` |
| easting | float | |
| northing | float | |
| reduced_level | float | mAHD |
| designer | string | tracker maker (GameChange/NEXTracker) |
| section_type | string | steel section, e.g. `150UB18` |
| target_depth | float | m |
| achieved_embedment | float | m |
| drive_time | float | min |
| driving_rate | float | m/s |

### PileTest  (container)
One per `PileTestLocation`; holds the overall result and the three typed sub-tests.
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| section_type | string | steel section |
| passed | bool | overall |

### TensionPileTest  — child of PileTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| uplift_applied_force | float | kN |
| uplift_max_deflection | float | mm |
| max_load_proportion_ed | float | % of Ed |

### LateralPileTest  — child of PileTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| max_applied_force | float | kN |
| max_deflection_top | float | mm |
| load_max | float | kN |
| max_load_proportion_ed | float | % of Ed |

### CompressionPileTest  — child of PileTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| max_applied_force | float | kN |
| max_deflection | float | mm |
| max_load_proportion_ed | float | % of Ed |

### DPSHTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| easting | float | |
| northing | float | |
| refusal_depth | float | m |

### BoreHole
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | full label, e.g. `BH02`, `SS-BH02` |
| zone_id | string | | FK -> Zone |
| ground_model_id | string | | FK -> GroundModel |
| series | string | | `BH` \| `SS-BH` (shallow grid vs deep SPT) |
| elevation | float | mAHD | optional |
| total_depth | float | m | optional |
| groundwater_depth | float | m | optional, null if none |

### TestPit
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | |
| zone_id | string | | FK -> Zone |
| ground_model_id | string | | FK -> GroundModel |
| elevation | float | mAHD | optional |
| total_depth | float | m | optional |

### SoilType  (material — shared reference vocabulary)
| property | type | notes |
|---|---|---|
| unit_no | string (unique) | the key, e.g. `4D` |
| origin | string | e.g. `bedrock`, `residual`, `alluvial` |
| unit_name | string | material name, e.g. `Andesite` |
| description | string | full description |

### GroundModel
| property | type | notes |
|---|---|---|
| id | string (unique) | one per BoreHole / TestPit; linked from the hole's `ground_model_id` |

### GroundLayer
A depth band within a GroundModel. A layer can contain **several** soil types —
express that as one row per (layer, soil) sharing the same layer `id`, each with a
different `soil_unit_no`; the upsert MERGEs the SoilType by `unit_no` and accumulates
the `OF_MATERIAL` edges, so the relationship is always created on layer-add.
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | layer id, e.g. `A1` |
| ground_model_id | string | | FK -> GroundModel |
| soil_unit_no | string | | FK -> SoilType (matched on `unit_no`); repeat rows for multiple soils |
| start_depth | float | mbgl | |
| end_depth | float | mbgl | |

### ThermalResistivityTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| depth | float | m |
| thermal_reading | float | W/mK |
| r_value | float | °C·cm/W |

### LaboratoryTest
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| top_depth | float | m |
| bottom_depth | float | m |
| moisture_content | float | % |
| liquid_limit | float | % |
| plastic_limit | float | % |
| plasticity_index | float | % |
| linear_shrinkage | float | % |
| emerson_class | int | |
| iss | float | % per ΔpF |
| gravel | float | % |
| sand | float | % |
| fines | float | % |
| compaction_mdd | float | t/m³ |
| compaction_omc | float | % |
| cbr_4day_2_5mm | int | |
| cbr_swell | float | % |

### SoilAggressivity
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| depth | float | mbgl |
| ph | float | |
| sulfate | float | ppm |
| chlorides | float | ppm |
| resistivity | float | Ω·cm |
| exposure_class_concrete | string | |
| exposure_class_steel | string | |

---

## Relationships

| relationship | from -> to |
|---|---|
| `HAS_ZONE` | Site -> Zone |
| `LOCATED_IN` | PileTestLocation -> Zone |
| `LOCATED_IN` | DPSHTest -> Zone |
| `LOCATED_IN` | BoreHole -> Zone |
| `LOCATED_IN` | TestPit -> Zone |
| `HAS_TEST` | PileTestLocation -> PileTest |
| `HAS_TENSION_TEST` | PileTest -> TensionPileTest |
| `HAS_LATERAL_TEST` | PileTest -> LateralPileTest |
| `HAS_COMPRESSION_TEST` | PileTest -> CompressionPileTest |
| `HAS_GROUND_MODEL` | BoreHole -> GroundModel |
| `HAS_GROUND_MODEL` | TestPit -> GroundModel |
| `HAS_LAYER` | GroundModel -> GroundLayer |
| `OF_MATERIAL` | GroundLayer -> SoilType |
| `HAS_THERMAL_TEST` | TestPit -> ThermalResistivityTest |
| `HAS_LAB_TEST` | BoreHole \| TestPit -> LaboratoryTest |
| `OF_MATERIAL` | LaboratoryTest -> SoilType (material encountered) |
| `HAS_AGGRESSIVITY_TEST` | BoreHole \| TestPit -> SoilAggressivity |

`LaboratoryTest`, `SoilAggressivity`, and `ThermalResistivityTest` attach to
either a `BoreHole` or a `TestPit`. To match them uniformly you can also stamp a
shared label `:InvestigationLocation` on both BoreHole and TestPit nodes (Neo4j
supports multiple labels) and match `(:InvestigationLocation)-[:HAS_LAB_TEST]->`.

---

## Mapping from earlier schema

| earlier | v3 | note |
|---|---|---|
| `Pile` | `PileTestLocation` | renamed + real fields (drive_time, driving_rate, driving_type) |
| `PileLoadTest` / `LoadTest` | `PileTest` | typed: tension/lateral/compression, % of Ed, passed |
| `InvestigationPoint` (DPSH) | `DPSHTest` | |
| `InvestigationPoint` (BH/TP) | `BoreHole`, `TestPit` | split by method, each with a GroundModel |
| `SoilLayer` / `GeotechUnit` | `SoilType` + `GroundLayer` | material vocab vs per-layer occurrence |
| - | `LaboratoryTest`, `SoilAggressivity`, `ThermalResistivityTest` | new, from the lab/GIR reports |

Earlier labels keep their constraints (legacy block in `schema.py`) so existing
loaded data still validates during the transition.

---

## Consequences for the rest of the app

- Queries / routes / parsers built against `Pile` / `InvestigationPoint` target
  the old labels. They need updating to `PileTestLocation` / `BoreHole` /
  `TestPit` / `PileTest` etc. before the v3 model is populated end to end.
- The PLT parser maps cleanly onto `PileTestLocation` (coords, section,
  embedment) + `PileTest` (the compression/tension/lateral result tables).
- Borehole logs populate `BoreHole` -> `GroundModel` -> `GroundLayer` +
  `LaboratoryTest`, but they are scanned field copies — OCR + manual structuring,
  not a clean table parse.
- ML target stays: predict `Zone.pre_drill_decision` / pile refusal
  (`achieved_embedment < target_depth`) from DPSH refusal depth, ground model,
  and lab/aggressivity features.
# Geotech AI — Graph Schema v3

All locations and tests live
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

### PileTest
One per test type on a `PileTestLocation` (a location has up to three).
| property | type | unit |
|---|---|---|
| id | string (unique) | |
| test_type | string | `tension` \| `lateral` \| `compression` |
| max_applied_force | float | kN |
| max_deflection | float | mm |
| load_max | float | kN (lateral; optional otherwise) |
| max_load_proportion_ed | float | % of design action effect Ed |
| passed | bool | |

> Modelled as one node per type (not three labels) so queries like "all failed
> tests" stay simple. `tension` uses *uplift* applied force/deflection; the field
> names above are the unified equivalents.

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
| series | string | | `BH` \| `SS-BH` (shallow grid vs deep SPT) |
| elevation | float | mAHD | optional |
| total_depth | float | m | optional |
| groundwater_depth | float | m | optional, null if none |

### TestPit
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | |
| elevation | float | mAHD | optional |
| total_depth | float | m | optional |

### SoilType  (material — shared reference vocabulary)
| property | type | notes |
|---|---|---|
| unit_name | string (unique) | the key, e.g. `CH`, `CI`, `XW Rock` |
| description | string | full USCS description |

### GroundModel
| property | type | notes |
|---|---|---|
| id | string (unique) | one per BoreHole / TestPit |

### GroundLayer
| property | type | unit | notes |
|---|---|---|---|
| id | string (unique) | | `<model>-L<n>` |
| order | int | | layer sequence from surface (1, 2, …) |
| start_depth | float | mbgl | |
| end_depth | float | mbgl | |
| condition | string | | `Firm` \| `Stiff` \| `VeryStiff` \| `Hard` \| `Dense` \| `VeryDense` |

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
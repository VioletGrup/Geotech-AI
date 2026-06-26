# Geotech AI — Spreadsheet Input Schema (v4)

## Legend
- `*` = compulsory input  
- `+` = primary key  
- `{relation}` = graph relationship  
- Derived IDs should be generated deterministically if not provided  

---

## site

| field | notes |
|------|------|
| id * + | unique site ID |
| name | |
| address | |
| coordinate_system | |

---

## zone

| field | notes |
|------|------|
| id + | order 1→ within site if not given |
| site_id * | {HAS_ZONE ← site} |
| name | |
| pile_drilling | [Pre-Drill, Driven, None, Other] *(None = to be predicted)* |
| trackers_4_string | int |
| trackers_3_string | int |
| trackers_2_string | int |

---

## pile-test-location

| field | notes |
|------|------|
| id + | derive from zone_id if not given |
| zone_id * | {LOCATED_IN → zone} |
| driving_type | [Driven, PreDrilled, Other] |
| easting | |
| northing | |
| reduced_level | |
| designer | |
| section_type | |
| target_depth | |
| achieved_embedment | |
| driving_time | minute:seconds format |
| driving_rate | |

---

## pile-test

| field | notes |
|------|------|
| id + | derive from location if not given |
| pile_location * | {HAS_TEST ← pile-test-location} |
| section_type | |
| passed | [true, false, undecided] |

---

## tension-test

| field | notes |
|------|------|
| id + | derive from pile-test if not given |
| pile_test_id * | {HAS_TENSION_TEST ← pile-test} |
| uplift_applied_force | |
| uplift_max_deflection | |
| max_load_proportion_ed | |

---

## lateral-test

| field | notes |
|------|------|
| id + | derive from pile-test if not given |
| pile_test_id * | {HAS_LATERAL_TEST ← pile-test} |
| max_applied_force | |
| max_deflection_top | |
| max_deflection_bottom | |
| load_max | |
| max_load_proportion_ed | |

---

## compression-test

| field | notes |
|------|------|
| id + | derive from pile-test if not given |
| pile_test_id * | {HAS_COMPRESSION_TEST ← pile-test} |
| max_applied_force | |
| max_deflection | |
| max_load_proportion_ed | |

---

## dpsh

| field | notes |
|------|------|
| id + | derive from zone_id if not given |
| zone_id * | {LOCATED_IN → zone} |
| easting | |
| northing | |
| refusal_depth | |

---

## borehole

| field | notes |
|------|------|
| id + | derive from zone_id if not given |
| zone_id * | {LOCATED_IN → zone} |
| easting ||
| northing ||
| ground_model_id | |
| elevation | |
| total_depth | also referred to as termination depth |
| groundwater_depth | |

---

## testpit

| field | notes |
|------|------|
| id + | derive from zone_id if not given |
| zone_id * | {LOCATED_IN → zone} |
| easting ||
| northing ||
| ground_model_id | |
| elevation | |
| total_depth | |

---

## soil-type

| field | notes |
|------|------|
| unit_no * + | must be globally unique |
| origin | |
| unit_name | if duplicate (origin + unit_name), prompt reuse |
| description | |

---

## ground-model

| field | notes |
|------|------|
| id * + | |

---

## ground-layer

| field | notes |
|------|------|
| id + | derive from ground-model if not given |
| ground_model_id * | {HAS_LAYER ← ground-model} |
| soil_unit_no * | {OF_MATERIAL → soil-type} |
| start_depth | |
| end_depth | |

---

## thermal-test

| field | notes |
|------|------|
| id + | derive from testpit_id if not given |
| testpit_id * | {HAS_THERMAL_TEST ← testpit} |
| depth | |
| thermal_reading | |
| r_value | |

---

## lab-test

| field | notes |
|------|------|
| id + | derive from location_id if not given |
| location_id * | {HAS_LAB_TEST ← testpit / borehole} |
| top_depth | |
| bottom_depth | |
| moisture_content | |
| liquid_limit | |
| plastic_limit | |
| plasticity_index | |
| linear_shrinkage | |
| emerson_class | |
| iss | |
| gravel | |
| sand | |
| fines | |
| compaction_mdd | |
| compaction_omc | |
| cbr_4day_2_5_mm | |
| cbr_swell | |

---

## aggressivity

| field | notes |
|------|------|
| id + | derive from location_id if not given |
| location_id * | {HAS_AGGRESSIVITY_TEST ← testpit / borehole} |
| depth | |
| ph | |
| sulfate | |
| chlorides | |
| resistivity | |
| exposure_class_concrete | |
| exposure_class_steel | |
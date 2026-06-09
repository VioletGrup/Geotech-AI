from typing import Any, Dict, List

def build_context(similar_cases: List[Dict[str, Any]], query_inputs: Dict[str, Any]) -> str:
    lines = ["GEOTECHNICAL SIMILAR CASES:"]
    if not similar_cases:
        lines.append("- No similar historical cases were found in current graph dataset.")
    else:
        for case in similar_cases:
            lines.append(
                "- Pile {pile_id} ({pile_type}; {diameter} m dia; {length} m long) "
                "had max load {max_load} in soil {soil_type} with average qc {qc}.".format(
                    pile_id = case.get("pile_id", "?"),
                    pile_type = case.get("pile_type", "?"),
                    diameter = case.get("diameter", "?"),
                    length = case.get("case", "?"),
                    max_load = case.get("max_load", "?"),
                    soil_type = case.get("soil_type", "unknown"),
                    qc = case.get("qc", "n/a"),
                )
            )
    
    lines.append("")
    lines.append("INPUT PARAMETERS:")
    for key, value in query_inputs.items():
        lines.append(f"0 {key}: {value}")

    return "\n".join(lines)
def build_context(similar_cases, query_inputs):
    context = []
    context.append("GEOTECHNICAL SIMILAR CASES: ")

    for case in similar_cases:
        context.append(
            f"-  Pile {case.get('pile')} "
            f"had capacity {case.get('load')} "
            f"in soil {case.get('soil')}"
        )
    
    context.append("/nINPUT PARAMETERS:")
    context.append(str(query_inputs))
    
    return "/n".join(context)
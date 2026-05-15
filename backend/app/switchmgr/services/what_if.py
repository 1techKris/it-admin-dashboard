def simulate_link_failure(graph, source, target):
    """
    Remove an edge and recompute:
    - Connectivity
    - STP root (simple heuristic)
    """
    new_graph = {
        "nodes": graph["nodes"].copy(),
        "links": [l for l in graph["links"] 
                  if not (l["source"] == source and l["target"] == target 
                          or l["source"] == target and l["target"] == source)]
    }

    # Connectivity check
    def walk(start):
        seen = set([start])
        queue = [start]
        while queue:
            n = queue.pop(0)
            for l in new_graph["links"]:
                if l["source"] == n and l["target"] not in seen:
                    seen.add(l["target"])
                    queue.append(l["target"])
                if l["target"] == n and l["source"] not in seen:
                    seen.add(l["source"])
                    queue.append(l["source"])
        return seen

    components = []
    for node in graph["nodes"]:
        ip = node["id"]
        if not any(ip in comp for comp in components):
            comp = walk(ip)
            components.append(comp)

    # STP root (simple: lowest IP in biggest component)
    largest = max(components, key=len)
    stp_root = sorted(largest)[0]

    return {
        "components": [list(c) for c in components],
        "stp_root": stp_root,
        "remaining_links": new_graph["links"],
    }
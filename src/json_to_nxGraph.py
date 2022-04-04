import networkx as nx
import json

def get_id(dic, use_name = False):
    if use_name == True:
        return dic["name"]
    else:
        return str(dic["id"])

def json_to_nxGraph(filename, prefix):
    USE_NAME = True
    with open(filename) as f:
        p4json = json.load(f)

    pipelines = p4json["pipelines"]
    for p in pipelines:
        if p["name"] == "ingress":
            ingress = p
        if p["name"] == "egress":
            egress = p

    graph = nx.MultiDiGraph()
    # the root of the graph
    graph.add_nodes_from([(prefix+"r", {'myId':prefix+"r", 'name':'r'})])
    # the sink of the graph
    graph.add_nodes_from([(prefix+"s", {'myId':prefix+"s", 'name':'s'})])

    name2id = {None: prefix+"s"}
    actionId2Name = {}

    # process the nodes
    for a in p4json["actions"]:
        actionId2Name[a["id"]] = a["name"]

    for t in ingress["tables"]:
        t["myId"] = prefix+"t%s"%get_id(t, USE_NAME)
        graph.add_nodes_from([(t["myId"], t)])
        name2id[t["name"]] = t["myId"]

    for c in ingress["conditionals"]:
        c["myId"] = prefix+"c%s"%get_id(c, USE_NAME)
        graph.add_nodes_from([(c["myId"], c)])
        name2id[c["name"]] = c["myId"]

    # TODO: Should we throw an error if we encounter action_calls?
    if "action_calls" in ingress:
        for a in ingress["action_calls"]:
            aid = prefix+"a%s"%get_id(a, USE_NAME)
            graph.add_nodes_from([(aid, {"myId":aid, "name":actionId2Name[a["action_id"]]})])
            name2id[a["name"]] = aid

    # process the edges
    graph.add_edges_from([(prefix+"r", name2id[ingress["init_table"]], {'type':'b_next'})]) # base_default_next
    for t in ingress["tables"]:
        # normally it has only one next table
        nextId = name2id[t["base_default_next"]]
        graph.add_edges_from([(name2id[t["name"]], nextId, {'type':'b_next'})])

        for nt in t["next_tables"]:
            if t["next_tables"][nt] != t["base_default_next"]:
                # TODO: support __HIT__, __MISS__, and action pointers
                raise NotImplementedError("Does not support multiple next table pointers for a table!")

    for c in ingress["conditionals"]:
        graph.add_edges_from([(name2id[c["name"]], name2id[c["true_next"]], {'type':'t_next'}),
                              (name2id[c["name"]], name2id[c["false_next"]], {'type':'f_next'})])

    # TODO: same with the node, should we throw an error here?
    if "action_calls" in ingress:
        for a in ingress["action_calls"]:
            graph.add_edges_from([(name2id[c["name"]], name2id[c["next_node"]], {'type':'b_next'})])

    return graph

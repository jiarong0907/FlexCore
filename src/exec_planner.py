import networkx as nx
import Logger as Logger
from planner import Planner

class ExecPlanner(Planner):
    def __init__(self, inbuilder):
        super().__init__(inbuilder)
        self.inbuilder = inbuilder

    def reconfig(self, rdg_o, rdg_n, dump_path):
        '''The main function of the alg
        Args:
            rdg_o (networkx object): The networkx graph of the old problem.
            rdg_o (networkx object): networkx graph of the new problem.
        Return:
            g (list(list)): A list of reconfig plans.
        '''

        # Compute the MCS and color the nodes and edges
        rdg_s = self.graph_tool.GetMCS(rdg_o, rdg_n, self.inbuilder)
        # Enhance it with TEs
        rdg_te = self.graph_tool.EnhanceWithTEs(rdg_s)

        plan = self.compute(rdg_te)
        return self.get_plan_commands(plan, dump_path)


    def compute(self, rdg_te):
        '''Compute reconfig plans for execution consistency
        This can be achieved by using colored DFS and topological sort.
        Args:
            rdg_te (networkx object): The MCS enhanced with TEs
        Return:
            g (list(list)): A list of reconfig plans.
        '''

        # get the key for an edge, which is used to delete an edge in a MultiDiGraph
        def find_edge_idx(graph, target):
            candidates = graph.get_edge_data(target[0], target[1])
            assert (candidates != None)

            for key in candidates.keys():
                if candidates[key]['type'] == target[2]['type']:
                    return key
            return -1

        # get all red and green edges
        green_edges = []
        red_edges = []
        for e in rdg_te.edges(data=True):
            ecolor = e[2]['color']
            if ecolor == 'green':
                idx = find_edge_idx (rdg_te, e)
                green_edges.append((e[0], e[1], idx))
            elif ecolor == 'red':
                idx = find_edge_idx (rdg_te, e)
                red_edges.append((e[0], e[1], idx))

        # we remove green edges from rdg_te to get the colored old graph
        g_red = rdg_te.copy()
        for u,v,idx in green_edges:
            g_red.remove_edge(u, v, idx)
        g_red.remove_nodes_from(list(nx.isolates(g_red)))


        # we remove red edges from rdg_te to get the colored new graph
        g_green = rdg_te.copy()
        for u,v,idx in red_edges:
            g_green.remove_edge(u, v, idx)
        g_green.remove_nodes_from(list(nx.isolates(g_green)))

        # get all TEs
        TEs = []
        for node in rdg_te.nodes(data=True):
            if node[1]['color'] == 'blue':
                if node not in TEs:
                    TEs.append(node[0])
                else:
                    Logger.DEBUG("Found a duplicated TE in the graph: "+str(node))
                    assert(0)

        Logger.INFO("The TEs are "+str(TEs))
        Logger.INFO("The number of TEs are "+str(len(TEs)))

        # get constraints: we start from a TE and do colored DFS
        C = set()
        for i in TEs:
            for j in TEs:
                if i != j:
                    # reachable in the old graph
                    if nx.has_path(g_red, source=str(i), target=str(j)):
                        C.add((i, j, '<='))
                    # reachable in the new graph
                    if nx.has_path(g_green, source=str(i), target=str(j)):
                        C.add((i, j, '>='))

        Logger.INFO("The constraints are "+str(C))

        # build the depedency graph
        dag = self.get_depedency_dag(TEs, C)

        # TODO: add sort back
        # get one topo sort solutions.
        one_sol = next(nx.all_topological_sorts(dag))
        # groupping
        one_plan = []
        for i in range(len(one_sol)):
            # for each group in this solution
            TEs = one_sol[i].split(",")
            new_group = []
            for TE in TEs:
                new_group.append(TE.strip())
                visited = set()
                visited = self.colored_dfs(rdg_te, TE.strip(), visited)

                for op in visited:
                    if op not in new_group:
                        new_group.append(op)
            one_plan.append(new_group)

        # we need to deduplciate the op for shared red and green edges
        one_plan = self.deduplicate(one_plan, rdg_te)
        one_plan = self.get_atomic_plan(rdg_te, one_plan)
        msg=""
        for step in one_plan:
            msg += str(step)+"\n"
        msg = msg[:-1]
        Logger.CRITICAL("The best reconfig plan is : \n"+msg)

        return one_plan


    def deduplicate(self, groups, rdg_te):
        '''Deduplicate ops for shared red and green nodes
        Args:
            rdg_te (networkx object): The MCS enhanced with TEs
            groups (list(list)): The origianl plans might have duplications
        Return:
            groups (list(list)): The final plans without duplications.
        '''

        # we compare each group combination
        for i in range(len(groups)-1):
            for j in range(i+1, len(groups)):
                intersect = set(groups[i]).intersection(set(groups[j]))
                if len(intersect) == 0:
                    continue
                else: # has duplications
                    for node in list(intersect):
                        vcolor = rdg_te.nodes[node].get('color')
                        if vcolor == 'red':
                            # red should be done by the last group, so we remove it from the previous one
                            groups[i].remove (node)
                        elif vcolor == 'green':
                            # red should be done by the first group, so we remove it from the later one
                            groups[j].remove (node)
                        else:
                            Logger.DEBUG("Cannot handle the node color: "+str(vcolor))
                            assert(0)
        return groups

    def get_depedency_dag(self, M, C):
        '''Construct the TE dependency graphs for topo sort in the next step.
        Args:
            M (list): A list of TEs
            C (list): Constraints between TEs
        Return:
            dag_scc (networkx object): A DiGraph object with merged TEs
        '''

        dag = nx.DiGraph(directed=True)
        for TE in M:
            dag.add_nodes_from([(TE, {'name':TE, 'color':'blue'})])

        for c in C:
            u = c[0]
            v = c[1]
            op = c[2]
            if op == '<=':
                dag.add_edges_from([(u, v,{'color':'blue'})])
            elif op == '>=':
                dag.add_edges_from([(v, u, {'color':'blue'})])
            elif op == '=':
                dag.add_edges_from([(v, u, {'color':'blue'})])
                dag.add_edges_from([(u, v, {'color':'blue'})])
            # handle progAtom at the beginning
            elif op == '=1':
                pass
            else:
                Logger.ERROR("Cannot solve constraint "+str(u)+" "+str(op)+" "+str(v))
                assert(0)

        # the new graph with merged TEs
        dag_scc = nx.DiGraph(directed=True)

        # node-scc_name mapping. used to create a new graph because we cannot iterate on a size-changed object
        n2scc_map = {}
        scc_list = list(nx.strongly_connected_components(dag))
        for scc in scc_list:
            name = ""
            for node in scc:
                name += node+", "
            name = name[:-2]
            # populate the mapping
            for node in scc:
                n2scc_map[node] = name

            dag_scc.add_nodes_from([(name, {'name':name, 'color':'blue'})])

        Logger.DEBUG("n2scc_map = "+str(n2scc_map))

        # an inner function to check whether two sccs should have an edge
        def check_scc_edge(uscc, vscc):
            for u in uscc:
                for v in vscc:
                    if (u, v) in dag.edges():
                        return True
            return False

        for uscc in scc_list:
            for vscc in scc_list:
                if uscc != vscc:
                    # check whether there is an edge
                    if check_scc_edge(uscc, vscc):
                        dag_scc.add_edges_from([(n2scc_map[list(uscc)[0]], n2scc_map[list(vscc)[0]], {'color':'blue'})])

        return dag_scc

    def colored_dfs(self, rdg_te, s, visited):
        '''DFS from a TE and stop when encounter a black node
        Args:
            rdg_te (networkx object): The MCS enhanced with TEs
            s (str): The source node--a TE
            visited (set): whether a node has been visited
        Return:
            visited (set): A set of nodes related to this TE.
        '''

        visited.add(s)
        out_edges = list(rdg_te.out_edges(s, data=True))
        for oe in out_edges:
            if oe[1] not in visited:
                vcolor = rdg_te.nodes[oe[1]].get('color')
                # we stop if the next node is black, blue is acutally not possible because it always follows a black node
                if vcolor == 'black' or vcolor == 'blue':
                    continue
                visited = self.colored_dfs(rdg_te, oe[1], visited)
        return visited
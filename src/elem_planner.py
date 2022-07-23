import networkx as nx
import Logger as Logger
from planner import Planner

class ElemPlanner(Planner):
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
        rdg_s = self.graph_tool.get_MCS(rdg_o, rdg_n, self.inbuilder)
        # Enhance it with TEs
        rdg_te = self.graph_tool.enhance_with_TEs(rdg_s)

        plan = self.compute(rdg_te)
        return self.get_plan_commands(plan, dump_path)

    def compute(self, rdg_te):
        '''Compute reconfig plans for element consistency
        This can be achieved by unioning researchable nodes in M.
        Args:
            rdg_te (networkx object): The MCS enhanced with TEs
        Return:
            g (list(list)): A list of reconfig plans.
        '''

        # Get all red/green/blue nodes
        M = list()
        for node in rdg_te.nodes(data=True):
            if node[1]['color'] != 'black':
                if node not in M:
                    M.append(node[0])
                else:
                    raise ValueError("Found a duplicated node in the graph: "+str(node))

        # init the union relation
        parent = {n: n for n in M}

        # if two nodes in M can reach from one to another, we merge them into one group
        for i in M:
            for j in M:
                if i != j and nx.has_path(rdg_te, source=str(i), target=str(j)):
                    self.union(parent, i, j)

        # get all groups by checking the union relation
        groups = dict()
        for key in parent:
            if parent[key] not in groups.keys():
                groups[parent[key]] = [key]
            else:
                groups[parent[key]].append(key)

        Logger.INFO("The number of groups is "+str(len(groups))+".\nThe groups are "+str(groups))

        sort = False
        ordered_plan = list()
        if sort:
            # TODO: add sort back
            pass
        else:
            for key in groups:
                ordered_plan.append(groups[key])

        Logger.DEBUG("Ordered plan: "+str(ordered_plan))

        # generate plans
        plan = self.get_atomic_plan(rdg_te, ordered_plan)
        msg=""
        for step in plan:
            msg += str(step)+"\n"
        msg = msg[:-1]
        Logger.CRITICAL("Its reconfig plan is : \n"+msg)
        return plan

    # A utility function to do union of two subsets
    def union(self, parent, x, y):
        pid = parent[x]
        qid = parent[y]

        for key in parent.keys():
            if parent[key] == pid:
                parent[key] = qid

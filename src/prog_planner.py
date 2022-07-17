import Logger as Logger
from planner import Planner

class ProgPlanner(Planner):
    def __init__(self, inbuilder):
        super().__init__(inbuilder)
        self.inbuilder = inbuilder
        self.enable_action_ptr = False

    def set_enable_action_ptr(self, flag):
        self.enable_action_ptr = flag

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
        '''Compute reconfig plans for program consistency
        This can be achieved by merging all red/green/blue nodes into one group.
        Args:
            rdg_te (networkx object): The MCS enhanced with TEs
        Return:
            g (list(list)): A list of reconfig plans.
        '''

        # get all red/green/blue nodes
        M = []
        for node in rdg_te.nodes(data=True):
            if node[1]['color'] != 'black':
                if node not in M:
                    M.append(node[0])
                else:
                    Logger.DEBUG("Found a duplicated node in the graph: "+str(node))
                    assert(0)

        Logger.INFO("Get a solution: "+str(M))

        plan = self.get_atomic_plan(rdg_te, [M], self.enable_action_ptr)
        msg=""
        for step in plan:
            msg += str(step)+"\n"
        msg = msg[:-1]
        Logger.CRITICAL("Its reconfig plan is : \n"+msg)

        return plan


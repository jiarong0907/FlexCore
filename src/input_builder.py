import networkx as nx
from abc import ABCMeta, abstractmethod
import pickle

import Logger as Logger
import json_to_nxGraph as json_to_nxGraph

class InputBuilder:
    __metaclass__ = ABCMeta
    def __init__(self, path_old, path_new):
        self.path_old = path_old
        self.path_new = path_new

    @abstractmethod
    def build(self):
        pass

class GraphInputBuilder(InputBuilder):
    def __init__(self, path_old, path_new):
        super().__init__(path_old, path_new)
        self.path_old = path_old
        self.path_new = path_new

    def build(self):
        '''Call the alg by providing two txt files, this is usually used for testing
        Args:
            path_old (str): The path of the txt file of the old graph.
            path_new (str): The path of the txt file of the new graph.
        Return:
            reconfig() (list): A sequence of cmd of the optimal reconfig plan.
        '''
        rdg_o = self.build_graph_from_txt(self.path_old)
        rdg_n = self.build_graph_from_txt(self.path_new)

        Logger.DEBUG("The old graph nodes: "+str(rdg_o.nodes()))
        Logger.DEBUG("The old graph edges: "+str(rdg_o.edges()))
        Logger.DEBUG("The new graph nodes: "+str(rdg_n.nodes()))
        Logger.DEBUG("The new graph edges: "+str(rdg_n.edges()))

        return rdg_o, rdg_n


    def build_graph_from_txt(self, path):
        '''A helper function: Construct the networkx graph from txt files, this is usually used for testing
        Args:
            path (str): The path of the txt file.
        Return:
            g (networkx object): The MultiDiGraph built from the data in the txt file.
        '''

        mfile = open(path, 'r')

        g = nx.MultiDiGraph(directed=True)
        for line in mfile.readlines():
            element = line.split(',')
            u = element[0].strip()
            v = element[1].strip()
            t = element[2].strip() # edge type

            if not g.has_node(u):
                g.add_nodes_from([(u,{'name':u[3:], 'myId':u})])
            if not g.has_node(v):
                g.add_nodes_from([(v,{'name':v[3:], 'myId':v})])
            g.add_edges_from([(u, v, {'type':t})])

        return g

class JsonInputBuilder(InputBuilder):
    def __init__(self, path_old, path_new):
        super().__init__(path_old, path_new)
        self.path_old = path_old
        self.path_new = path_new

    def build(self):
        '''Call the alg by providing two json files, this is used for real P4 programs
        Args:
            path_old (str): The path of the json file of the old program.
            path_new (str): The path of the json file of the new program.
        Return:
            reconfig() (list): A sequence of cmd of the optimal reconfig plan.
        '''

        rdg_o = self.get_rooted_directed_graph(self.path_old, "g1_")
        rdg_n = self.get_rooted_directed_graph(self.path_new, "g2_")
        Logger.DEBUG("The old graph has "+str(len(rdg_o.nodes()))+" node.")
        Logger.DEBUG("The old graph nodes: "+str(rdg_o.nodes()))
        Logger.DEBUG("The old graph has "+str(len(rdg_o.edges()))+" edges.")
        Logger.DEBUG("The old graph edges: "+str(rdg_o.edges(data=True)))
        Logger.DEBUG("The new graph nodes: "+str(rdg_n.nodes()))
        Logger.DEBUG("The new graph edges: "+str(rdg_n.edges(data=True)))

        return rdg_o, rdg_n

    def get_rooted_directed_graph(self, prog_path, graph_prefix):
        '''Get the control flow graph based on the compiled json file
        Args:
            prog_path: The full path of the json file of which the graph will build on.
            graph_prefix: The prefix of the label of the node. Use to distinguish the old and the new graph elements.
        Return:
            A networkx graph object.
        '''
        return json_to_nxGraph.json_to_nxGraph(prog_path, graph_prefix)



class ObjInputBuilder(InputBuilder):
    def __init__(self, path_old, path_new):
        super().__init__(path_old, path_new)
        self.path_old = path_old
        self.path_new = path_new

    def build(self):
        '''Call the alg by providing two objection built from synthesizer output
        Args:
            obj_old (networkx object): The old graph object.
            obj_new (networkx object): The new graph object.
        Return:
            reconfig() (list): A sequence of cmd of the optimal reconfig plan.
        '''

        obj_old = pickle.load(open(self.path_old, 'rb'))
        obj_new = pickle.load(open(self.path_new, 'rb'))

        # add prefix for the old one
        g1_node_relabl = dict()
        for v, attr in obj_old.nodes(data=True):
            g1_node_relabl[v] = "g1_"+str(v)
            attr['myId'] = "g1_"+attr['myId']
        obj_old = nx.relabel_nodes(obj_old, g1_node_relabl)

        # add prefix for the new one
        g2_node_relabl = dict()
        for v, attr in obj_new.nodes(data=True):
            g2_node_relabl[v] = "g2_"+str(v)
            attr['myId'] = "g2_"+attr['myId']
        obj_new = nx.relabel_nodes(obj_new, g2_node_relabl)

        Logger.DEBUG("The old graph nodes: "+str(obj_old.nodes()))
        Logger.DEBUG("The old graph edges: "+str(obj_old.edges(data=True)))
        Logger.DEBUG("The new graph nodes: "+str(obj_new.nodes()))
        Logger.DEBUG("The new graph edges: "+str(obj_new.edges(data=True)))

        return obj_old, obj_new

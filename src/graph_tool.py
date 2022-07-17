import networkx as nx
import sys

import Logger as Logger
import matplotlib.pyplot as plt


class GraphTool:
    def __init__(self):
        self.alias = {
            'ingress_metadata.ifindex' : 'standard_metadata.ingress_port',
            'l2_metadata.lkp_pkt_type' : 'l2_metadata.lkp_pkt_type',
            'l2_metadata.lkp_mac_sa' : 'ethernet.srcAddr',
            'l2_metadata.lkp_mac_da' : 'ethernet.dstAddr',
            'l3_metadata.lkp_ip_ttl' : 'ipv4.ttl',
            'ipv4_metadata.lkp_ipv4_sa' : 'ipv4.srcAddr',
            'ipv4_metadata.lkp_ipv4_da' : 'ipv4.dstAddr',
            'l3_metadata.lkp_ip_ttl' : 'ipv6.hopLimit',
            'ipv6_metadata.lkp_ipv6_sa' : 'ipv6.srcAddr',
            'ipv6_metadata.lkp_ipv6_da' : 'ipv6.dstAddr',
        }

    def GetMCS(self, graph_old, graph_new, inbuilder):
        '''Construct the minimal common supergraph
        Args:
            graph_old: The networkx object of the old graph
            graph_new: The networkx object of the new graph
        Return:
            A networkx graph object.
        '''
        o2n_node_map = self.node_mapping(graph_old, graph_new, inbuilder)
        n2o_node_map = self.node_mapping(graph_new, graph_old, inbuilder)

        Logger.INFO("old to new node mapping: "+str(o2n_node_map))
        Logger.INFO("new to old node mapping: "+str(n2o_node_map))

        # use to store which table has been taken, to prevent two old tables use the same new table
        taken = dict()
        for nodes_myId_new in graph_new.nodes():
            taken[nodes_myId_new] = 0

        # check whether an old table can map to multiple new tables
        cn_map_o2n = dict() # common node mapping from old to new
        for key in o2n_node_map.keys():
            mapping = o2n_node_map[key]
            if len(mapping) > 1:
                Logger.DEBUG("The old table can map to multiple new tables. Need to handle specially!\n" + str(key) +"\n"+str(mapping))
                candidate = None
                for m in mapping:
                    if m[3:] == key[3:]:
                        candidate = m
                        break
                if candidate is not None:
                    if taken[candidate] == 0:
                        Logger.DEBUG("According to the table name, we choose: " + str(candidate))
                        cn_map_o2n[key]=[candidate]
                        taken[candidate] = 1
                    else:
                        Logger.DEBUG("We find one by name but it has been taken by others")
                        assert(0)
                else:
                    Logger.DEBUG("Cannot make a decision using table name, we regard this table as deleted.")

            elif len(mapping) == 1:
                if taken[mapping[0]] == 0:
                    cn_map_o2n[key]=mapping
                    taken[mapping[0]] = 1
                else:
                    Logger.DEBUG("Only one candidate but it has been taken by others")
                    # assert(0)

        # check whether muliple old tables map to one new table
        for key in n2o_node_map.keys():
            mapping = n2o_node_map[key]
            if len(mapping) > 1:
                Logger.DEBUG("The new table can map to multiple old tables. Need to handle specially!")
                # assert(0)

        Logger.INFO("Table mapping check done.")

        # rewrite cn_map_o2n as each key only has one value now
        tmp = dict()
        for key in cn_map_o2n.keys():
            assert (len(cn_map_o2n[key])==1)
            tmp[key] = cn_map_o2n[key][0]
        cn_map_o2n = tmp

        # double-check there is no shared nodes
        val_set = cn_map_o2n.values()
        assert(len(val_set)==len(set(val_set)))

        # make cn_map_n2o for convience
        cn_map_n2o = dict()
        for key in cn_map_o2n.keys():
            cn_map_n2o[cn_map_o2n[key]] = key

        # compute all deleted nodes
        deleted_nodes = []
        nodes_old = graph_old.nodes()
        for nodes_myId_old in nodes_old:
            if nodes_myId_old not in cn_map_o2n.keys():
                deleted_nodes.append(nodes_myId_old)

        Logger.DEBUG(cn_map_o2n.values())

        # compute all inserted nodes
        inserted_nodes = []
        nodes_new = graph_new.nodes()
        for nodes_myId_new in nodes_new:
            if nodes_myId_new not in list(cn_map_o2n.values()):
                inserted_nodes.append(nodes_myId_new)

        Logger.INFO("The number of common_nodes: "+str(len(cn_map_o2n)))
        Logger.INFO("common_nodes: "+str(cn_map_o2n))
        Logger.INFO("The number of deleted_nodes: "+str(len(deleted_nodes)))
        Logger.INFO("deleted_nodes: "+str(deleted_nodes))
        Logger.INFO("The number of inserted_nodes: "+str(len(inserted_nodes)))
        Logger.INFO("inserted_nodes: "+str(inserted_nodes))

        # build the MCS
        MCS = nx.MultiDiGraph(directed=True)
        for node in cn_map_o2n.keys():
            MCS.add_nodes_from([(node[3:], {'name':node[3:], 'color':'black'})]) # [3:] to remove the prefix

        for node in deleted_nodes:
            MCS.add_nodes_from([(node, {'name':node, 'color':'red'})])

        for node in inserted_nodes:
            MCS.add_nodes_from([(node, {'name':node, 'color':'green'})])

        # check whether an edge is in a graph
        def check_exist_edge(graph, u, v, etype):
            candidates = graph.get_edge_data(u, v)
            if candidates is None:
                return False

            for key in candidates:
                if etype == candidates[key]['type']:
                    return True
            return False

        # add edges
        for edge in graph_old.edges(data=True):
            edge_type = edge[2]['type']
            # There are four cases to consider
            # u and v are both common nodes
            if edge[0] in cn_map_o2n.keys() and edge[1] in cn_map_o2n.keys():
                u = edge[0][3:] # [3:] to remove the prefix
                v = edge[1][3:]
                # check whether the edge is in the new graph
                if check_exist_edge (graph_new, cn_map_o2n[edge[0]], cn_map_o2n[edge[1]], edge_type):
                    color = 'black'
                else:
                    color = 'red'
            # v is not in common nodes, so it must be a red edge
            elif edge[0] in cn_map_o2n.keys() and edge[1] not in cn_map_o2n.keys():
                assert(edge[1] in deleted_nodes)
                u = edge[0][3:]
                v = edge[1]
                color = 'red'
            # u is not in common nodes, so it must be a red edge
            elif edge[0] not in cn_map_o2n.keys() and edge[1] in cn_map_o2n.keys():
                assert(edge[0] in deleted_nodes)
                u = edge[0]
                v = edge[1][3:]
                color = 'red'
            # u is not in common nodes, so it must be a red edge
            elif edge[0] not in cn_map_o2n.keys() and edge[1] not in cn_map_o2n.keys():
                assert(edge[0] in deleted_nodes and edge[1] in deleted_nodes)
                u = edge[0]
                v = edge[1]
                color = 'red'
            else:
                assert(0)

            MCS.add_edges_from([(u, v,{'type':edge_type, 'color':color, 'isTE':False})])

        for edge in graph_new.edges(data=True):
            # edge type will be used to determine TEs
            edge_type = edge[2]['type']

            if edge[0] in cn_map_o2n.values() and edge[1] in cn_map_o2n.values():
                # We must translate the name back to that in the old graph, because the common table might have different name
                u = cn_map_n2o[edge[0]][3:] # [3:] to remove the prefix
                v = cn_map_n2o[edge[1]][3:]
                # check whether the edge is in the old graph
                if not check_exist_edge (graph_old, cn_map_n2o[edge[0]], cn_map_n2o[edge[1]], edge_type):
                    color = 'green'
                else:
                    continue # has been processed in the old edges.
            # v is not in common nodes, it must be in green
            elif edge[0] in cn_map_o2n.values() and edge[1] not in cn_map_o2n.values():
                assert(edge[1] in inserted_nodes)
                u = cn_map_n2o[edge[0]][3:]
                v = edge[1]
                color = 'green'
            # u is not in common nodes, it must be in green
            elif edge[0] not in cn_map_o2n.values() and edge[1] in cn_map_o2n.values():
                assert(edge[0] in inserted_nodes)
                u = edge[0]
                v = cn_map_n2o[edge[1]][3:]
                color = 'green'
            # u is not in common nodes, it must be in green
            elif edge[0] not in cn_map_o2n.values() and edge[1] not in cn_map_o2n.values():
                assert(edge[0] in inserted_nodes and edge[1] in inserted_nodes)
                u = edge[0]
                v = edge[1]
                color = 'green'
            else:
                assert(0)

            MCS.add_edges_from([(u, v,{'type':edge_type, 'color':color, 'isTE':False})])

        Logger.INFO("# MCS nodes: " + str(len(MCS.nodes())))
        Logger.INFO("MCS nodes: " + str(MCS.nodes()))
        Logger.INFO("# MCS edges: " + str(len(MCS.edges())))
        Logger.INFO("MCS edges: " + str(MCS.edges()))
        # show_MCS(MCS)

        # print (len(list(nx.simple_cycles(MCS))))
        # Sometimes this will long time.
        # Logger.DEBUG ("The number of loops is "+str(len(list(nx.simple_cycles(MCS)))))
        # print (nx.find_cycle(MCS, source = 'r', orientation="original"))

        return MCS


    def node_mapping(self, g1, g2, inbuilder):
        '''Construct the minimal common supergraph
        Args:
            g1: The networkx object of the base graph
            g2: The networkx object of the target graph
        Return:
            A dict of node mapping: {g1_node1:[g2_node1, g2_node2...], ..., g1_noden:[]}
            A node in g1 can have 0, 1 or more candicate mapping nodes.
        '''
        nodes_g1 = g1.nodes()
        nodes_g2 = g2.nodes()

        node_mapping = dict()
        for nodes_myId_g1 in nodes_g1:
            not_found = True
            for nodes_myId_g2 in nodes_g2:
                n1 = g1.nodes[nodes_myId_g1]
                n2 = g2.nodes[nodes_myId_g2]

                # compare the type of nodes, we have three types of node: t--table, c--conditional, a--action call
                # and two special types: r--root and s--sink
                if n1.get('myId')[3] != n2.get('myId')[3]:
                    continue

                # TODO: change[3] stuff to use a unified function like GetNodeType
                if n1.get('myId')[3] == 'r' \
                        or n1.get('myId')[3] == 's' \
                        or n1.get('myId')[3] == 't' and self.compare_table(n1, n2, inbuilder) \
                        or n1.get('myId')[3] == 'c' and self.compare_conditional(n1, n2, inbuilder) \
                        or n1.get('myId')[3] == 'a' and n1.get('name') == n2.get('name'):
                    not_found = False
                    if n1.get('myId') in node_mapping:
                        node_mapping[n1.get('myId')].append(n2.get('myId'))
                    else:
                        node_mapping[n1.get('myId')] = [n2.get('myId')]

            if not_found:
                node_mapping[n1.get('myId')] = []

        return node_mapping

    def EnhanceWithTEs(self, g):
        '''Enhance the MCS with TE nodes. The purpose is to handle a node has more than one TEs.
        A TE node (blue) will be inserted right after the node that has TEs.
         O                   O
        / \      -->         |
      TEr  TEg              TE
                            / \
                          TEr  TEg
        Args:
            g: A networkx object: The orginal MCS.
        Return:
            g: A networkx object: The MCS enhanced with TE nodes.
        '''
        # find all TEs
        TEs = dict()
        for edge in g.edges(data=True):
            for another in g.edges(data=True):
                edge_type = edge[2]['type']
                another_type = another[2]['type']
                if edge[1] != another[1] and edge[0]==another[0] and edge_type==another_type:
                    edge[2]['isTE'] = True
                    another[2]['isTE'] = True
                    # create a TE mapping
                    if edge[2]['color'] == 'red':
                        if (edge[0], edge[1], edge_type) not in TEs.keys():
                            TEs[(edge[0], edge[1], edge_type)] = (another[0], another[1], another_type)
                    elif edge[2]['color'] == 'green':
                        if (another[0], another[1], another_type) not in TEs.keys():
                            TEs[(another[0], another[1], another_type)] = (edge[0], edge[1], edge_type)

        Logger.DEBUG("The original number of TEs is "+str(len(TEs)))
        Logger.DEBUG("The original TEs are "+str(TEs))

        # groups TEs: to support one each each action.
        # when a table has many actions, but they all point to the same next node,
        # we regard them as one TE with multiple incoming edges
        # init the union relation
        parent = dict()
        for i in range(len(TEs)):
            parent[i] = i

        # A utility function to do union of two subsets
        def union(parent, x, y):
            pid = parent[x]
            qid = parent[y]

            for key in parent.keys():
                if parent[key] == pid:
                    parent[key] = qid

        # if two TEs if they have the same source and destination node, we group them
        for i in range(len(TEs)):
            for j in range(len(TEs)):
                keyi = list(TEs.keys())[i]
                keyj = list(TEs.keys())[j]
                if i != j and keyi[0] == keyj[0] and keyi[1] == keyj[1] and \
                        TEs[keyi][0] == TEs[keyj][0] and TEs[keyi][1] == TEs[keyj][1]:
                    union(parent, i, j)

        # print (parent)
        # get all groups by checking the union relation
        groups = dict()
        for key in parent:
            if parent[key] not in groups.keys():
                groups[parent[key]] = [list(TEs.keys())[key]]
            else:
                groups[parent[key]].append(list(TEs.keys())[key])

        Logger.DEBUG("The number of TE groups is "+str(len(groups))+".\n The groups are "+str(groups))
        Logger.DEBUG("The groups of TEs are "+str(groups))

        def find_TE_in_graph(graph, target):
            candidates = graph.get_edge_data(target[0], target[1])
            assert (candidates != None)
            TE = None
            idx = -1
            for key in candidates.keys():
                if candidates[key]['isTE'] and candidates[key]['type'] == target[2]:
                    TE = candidates[key]
                    idx = key
                    break
            return TE, idx

        # insert nodes of TEs
        count_TEs = 0
        for key in groups:
            all_TEs = groups[key] # all TEs in this group
            all_red_type = [] # type for all red edges
            all_green_type = [] # type for all green edges
            all_red_idx = [] # index for all red edges
            all_green_idx = [] # index for all green edges
            red_v = None # the next node of red edges, all red edges share the same next node
            green_v = None # the next node of green edges, all green edges share the same next node
            com_u = None # the previous node, all edges share the same previous node

            for te in all_TEs:
                key_edge, key_idx = find_TE_in_graph(g, te)
                paired_edge, paired_idx = find_TE_in_graph(g, TEs[te])

                if key_edge['color'] == 'red':
                    all_red_type.append(key_edge['type'])
                    all_green_type.append(paired_edge['type'])
                    all_red_idx.append(key_idx)
                    all_green_idx.append(paired_idx)

                    if red_v is None:
                        red_v = te[1]
                    else:
                        assert(red_v==te[1])

                    if green_v is None:
                        green_v = TEs[te][1]
                    else:
                        assert(green_v==TEs[te][1])

                elif key_edge['color'] == 'green':
                    all_green_type.append(key_edge['type'])
                    all_red_type.append(paired_edge['type'])
                    all_green_idx.append(key_idx)
                    all_red_idx.append(paired_idx)

                    if green_v is None:
                        green_v = te[1]
                    else:
                        assert(green_v==te[1])
                    if red_v is None:
                        red_v = TEs[te][1]
                    else:
                        assert(red_v==TEs[te][1])
                else:
                    Logger.ERROR("The color of the TE is not correct: "+str(key_edge['color']))
                    assert(0)

                if com_u is None:
                    com_u = te[0]
                    assert(te[0]==TEs[te][0])
                else:
                    assert(com_u==te[0])
                    assert(com_u==TEs[te][0])

            # add a TE node
            g.add_nodes_from([("TE"+str(count_TEs), {'name':"TE"+str(count_TEs), 'color':'blue'})])
            # add the red outgoing edge
            g.add_edges_from([("TE"+str(count_TEs), red_v, {'type':all_red_type, 'color':'red', 'isTE':True})])
            # add the green outgoing edge
            g.add_edges_from([("TE"+str(count_TEs), green_v, {'type':all_green_type, 'color':'green', 'isTE':True})])
            # add the incomming edges
            for i in range(len(all_red_type)):
                g.add_edges_from([(com_u, "TE"+str(count_TEs), {'type':all_red_type[i], 'color':'blue', 'isTE':False})])
            # delete the original TE edges
            # Must give a key for MultiGraph
            for idx in all_red_idx:
                g.remove_edge(com_u, red_v, idx)
            for idx in all_green_idx:
                g.remove_edge(com_u, green_v, idx)

            count_TEs += 1

        Logger.INFO("# rdg_te nodes: " + str(len(g.nodes())))
        Logger.INFO("rdg_te nodes: " + str(g.nodes()))
        Logger.INFO("# rdg_te edges: " + str(len(g.edges())))
        Logger.INFO("rdg_te edges: " + str(g.edges()))

        # show_MCS(g)
        # show_colored_only_MCS(g)
        # for n in g.nodes(data=True):
        #     print (n)
        return g



    def alias_check(self, s1, s2):
        if s1 == s2:
            return True
        if s1 in self.alias and self.alias[s1] == s2 \
            or s2 in self.alias and self.alias[s2] == s1:
            return True
        return False

    def aliasList_check(self, f1, f2):
        return False

    def compare_table(self, n1, n2, inbuilder):
        if inbuilder.__class__.__name__ == 'GraphInputBuilder':
            return n1['name'] == n2['name']

        # compare keys
        if len(n1['key']) != len(n2['key']):
            return False
        for i in range(0, len(n1['key'])):
            if n1['key'][i]['match_type'] != n2['key'][i]['match_type'] \
                or not self.alias_check(n1['key'][i]['name'], n2['key'][i]['name']):
                return False

        # compare actions
        if len(n1['actions']) != len(n2['actions']):
            return False
        for i in range(0, len(n1['actions'])):
            if n1['actions'][i] != n2['actions'][i] \
                or not self.alias_check(n1['actions'][i], n2['actions'][i]):
                return False

        # If one table has __HIT__ and __MISS__, but the other does not, they are viewed as
        # different tables, even if everything else is the same.
        if ('__HIT__' in n1['next_tables'] and '__HIT__' not in n2['next_tables']) or \
           ('__HIT__' in n2['next_tables'] and '__HIT__' not in n1['next_tables']):
           return False

        return True

    def compare_fieldValue(self, f1, f2):
        if f1[0] == 'scalars' and f2[0] == 'scalars':
            length = min(len(f1[1]), len(f2[1]))
            prefixLen = length - 3
            if f1[1][0:prefixLen] == f2[1][0:prefixLen]: # TODO: temporary solution for diff numbering of targets
                return True
            else:
                return self.aliasList_check(f1, f2)
        else:
            if f1 == f2:
                return True
            return self.aliasList_check(f1, f2)

    def compare_exprValue(self, v1, v2):
        if not ('op' in v1 and 'op' in v2):
            print ("op not in exprValue: ", v1, v2)
            sys.exit(-2)
        if v1['op'] != v2['op']:
            return False
        if not ('left' in v1 and 'left' in v2 and 'right' in v1 and 'right' in v2):
            print ("Something wrong about understanding op expression, ", v1, v2)
            sys.exit(-2)
        if not self.compare_leftRight(v1['left'], v2['left']) \
            or not self.compare_leftRight(v1['right'], v2['right']):
            return False
        return True
        # if v1['op'] == 'or' \
        #     or v1['op'] == 'and' \
        #     or v1['op'] == '==' \
        #     or v1['op'] == '!-' \
        #     or v1['op'] == 'not' \
        #     or v1['op'] == 'd2b' \
        #     :

    def compare_leftRight(self, lr1, lr2):
        if lr1 == None and lr2 == None:
            return True
        if lr1 == None or lr2 == None:
            return False
        if lr1['type'] != lr2['type']:
            return False
        if lr1['type'] == 'expression':
            return self.compare_exprValue(lr1['value'], lr2['value'])
        if lr1['type'] == 'field':
            return self.compare_fieldValue(lr1['value'], lr2['value'])
        if lr1['type'] == 'hexstr':
            return lr1['value'] == lr2['value']
        print ("Something wrong about understanding leftRight, type: "+lr1['type'])
        sys.exit(-3)

    def compare_expression(self, e1, e2):
        return self.compare_leftRight(e1, e2)

    def compare_conditional(self, n1, n2,  inbuilder):
        if inbuilder.__class__.__name__ == 'GraphInputBuilder':
            return n1['name'] == n2['name']
        return self.compare_expression(n1['expression'], n2['expression'])



    def show_figure(self, G):
        '''A helper function. Draw the figure for debugging
        Args:
            G: The networkx graph to show
        Return:
            None
        '''

        pos=nx.spring_layout(G)
        nx.draw(G,pos, node_size=1500, with_labels=True)
        plt.draw()
        plt.show()


    def show_MCS(self, G):
        '''A helper function. Draw the figure of MCS
        Args:
            G: The networkx graph of MCS
        Return:
            None
        '''
        node_color_map = []
        for node in G.nodes():
            node_color = G.nodes[node].get('color')
            if node_color == 'red':
                node_color_map.append('red')
            elif node_color == 'green':
                node_color_map.append('green')
            elif node_color == 'blue':
                node_color_map.append('blue')
            else:
                node_color_map.append('grey')

        edge_color_map = []
        for edge in G.edges(data=True):
            edge_color = edge[2]['color']
            if edge_color == 'red':
                edge_color_map.append('red')
            elif edge_color == 'green':
                edge_color_map.append('green')
            elif edge_color == 'blue':
                edge_color_map.append('blue')
            else:
                edge_color_map.append('grey')


        pos=nx.spring_layout(G)
        nx.draw(G,pos, node_color=node_color_map, edge_color=edge_color_map, node_size=1000, width=2.0, with_labels=True)
        plt.draw()
        plt.show()

    def show_colored_only_MCS(self, G):
        '''A helper function. Draw the part of MCS that is colored
        Args:
            G: The networkx graph of MCS
        Return:
            None
        '''
        def find_edge_idx(graph, target):
            candidates = graph.get_edge_data(target[0], target[1])
            assert (candidates != None)

            for key in candidates.keys():
                if candidates[key]['type'] == target[2]['type']:
                    return key
            return -1

        green_edges = []
        red_edges = []
        for e in G.edges(data=True):
            ecolor = e[2]['color']
            if ecolor == 'green':
                idx = find_edge_idx (G, e)
                green_edges.append((e[0], e[1], idx))
            elif ecolor == 'red':
                idx = find_edge_idx (G, e)
                red_edges.append((e[0], e[1], idx))

        # get the old graph
        g_red = G.copy()
        for u,v,idx in green_edges:
            g_red.remove_edge(u, v, idx)
        g_red.remove_nodes_from(list(nx.isolates(g_red)))


        # get the new graph
        g_green = G.copy()
        for u,v,idx in red_edges:
            g_green.remove_edge(u, v, idx)
        g_green.remove_nodes_from(list(nx.isolates(g_green)))


        # get TEs
        old_nodes = []
        new_nodes = []
        for node in G.nodes(data=True):
            if node[1]['color'] == 'blue':
                if node not in old_nodes:
                    old_nodes.append(node)

                if node not in new_nodes:
                    new_nodes.append(node)

            elif node[1]['color'] == 'red':
                if node not in old_nodes:
                    old_nodes.append(node)

            elif node[1]['color'] == 'green':
                if node not in new_nodes:
                    new_nodes.append(node)


        new_G = nx.MultiDiGraph(directed=True)
        nodes = set()
        edges = set()

        # get all related nodes in old graph
        for i in old_nodes:
            for j in old_nodes:
                if i != j:
                    # we regard nodes on a path from i to j are related
                    if nx.has_path(g_red, source=i[0], target=j[0]):
                        path = nx.shortest_path(g_red, source=i[0], target=j[0])
                        nodes.add(path[0])
                        prev = path[0]
                        for k in range(1, len(path)):
                            nodes.add(path[k])
                            edges.add((prev, path[k]))
                            prev = path[k]

        # similar to old graph
        for i in new_nodes:
            for j in new_nodes:
                if i != j:
                    if nx.has_path(g_green, source=i[0], target=j[0]):
                        path = nx.shortest_path(g_green, source=i[0], target=j[0])
                        nodes.add(path[0])
                        prev = path[0]
                        for k in range(1, len(path)):
                            nodes.add(path[k])
                            edges.add((prev, path[k]))
                            prev = path[k]

        # add nodes
        for node in nodes:
            new_G.add_nodes_from([(node, {'name':G.nodes[node]['name'], 'color':G.nodes[node]['color']})])
        # add edges
        for edge in edges:
            edata = G.get_edge_data(edge[0], edge[1])[0]
            new_G.add_edges_from([(edge[0], edge[1], {'type':edata['type'], 'color':edata['color'], 'isTE':edata['isTE']})])

        # get color map for nodes
        node_color_map = []
        for node in new_G.nodes():
            node_color = new_G.nodes[node].get('color')
            if node_color == 'red':
                node_color_map.append('red')
            elif node_color == 'green':
                node_color_map.append('green')
            elif node_color == 'blue':
                node_color_map.append('blue')
            else:
                node_color_map.append('grey')

        # get color map for edges
        edge_color_map = []
        for edge in new_G.edges(data=True):
            edge_color = edge[2]['color']
            if edge_color == 'red':
                edge_color_map.append('red')
            elif edge_color == 'green':
                edge_color_map.append('green')
            elif edge_color == 'blue':
                edge_color_map.append('blue')
            else:
                edge_color_map.append('grey')


        pos=nx.spring_layout(new_G, k=0.2, iterations=50) # k is the distance between nodes
        nx.draw(new_G,pos, node_color=node_color_map, edge_color=edge_color_map, node_size=500, width=2.0, with_labels=True)
        plt.draw()
        plt.show()
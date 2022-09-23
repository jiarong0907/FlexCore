from abc import ABCMeta, abstractmethod
import json

import os
from typing import List


import Logger as Logger
from graph_tool import GraphTool

class Planner:
    __metaclass__ = ABCMeta
    def __init__(self, inbuilder):
        self.graph_tool = GraphTool()
        self.inbuilder = inbuilder
        self.dump_cmd = True
        self.node_cost = 1
        self.te_cost = 0

    @abstractmethod
    def compute(self):
        pass

    @abstractmethod
    def reconfig(self, rdg_o, rdg_n, dump_path):
        pass


    def get_atomic_plan(self, rdg_te, sol, enable_action_next=False):
        '''Generate reconfig script for one solution
            Args:
                rdg_te (networkx object): The MCS enhanced with TEs
                sol (list[]): All groups in this solution.
            Return:
                ops (list): A squence of op that can finish this solution atomically.
        '''
        ops = list() # all ops
        for group in sol:
            ops_edge = list() # set next pointer operations
            ops_post_TE = list() # make the TE offline before deleting it
            ops_post = list() # ops must be done after setting metadata
            ops_TE_edge = list() # ops must be done right before the metadata is set.
            for v in group:
                vcolor = rdg_te.nodes[v].get('color')
                if vcolor == 'green':
                    node_type = rdg_te.nodes[v].get('name')[3]
                    # conditions
                    if node_type == 'c':
                        out_edges = list(rdg_te.out_edges(v, data=True))
                        assert(len(out_edges) == 2)
                        # rely on edge type to get true and false branch
                        etype = rdg_te.get_edge_data(out_edges[0][0], out_edges[0][1])[0]['type']
                        if etype == 't_next':
                            true_branch, false_branch = out_edges[0], out_edges[1]
                        elif etype == 'f_next':
                            true_branch, false_branch = out_edges[1], out_edges[0]
                        else:
                            raise ValueError("The edge type is not correct.")
                        ops.append({'op_type':"cond_insert", 'name': v, 'edge_type':'null', 'edge_value':'null'})
                        ops_edge.append({'op_type':"set_true_ptr", 'name': v, 'edge_type':'t_next', 'edge_value':true_branch[1]})
                        ops_edge.append({'op_type':"set_false_ptr", 'name': v, 'edge_type':'f_next', 'edge_value':false_branch[1]})
                    # tables
                    elif node_type == 't':
                        out_edges = list(rdg_te.out_edges(v, data=True))
                        # assert(len(out_edges) == 1)
                        ops.append({'op_type':"tbl_insert", 'name': v, 'edge_type':'null', 'edge_value':'null'})
                        if enable_action_next:
                            for out_edge in out_edges:
                                if out_edge[2]['type'] == 'b_next':
                                    ops_edge.append({'op_type':"set_base_ptr", 'name': v, 'edge_type':out_edge[2]['type'], 'edge_value':out_edge[1]})
                                else:
                                    ops_edge.append({'op_type':"set_action_ptr", 'name': v, 'edge_type':out_edge[2]['type'], 'edge_value':out_edge[1]})
                        else:
                            for out_edge in out_edges:
                                ops_edge.append({'op_type':"set_base_ptr", 'name': v, 'edge_type':out_edge[2]['type'], 'edge_value':out_edge[1]})
                    else:
                        raise ValueError("The green node type is not correct.")
                elif vcolor == 'blue':
                    out_edges = list(rdg_te.out_edges(v, data=True))
                    assert(len(out_edges) == 2)
                    # we don't have edge type of TEs, so we use color to get true and false branch
                    ecolor = rdg_te.get_edge_data(out_edges[0][0], out_edges[0][1])[0]['color']
                    if ecolor == 'green':
                        true_branch, false_branch = out_edges[0], out_edges[1]
                    elif ecolor == 'red':
                        true_branch, false_branch = out_edges[1], out_edges[0]
                    else:
                        raise ValueError("The edge color is not correct.")
                    ops.append({'op_type':"TE_insert", 'name': v, 'edge_type':'null', 'edge_value':'null'})
                    ops_edge.append({'op_type':"set_TE_true_ptr", 'name': v, 'edge_type':'t_next', 'edge_value':true_branch[1]})
                    ops_edge.append({'op_type':"set_TE_false_ptr", 'name': v, 'edge_type':'f_next', 'edge_value':false_branch[1]})

                    # skip TE and delete it
                    in_edges = list(rdg_te.in_edges(v, data=True))

                    if in_edges[0][0][0] == 'c':
                        assert(len(in_edges) == 1)
                        # if in_edges[0]
                        if true_branch[2]['type'][0] == 't_next': # the type here is [] so we need [0]
                            ops_TE_edge.append({'op_type':"set_true_ptr", 'name': in_edges[0][0], 'edge_type':'t_next', 'edge_value': v})
                            ops_post_TE.append({'op_type':"set_true_ptr", 'name': in_edges[0][0], 'edge_type':'t_next', 'edge_value': true_branch[1]})
                        else:
                            ops_TE_edge.append({'op_type':"set_false_ptr", 'name': in_edges[0][0], 'edge_type':'f_next', 'edge_value': v})
                            ops_post_TE.append({'op_type':"set_false_ptr", 'name': in_edges[0][0], 'edge_type':'f_next', 'edge_value': true_branch[1]})
                    elif in_edges[0][0][0] == 'r':
                        for in_edge in in_edges:
                            ops_TE_edge.append({'op_type':"set_base_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': v})
                            ops_post_TE.append({'op_type':"set_base_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': true_branch[1]})
                    elif in_edges[0][0][0] == 't':
                        for in_edge in in_edges:
                            if enable_action_next:
                                ops_TE_edge.append({'op_type':"set_action_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': v})
                                ops_post_TE.append({'op_type':"set_action_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': true_branch[1]})
                            else:
                                ops_TE_edge.append({'op_type':"set_base_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': v})
                                ops_post_TE.append({'op_type':"set_base_ptr", 'name': in_edge[0], 'edge_type':in_edge[2]['type'], 'edge_value': true_branch[1]})
                    else:
                        raise ValueError("The type of previous node of TE is node correct: "+str(in_edges[0][0][0]))
                    ops_post.append({'op_type':"TE_delete", 'name': v, 'edge_type':'null', 'edge_value':'null'})

                elif vcolor == 'red':
                    node_type = rdg_te.nodes[v].get('name')[3]
                    if node_type == 'c':
                        ops_post.append({'op_type':"cond_delete", 'name': v, 'edge_type':'null', 'edge_value':'null'})
                    elif node_type == 't':
                        ops_post.append({'op_type':"tbl_delete", 'name': v, 'edge_type':'null', 'edge_value':'null'})
                    else:
                        raise ValueError("The red node type is not correct.")
                else:
                    raise ValueError("Cannot handle this node color. "+str(rdg_te.nodes[v].get('color')))


            ops.extend(ops_edge)
            ops.extend(ops_TE_edge)
            ops.append({'op_type':"set_metadata", 'name': group, 'edge_type':'null', 'edge_value':'null'})
            ops.extend(ops_post_TE)
            ops.extend(ops_post)

        # make sure there is no duplicated ops
        for i in range(len(ops)):
            for j in range(len(ops)):
                if i != j and ops[i] == ops[j]:
                    raise ValueError("Duplication found in the script:  "+str(ops[i]))

        return ops

    def get_plan_commands(self, plan, path):
        # suppose the TEs are all in the ingress
        output = ""
        has_trigger_on = False
        new_table_names:List[str] = []
        command_file_path =os.path.join(path, f"command_{self.__class__.__name__}.txt")
        entry_file_path =os.path.join(path, f"entry_{self.__class__.__name__}.txt")
        for line in plan:
            optype  = line['op_type']
            name    = line['name']
            etype   = line['edge_type']
            evalue  = line['edge_value']

            if optype == 'TE_insert' or optype == 'cond_insert' or optype == 'TE_delete' or optype == 'cond_delete' \
                    or optype == 'tbl_insert' or optype == 'tbl_delete' or optype == 'set_metadata':
                assert(etype=='null' and evalue=='null')

            # insert flex ingress flex_name null null
            if optype == 'TE_insert':
                output += "insert flex ingress "+self.translate_name(name)+" null null\n"

            # delete flex ingress flx_name
            elif optype == 'TE_delete':
                if has_trigger_on:
                    output += "trigger off\n"
                    has_trigger_on = False
                output += "delete flex ingress "+self.translate_name(name)+"\n"

            # insert cond ingress new_name
            elif optype == 'cond_insert':
                # uuid = str(uuid.uuid4().hex)
                # assert(name not in cond_name_map.keys())
                # cond_name_map[name] = "cnode_"+uuid
                assert(name[:3]=='g2_')
                output += "insert cond ingress "+self.translate_name(name)+"\n"

            # delete cond ingress old_name
            elif optype == 'cond_delete':
                assert(name[:3]=='g1_')
                output += "delete flex ingress "+self.translate_name(name)+"\n"

            # insert tabl ingress new_name
            elif optype == 'tbl_insert':
                assert(name[:3]=='g2_')
                output += "insert tabl ingress "+self.translate_name(name)+"\n"
                new_table_names.append(self.translate_name(name))

            # delete tabl ingress old_name
            elif optype == 'tbl_delete':
                assert(name[:3]=='g1_')
                output += "delete tabl ingress "+self.translate_name(name)+"\n"

            elif optype == 'set_true_ptr':
                assert(etype=='t_next')
                # change cond ingress cnode1 true_next MyIngress.acl
                output += "change cond ingress "+self.translate_name(name)+" true_next "+self.translate_name(evalue)+"\n"

            elif optype == 'set_false_ptr':
                assert(etype=='f_next')
                # change cond ingress cnode1 false_next MyIngress.acl
                output += "change cond ingress "+self.translate_name(name)+" false_next "+self.translate_name(evalue)+"\n"

            elif optype == 'set_TE_true_ptr':
                assert(etype=='t_next')
                # change cond ingress cnode1 true_next MyIngress.acl
                output += "change flex ingress "+self.translate_name(name)+" true_next "+self.translate_name(evalue)+"\n"

            elif optype == 'set_TE_false_ptr':
                assert(etype=='f_next')
                # change cond ingress cnode1 false_next MyIngress.acl
                output += "change flex ingress "+self.translate_name(name)+" false_next "+self.translate_name(evalue)+"\n"

            elif optype == 'set_base_ptr':
                # change tabl ingress MyIngress.ipv4_lpm MyIngress.ipv4_forward	flex2
                if etype == 'b_next':
                    etype = "base_default_next"
                if self.translate_name(name) == 'init':
                    output += "change init ingress "+self.translate_name(evalue)+"\n"
                else:
                    output += "change tabl ingress "+self.translate_name(name)+" "+etype+" "+self.translate_name(evalue)+"\n"

            elif optype == 'set_action_ptr':
                if etype == 'b_next':
                    etype = "base_default_next"
                output += "change tabl ingress "+self.translate_name(name)+" "+etype+" "+self.translate_name(evalue)+"\n"

            elif optype == 'set_metadata':
                # trigger on
                output += f"populate entry {entry_file_path}\n"
                output += f"trigger on\n"
                has_trigger_on = True
            else:
                raise ValueError("Cannot handle this optype: "+str(optype))

        output = output[:-1]
        Logger.CRITICAL("\n"+output)
        if self.dump_cmd:
            with open(command_file_path,'w') as f:
                f.write(output)
            # generate entry insertion commands
            out_json = {}
            for name in new_table_names:
                out_json[f"{name}"] = None
            with open(entry_file_path,'w') as f:
                json.dump(out_json, f, indent=4)
            Logger.CRITICAL(f"Dump the plan to {command_file_path}, "
                            f"entry insertion commands to {entry_file_path}")
        return output

    def compute_take_release(self, rdg_te, group):
        take = 0
        release = 0
        for node in group:
            vcolor = rdg_te.nodes[node].get('color')
            if vcolor == 'green':
                take += self.node_cost
            elif vcolor == 'red':
                release += self.node_cost
            elif vcolor == 'blue':
                take += self.te_cost
                release += self.node_cost
            else:
                assert(0)
        return take, release

    def compute_max_transient(self, rdg_te, plan):
        usage = 0
        max_usage = 0
        for group in plan:
            take, release = self.compute_take_release(rdg_te, group)
            usage += take
            if usage > max_usage:
                max_usage = usage
            usage -= release

        return max_usage

    def translate_name(self, old_name):
        if old_name == 'r':
            return "init"
        if old_name == 's':
            return "null"
        if old_name[:2] == 'TE':
            return "flx_"+old_name
        if old_name[0]=='g':
            if old_name[:3]=='g1_':
                return "old_"+old_name[4:]
            elif old_name[:3]=='g2_':
                return "new_"+old_name[4:]
            else:
                raise ValueError("Wrong old_name prefix: "+str(old_name[:3]))
        elif old_name[0]=='t' or old_name[0]=='c' or old_name[0]=='a':
            return "old_"+old_name[1:]

        raise ValueError("Wrong old_name prefix prefix")





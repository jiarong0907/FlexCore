import argparse
import pickle
import sys
import networkx as nx
import matplotlib.pyplot as plt
import random

import json_to_nxGraph

class ExecutionNode:
	def __init__(self, name, id, myId, parent_block):
		self.name = name
		self.id = id
		self.myId = myId
		self.parent_block = parent_block
	def rec_find_parent_next_myId(self, prefix):
		n = self.parent_block.get_node_after(self)
		if n == None:
			if self.parent_block.parent_cond == None:
				return prefix+"s"
			else:
				return self.parent_block.parent_cond.rec_find_parent_next_myId(prefix)
		else:
			return n.myId
class Block:
	def __init__(self, parent_cond, block_type, exec_list):
		self.parent_cond = parent_cond
		self.parent_id = 0 if parent_cond == None else parent_cond.id
		self.block_type = block_type
		self.exec_list = exec_list
	def append_node(self, node):
		self.exec_list.append(node)
	def get_node_after(self, prev):
		idx = self.exec_list.index(prev)
		return self.exec_list[idx+1] if idx+1 < self.size() else None
	def add_node_after(self, prev, node):
		idx = self.exec_list.index(prev)
		self.exec_list.insert(idx+1, node)
	def add_node_at(self, idx, node):
		self.exec_list.insert(idx, node)
	def remove_sublist(self, start_id, size):
		removed = []
		for i in range(start_id, start_id+size):
			n = self.exec_list.pop(start_id)
			n.parent_block = None
			removed.append(n)
		return removed
	def size(self):
		return len(self.exec_list)
	def get_random_subblock(self, cap):
		start = random.randint(1, self.size()-1) if self.size() > 1 else 1
		cap = min(self.size()-start, cap)
		size = random.randint(0, cap)
		return (start, size)
	def get_first_exec(self):
		return self.exec_list[1] if self.size() > 1 else None
	def print_exec(self):
		s = ""
		for n in self.exec_list:
			s += str(n.id) + " "
		print(s)
	def contains(self, start_id, subblock_size, parent_block):
		for i in range(start_id, start_id+subblock_size):
			if isinstance(self.exec_list[i], Conditional):
				true_block = self.exec_list[i].true_block
				false_block = self.exec_list[i].false_block
				if self.exec_list[i].true_block == parent_block or \
					self.exec_list[i].false_block == parent_block or \
					true_block.contains(1, true_block.size()-1, parent_block) or \
					false_block.contains(1, false_block.size()-1, parent_block):
					return True
		return False

class Dummy(ExecutionNode):
	def __init__(self, name, id, myId, parent_block):
		super().__init__(name, id, myId, parent_block)

class Conditional(ExecutionNode):
	def __init__(self, name, id, myId, parent_block, true_block, false_block, expression = None, json = None):
		super().__init__(name, id, myId, parent_block)
		self.true_block = true_block
		self.false_block = false_block
		if json != None:
			self.expression = json["expression"]
			self.json = json
		elif expression != None:
			self.expression = expression
			self.json = {
				'name': name,
				'id': id,
				'myId': myId,
				'expression': expression
			}
		else:
			print("Conditional init need either expression or json")
			sys.exit(-1)

	def set_true_block(self, true_block):
		self.true_block = true_block
	def set_false_block(self, false_block):
		self.false_block = false_block

class Table(ExecutionNode):
	def __init__(self, name, id, myId, parent_block, key = None, actions = None, json = None):
		super().__init__(name, id, myId, parent_block)
		if json != None:
			self.key = json["key"]
			self.actions = json["actions"]
			self.json = json
		elif key != None and actions != None:
			self.key = key
			self.actions = actions
			self.json = {
				'name': name,
				'id': id,
				'myId': myId,
				'key': key,
				'actions': actions
			}
		else:
			print("Table init need either key, actions or json")
			sys.exit(-1)

class Program:
	def __init__(self, idStart, size, prefix, init_table_ratio = 80, init_subblock_cap = 3):
		self.idCount = idStart
		self.size = size
		self.init_table_ratio = init_table_ratio
		self.init_subblock_cap = init_subblock_cap
		self.prefix = prefix

	def gen_prog(self):
		self.id2node = {}
		self.nodes = []
		self.nodes_with_dummy = []
		self.p4file2ids = None
		self.root_block = self.new_block(None, "root")
		# self.root_block.print_exec()
		self.root_block.append_node(self.new_dummy(self.root_block))
		count = 0
		if self.size == 0:
			return
		prev = self.get_random_node_with_dummy()
		self.add_table_after(prev) # first node can only be table
		while count < self.size - 1:
			target = random.randint(0, 99)
			if target < self.init_table_ratio:
				prev = self.get_random_node_with_dummy()
				self.add_table_after(prev)
			else:
				subblock_size = 0
				while subblock_size < 1:
					n = self.get_random_node_with_dummy()
					start_id, subblock_size = n.parent_block.get_random_subblock(self.init_subblock_cap)
				self.add_cond_at(n.parent_block, start_id, subblock_size)
			count += 1
		# self.root_block.print_exec()

	def gen_prog_from_graph(self, graph):
		root_edges = list(graph.edges("r"))
		if len(root_edges) != 1:
			print("Root node should have exactly one next node")
			sys.exit(-1)
		# edge2covered = {}
		# self.get_covered_nodes(edge2covered, graph, root_edges[0])
		self.id2node = {}
		self.nodes = []
		self.nodes_with_dummy = []
		self.p4file2ids = {}
		self.root_block = self.create_block_from_graph(graph, root_edges[0][1], "s", None, "root")

	def get_one_path(self, graph, edge):
		cur = edge
		dstMyId = graph.nodes[edge[1]]['myId']
		path = []
		while dstMyId != "s":
			path += [dstMyId]
			dst = list(graph.edges(dstMyId))[0][1]
			dstMyId = graph.nodes[dst]['myId']
		path += "s"
		return path

	def get_all_covered_nodes(self, edge2covered, graph, edge):
		stack = [edge]
		while len(stack) != 0:
			edge = stack[-1]
			# print("Edge", edge, len(stack), len(edge2covered))
			dstMyId = graph.nodes[edge[1]]['myId']
			if dstMyId[0] == "t":
				next_edges = list(graph.edges(edge[1]))
				if len(next_edges) != 1:
					print("Table should have exactly one next node")
					sys.exit(-1)
				if next_edges[0] not in edge2covered:
					stack.append(next_edges[0])
				else:
					edge2covered[edge] = [dstMyId] + edge2covered[next_edges[0]]
					stack.pop()
			elif dstMyId[0] == "c":
				next_edges = list(graph.edges(edge[1]))
				if len(next_edges) != 2:
					print("Conditional should have exactly two next nodes")
					sys.exit(-1)
				if next_edges[0] not in edge2covered:
					stack.append(next_edges[0])
				if next_edges[1] not in edge2covered:
					stack.append(next_edges[1])
				if next_edges[0] in edge2covered and next_edges[1] in edge2covered:
					edge2covered[edge] = [dstMyId] \
						+ edge2covered[next_edges[0]] \
						+ edge2covered[next_edges[1]]
					stack.pop()
			elif dstMyId == "s":
				edge2covered[edge] = [dstMyId]
				stack.pop()
			else:
				print("myId can only have prefix 's', 't', 'c' (not 'r')")
				sys.exit(-1)

	def rec_get_covered_nodes(self, edge2covered, graph, edge):
		print("Edge", edge)
		dstMyId = graph.nodes[edge[1]]['myId']
		covered = [dstMyId]
		if dstMyId[0] == "t":
			next_edges = list(graph.edges(edge[1]))
			if len(next_edges) != 1:
				print("Table should have exactly one next node")
				sys.exit(-1)
			if next_edges[0] not in edge2covered:
				self.rec_get_covered_nodes(edge2covered, graph, next_edges[0])
			covered = covered + edge2covered[next_edges[0]]
		elif dstMyId[0] == "c":
			next_edges = list(graph.edges(edge[1]))
			if len(next_edges) != 2:
				print("Conditional should have exactly two next nodes")
				sys.exit(-1)
			if next_edges[0] not in edge2covered:
				self.rec_get_covered_nodes(edge2covered, graph, next_edges[0])
			if next_edges[1] not in edge2covered:
				self.rec_get_covered_nodes(edge2covered, graph, next_edges[1])
			covered = covered \
				+ edge2covered[next_edges[0]] \
				+ edge2covered[next_edges[1]]
		elif edge[1] != "s":
			print("myId can only have prefix 's', 't', 'c' (not 'r')")
			sys.exit(-1)
		edge2covered[edge] = covered
		return covered

	def create_block_from_graph(self, graph, first_node, end_node, parent_cond, block_type):
		block = self.new_block(parent_cond, block_type)
		dummy = self.new_dummy(block)
		if parent_cond == None:
			p4file = "switch.p4"
		else:
			p4file = parent_cond.json["source_info"]["filename"]
		if p4file not in self.p4file2ids:
			self.p4file2ids[p4file] = set()
		self.p4file2ids[p4file].add(dummy.id)
		block.append_node(dummy)
		cur = first_node
		while cur != end_node:
			attr = graph.nodes[cur]
			if attr['myId'][0] == "t":
				attr["myId"] = self.prefix + attr["myId"]
				t = Table(attr["name"],
					self.idCount,
					attr["myId"],
					block,
					attr["key"],
					attr["actions"],
					attr)
				self.id2node[self.idCount] = t
				self.nodes_with_dummy.append(t)
				self.nodes.append(t)
				p4file = attr["source_info"]["filename"]
				if p4file not in self.p4file2ids:
					self.p4file2ids[p4file] = set()
				self.p4file2ids[p4file].add(self.idCount)
				self.idCount += 1
				block.append_node(t)
				next_edges = list(graph.edges(cur))
				cur = next_edges[0][1]
			elif attr['myId'][0] == "c":
				attr["myId"] = self.prefix + attr["myId"]
				c = Conditional(attr["name"],
					self.idCount,
					attr["myId"],
					block,
					None,
					None,
					attr["expression"],
					attr)
				self.id2node[self.idCount] = c
				self.nodes_with_dummy.append(c)
				self.nodes.append(c)
				p4file = attr["source_info"]["filename"]
				if p4file not in self.p4file2ids:
					self.p4file2ids[p4file] = set()
				self.p4file2ids[p4file].add(self.idCount)
				self.idCount += 1
				next_edges = list(graph.edges(cur))
				cc = self.get_common_child(graph, next_edges)
				next_edges = list(graph.edges(cur, data=True))
				for edge in next_edges:
					if edge[2]['type'] == "t_next":
						true_block = self.create_block_from_graph(graph,
							edge[1],
							cc,
							c,
							"true")
					elif edge[2]['type'] == "f_next":
						false_block = self.create_block_from_graph(graph,
							edge[1],
							cc,
							c,
							"false")
					else:
						print("Edge type of conditional should only be t_next or f_next")
						sys.exit(-1)
				c.set_true_block(true_block)
				c.set_false_block(false_block)
				block.append_node(c)
				cur = cc
			else:
				print("Error: myId can only have prefix 't', 'c' (not 'r' or 's')", attr['myId'], end_node)
				sys.exit(-1)
		return block


	def get_common_child(self, graph, edges):
		if len(edges) != 2:
			print("get_common_child should be used on exactly two edges")
			sys.exit(-1)
		path1 = self.get_one_path(graph, edges[0])
		path2 = self.get_one_path(graph, edges[1])
		for n in path1:
			if n in path2:
				return n

	def get_random_node_with_dummy(self, p4_file = None):
		if p4_file == None:
			return random.choice(self.nodes_with_dummy)
		if self.p4file2ids == None:
			print("Error: random node under a p4 file can only be used for programs generated by gen_prog_from_graph")
			sys.exit(-1)
		if p4_file not in self.p4file2ids:
			print("Error: file", p4_file, "doesn't exist in the input program")
			sys.exit(-1)
		candidates = self.p4file2ids[p4_file]
		return self.id2node[random.choice(list(candidates))]
		
		# loc = 0
		# for idx in id2node:
		# 	if loc == r:
		# 		return id2node[idx]
		# 	loc += 1
		# print("Error: random get location out of id2node")
		# sys.exit(-1)
		# return None

	def add_table_after(self, prev, silent = True, p4_file = None):
		parent_block = prev.parent_block
		table = self.new_table(parent_block)
		if self.p4file2ids != None and p4_file != None:
			self.p4file2ids[p4_file].add(table.id)
		#parent_block.print_exec()
		parent_block.add_node_after(prev, table)
		if not silent:
			if isinstance(prev, Dummy) and prev.parent_block.block_type != "root":
				print("t", table.id, "parent", prev.parent_block.parent_cond.id, prev.parent_block.block_type)
			else:
				print("t", table.id, "after", prev.id)
		#parent_block.print_exec()

	def add_cond_at(self, parent_block, start_id, size, silent = True, p4_file = None):
		covered = parent_block.remove_sublist(start_id, size)
		false_node_loc = random.randint(1, size)
		cond = self.new_cond(parent_block)
		if p4_file != None and self.p4file2ids != None:
			self.p4file2ids[p4_file].add(cond.id)
		true_block = self.new_block(cond, "true")
		false_block = self.new_block(cond, "false")
		cond.set_true_block(true_block)
		cond.set_false_block(false_block)
		true_block.append_node(self.new_dummy(true_block))
		false_block.append_node(self.new_dummy(false_block))

		for i in range(0, false_node_loc):
			covered[i].parent_block = true_block
			true_block.append_node(covered[i])
		for i in range(false_node_loc, size):
			covered[i].parent_block = false_block
			false_block.append_node(covered[i])
		parent_block.add_node_at(start_id, cond)

		true_node = true_block.get_first_exec()
		false_node = false_block.get_first_exec()
		next_node = parent_block.get_node_after(cond)
		if not silent:
			print("c", cond.id, "before", true_node.id, 
				"false", false_node.id if false_node else false_node,
				"next node", next_node.id if next_node else next_node)

	def add_node(self, node):
		self.id2node[node.id] = node
		self.nodes_with_dummy.append(node)
		if not isinstance(node, Dummy):
			self.nodes.append(node)
		if isinstance(node, Conditional):
			for m in node.true_block.exec_list:
				self.add_node(m)
			for m in node.false_block.exec_list:
				self.add_node(m)

	def delete_node_with_id(self, idx, p4_file = None):
		n = self.id2node[idx]
		self.id2node.pop(idx)
		self.nodes_with_dummy.remove(n)
		if self.p4file2ids != None and p4_file != None:
			self.p4file2ids[p4_file].discard(idx)
		if not isinstance(n, Dummy):
			self.nodes.remove(n)
		if isinstance(n, Conditional):
			for m in n.true_block.exec_list:
				self.delete_node_with_id(m.id, p4_file)
			for m in n.false_block.exec_list:
				self.delete_node_with_id(m.id, p4_file)

	def new_table(self, parent_block):
		table = Table("table"+str(self.idCount),
			self.idCount,
			"t"+str(self.idCount),
			parent_block,
			[{'match_type': str(self.idCount), 'name': str(self.idCount)}],
			[])
		self.id2node[self.idCount] = table
		self.nodes_with_dummy.append(table)
		self.nodes.append(table)
		self.idCount += 1
		return table

	def new_dummy(self, parent_block):
		dummy = Dummy("dummy"+str(self.idCount),
			self.idCount,
			"d"+str(self.idCount),
			parent_block)
		self.id2node[self.idCount] = dummy
		self.nodes_with_dummy.append(dummy)
		self.idCount += 1
		return dummy

	def new_cond(self, parent_block):
		true_block = None
		false_block = None
		cond = Conditional("cond"+str(self.idCount),
			self.idCount,
			"c"+str(self.idCount),
			parent_block,
			true_block,
			false_block,
			{'type': 'hexstr', 'value':'0x01'+str(id)})
		self.id2node[self.idCount] = cond
		self.nodes_with_dummy.append(cond)
		self.nodes.append(cond)
		self.idCount += 1
		return cond

	def new_block(self, parent_cond, block_type):
		exec_list = []
		block = Block(parent_cond,
			block_type,
			exec_list)
		# block.print_exec()
		return block

	def to_nxGraph(self):
		graph = nx.MultiDiGraph()
		graph.add_nodes_from([(self.prefix+"r", {'myId': self.prefix+'r', 'name':'r'})])
		graph.add_nodes_from([(self.prefix+"s", {'myId': self.prefix+'s', 'name':'s'})])
		for n in self.nodes:
			graph.add_nodes_from([(n.myId, n.json)])
		graph.add_edges_from([(self.prefix+"r", self.root_block.get_first_exec().myId, {'type': 'b_next'})])

		for n in self.nodes:
			if isinstance(n, Table):
				dstMyId = n.rec_find_parent_next_myId(self.prefix)
				graph.add_edges_from([(n.myId, dstMyId, {'type': 'b_next'})])
			elif isinstance(n, Conditional):
				trueNode = n.true_block.get_first_exec()
				falseNode = n.false_block.get_first_exec()
				graph.add_edges_from([(n.myId, trueNode.myId, {'type': 't_next'})])
				if falseNode != None:
					falseNodeMyId = falseNode.myId
				else:
					falseNodeMyId = n.rec_find_parent_next_myId(self.prefix)
				graph.add_edges_from([(n.myId, falseNodeMyId, {'type': 'f_next'})])
		return graph

	def rec_check_swap(self, parent_block): # impossible to swap when all nodes except the last one are conditional and only have true_block => return True
		if parent_block.size() == 2:
			if isinstance(parent_block.exec_list[1], Table):
				return True
			if parent_block.exec_list[1].false_block.size() > 1:
				return False
			return self.rec_check_swap(parent_block.exec_list[1].true_block)
		else:
			return False

	def impossible_to_swap(self):
		return self.rec_check_swap(self.root_block)

	def edit(self, step, add_table_ratio = 0, add_cond_ratio = 0, replace_ratio = 10, replace_prog_cap = 5, edit_subblock_cap = 5, p4_file = None):
		add_table_thr = add_table_ratio
		add_cond_thr = add_table_thr + add_cond_ratio
		replace_thr = add_cond_thr + replace_ratio
		if p4_file != None and replace_thr < 100:
			print("Warning: For now, no check to ensure swap can or cannot happen, so I try 100 times at most before giving up swap operation")
		if p4_file != None and self.p4file2ids == None:
			print("Error: p4_file can only be used when program is generated from graph")
			sys.exit(-1)
		# print("thrs:", add_table_thr, add_cond_thr, replace_thr)
		for i in range(0, step):
			target = random.randint(0, 99)
			if target < add_table_thr:
				prev = self.get_random_node_with_dummy(p4_file)
				self.add_table_after(prev, silent = True, p4_file = p4_file)
			elif target < add_cond_thr:
				subblock_size = 0
				while subblock_size < 1:
					n = self.get_random_node_with_dummy(p4_file)
					start_id, subblock_size = n.parent_block.get_random_subblock(edit_subblock_cap)
				self.add_cond_at(n.parent_block, start_id, subblock_size, silent = True, p4_file = p4_file)
			elif target < replace_thr:
				first_time = True
				while first_time or \
					len(prog.nodes) == 0 and n.parent_block.block_type != "false" and subblock_size == n.parent_block.size()-1 or \
					len(prog.nodes) == 0 and subblock_size == 0:
					n = self.get_random_node_with_dummy(p4_file)
					start_id, subblock_size = n.parent_block.get_random_subblock(edit_subblock_cap)
					replace_prog_size = random.randint(0, replace_prog_cap)
					prog = Program(idStart = self.idCount, 
						size = replace_prog_size, 
						prefix = self.prefix, 
						init_table_ratio = self.init_table_ratio, 
						init_subblock_cap = self.init_subblock_cap)
					prog.gen_prog()
					first_time = False
				# self.root_block.print_exec()
				# prog.root_block.print_exec()
				self.replace_subprog(n.parent_block, start_id, subblock_size, prog, p4_file)
			else:
				if self.impossible_to_swap():
					continue;
				subblock_size1 = 0
				subblock_size2 = 0
				tries = 0
				while subblock_size1 == 0 and subblock_size2 == 0 or \
					parent_block1 == parent_block2 and subblock_size1 == 1 and subblock_size2 == 1 and start_id1 == start_id2 or \
					subblock_size1 == 0 and parent_block2.block_type != "false" and subblock_size2 == parent_block2.size()-1 or \
					subblock_size2 == 0 and parent_block1.block_type != "false" and subblock_size1 == parent_block1.size()-1 or \
					parent_block1.contains(start_id1, subblock_size1, parent_block2) or \
					parent_block2.contains(start_id2, subblock_size2, parent_block1) or \
					tries > 100:
					n = self.get_random_node_with_dummy(p4_file)
					parent_block1 = n.parent_block
					start_id1, subblock_size1 = parent_block1.get_random_subblock(edit_subblock_cap)
					n = self.get_random_node_with_dummy(p4_file)
					parent_block2 = n.parent_block
					start_id2, subblock_size2 = parent_block2.get_random_subblock(edit_subblock_cap)
					if parent_block1 == parent_block2:
						p = [start_id1, start_id1+subblock_size1, start_id2, start_id2+subblock_size2]
						p.sort()
						(start_id1, subblock_size1, start_id2, subblock_size2) = \
							(p[0], p[1]-p[0], p[2], p[3]-p[2])
					tries += 1
				if tries >= 100:
					print("Warning: Skip one swap operation because trying 100 times without finding a feasible swap")
					continue;
				# cond1 = parent_block1.parent_cond
				# cond2 = parent_block2.parent_cond
				# print(cond1 if cond1 == None else cond1.id,
				# 	cond2 if cond2 == None else cond2.id,
				# 	start_id1,
				# 	start_id2,
				# 	subblock_size1,
				# 	subblock_size2)
				self.swap(parent_block1, start_id1, subblock_size1, parent_block2, start_id2, subblock_size2)

	def replace_subprog(self, parent_block, start_id, subblock_size, prog, p4_file = None):
		# self.root_block.print_exec()
		# prog.root_block.print_exec()
		# parent_block.print_exec()
		to_del = parent_block.remove_sublist(start_id, subblock_size)
		# parent_block.print_exec()
		for i in range(0, subblock_size):
			self.delete_node_with_id(to_del[i].id, p4_file)
			if p4_file != None and self.p4file2ids != None:
				self.p4file2ids[p4_file].add(parent_block.exec_list[0].id) # to ensure there is at least one node to edit for p4_file
		# prog.root_block.print_exec()
		to_add = prog.root_block.remove_sublist(1, prog.root_block.size()-1)
		# prog.root_block.print_exec()
		for i in range(0, len(to_add)):
			to_add[i].parent_block = parent_block
			self.add_node(to_add[i])
			parent_block.add_node_at(start_id+i, to_add[i])
			if p4_file != None and self.p4file2ids != None:
				self.p4file2ids[p4_file].add(to_add[i].id)
		# parent_block.print_exec()
		# self.root_block.print_exec()
		self.idCount = prog.idCount
		cond = parent_block.parent_cond
		parent_id = 0 if cond == None else cond.id
		# print("replace", parent_id, list(map(lambda x: x.id, to_del)), "with", list(map(lambda x: x.id, to_add)))

	def swap(self, parent_block1, start_id1, subblock_size1, parent_block2, start_id2, subblock_size2):
		list2 = parent_block2.remove_sublist(start_id2, subblock_size2)
		list1 = parent_block1.remove_sublist(start_id1, subblock_size1)
		for i in range(0, len(list1)):
			list1[i].parent_block = parent_block2
			parent_block2.add_node_at(start_id2+i, list1[i])
		for i in range(0, len(list2)):
			list2[i].parent_block = parent_block1
			parent_block1.add_node_at(start_id1+i, list2[i])
		cond1 = parent_block1.parent_cond
		cond2 = parent_block2.parent_cond
		parent_id1 = 0 if cond1 == None else cond1.id
		parent_id2 = 0 if cond2 == None else cond2.id
		# print("swap", parent_id1, parent_block1.block_type, start_id1, list(map(lambda x: x.id, list1)),
		# 	"and", parent_id2, parent_block2.block_type, start_id2, list(map(lambda x: x.id, list2)))

def gen_synthetic_prog_pair(init_prog_size = 10,
			init_table_ratio = 50,
			init_subblock_cap = 3,
			edit_times = 10,
			add_table_ratio = 50,
			add_cond_ratio = 0,
			replace_ratio = 45,
			replace_prog_cap = 3,
			edit_subblock_cap = 3):
	# random.seed(0)
	prog = Program(idStart = 0, 
		size = init_prog_size, 
		prefix = '', 
		init_table_ratio = init_table_ratio, 
		init_subblock_cap = init_subblock_cap)
	prog.gen_prog()
	print("Old program generation done")
	graph1 = prog.to_nxGraph()
	print("Old program's graph generation done")
	#pos=nx.random_layout(graph)
	#pos=nx.kamada_kawai_layout(graph)
	#pos=nx.circular_layout(graph)
	# pos=nx.planar_layout(graph)
	# nx.draw(graph, node_size=5, with_labels=True)
	# plt.savefig('foo3.pdf')
	# print("Graph visualization output")

	prog.edit(step = edit_times,
		add_table_ratio = add_table_ratio,
		add_cond_ratio = add_cond_ratio,
		replace_ratio = replace_ratio,
		replace_prog_cap = replace_prog_cap,
		edit_subblock_cap = edit_subblock_cap)
	print("New program generation done")
	# plt.clf()
	graph2 = prog.to_nxGraph()
	print("New program's graph generation done")
	#pos=nx.random_layout(graph)
	#pos=nx.kamada_kawai_layout(graph)
	#pos=nx.circular_layout(graph)
	# pos=nx.planar_layout(graph)
	# nx.draw(graph, node_size=5, with_labels=True)
	# plt.savefig('foo4.pdf')
	# print("Graph visualization output after edited")
	return (graph1, graph2)

def gen_prog_pair_from_graph(graph, prefix,
			init_table_ratio = 50,
			init_subblock_cap = 3,
			edit_times = 10,
			add_table_ratio = 50,
			add_cond_ratio = 0,
			replace_ratio = 45,
			replace_prog_cap = 3,
			edit_subblock_cap = 3,
			p4_file = None):
	# random.seed(0)
	prog = Program(idStart = 0, 
		size = 0, 
		prefix = prefix,
		init_table_ratio = init_table_ratio,
		init_subblock_cap = init_subblock_cap)
	prog.gen_prog_from_graph(graph)
	print("Old program generation from graph done")
	graph1 = prog.to_nxGraph()
	print("Old program's graph generation done")
	#pos=nx.random_layout(graph)
	#pos=nx.kamada_kawai_layout(graph)
	#pos=nx.circular_layout(graph)
	# pos=nx.planar_layout(graph)
	# nx.draw(graph, node_size=5, with_labels=True)
	# plt.savefig('foo3.pdf')
	# print("Graph visualization output")
	prog.edit(step = edit_times,
		add_table_ratio = add_table_ratio,
		add_cond_ratio = add_cond_ratio,
		replace_ratio = replace_ratio,
		replace_prog_cap = replace_prog_cap,
		edit_subblock_cap = edit_subblock_cap,
		p4_file = p4_file)
	print("New program generation done")
	# plt.clf()
	graph2 = prog.to_nxGraph()
	print("New program's graph generation done")
	#pos=nx.random_layout(graph)
	#pos=nx.kamada_kawai_layout(graph)
	#pos=nx.circular_layout(graph)
	# pos=nx.planar_layout(graph)
	# nx.draw(graph, node_size=5, with_labels=True)
	# plt.savefig('foo4.pdf')
	# print("Graph visualization output after edited")
	return (graph1, graph2)

def _configure() -> argparse.Namespace:
	"""Sets up arg parser"""
	parser = argparse.ArgumentParser()
	parser.add_argument(
		"-j",
		dest="initial_json",
		default=None,
		help=(
			"The initial json file. "
			"If provided, the pair of programs output will be the "
			"initial json itself and the randomly edited program; "
			"if not provided, both the initial program and the "
			"edited program will be randomly generated."
		),
	)
	parser.add_argument(
		"-o",
		dest="output_prefix",
		required=True,
		help=(
			"The prefix for the output files. "
			"There are two output files. Both will have prefix "
			"specified by this parameter, i.e., "
			"<output_prefix>_old.graph and "
			"<output_prefix>_new.graph."
		),
	)
	parser.add_argument(
		"-ip",
		dest="init_prog_size",
		type=int,
		default=10,
		help=(
			"The initial program size (also the program size when "
			"adding a new code snippet during editing). Default: 10"
		),
	)
	parser.add_argument(
		"-it",
		dest="init_table_ratio",
		type=int,
		default=50,
		help=(
			"The initial ratio for table nodes (also the table "
			"ratio when adding a new code snippet during editing). "
			"Default: 50. "
			"The conditional nodes are the remaining nodes. 50 for 50%%."
		),
	)
	parser.add_argument(
		"-is",
		dest="init_subblock_cap",
		type=int,
		default=3,
		help=(
			"The maximum size a subblock can contain when defining "
			"conditional node branches for the initial program "
			"(also the subblock cap when adding a new code snippet "
			"during editing). Default: 3"
		),
	)
	parser.add_argument(
		"-e",
		dest="edit_times",
		type=int,
		default=100,
		help=(
			"The number of edits done on the intial program. "
			"Default: 100"
		),
	)
	parser.add_argument(
		"-at",
		dest="add_table_ratio",
		type=int,
		default=50,
		help=(
			"The ratio of table addition among all edits. Default: 50. "
			"50 for 50%%"
		),
	)
	parser.add_argument(
		"-ac",
		dest="add_cond_ratio",
		type=int,
		default=0,
		help=(
			"The ratio of conditional node addition among all "
			"edits. Default: 0. "
			"50 for 50%%"
		),
	)
	parser.add_argument(
		"-r",
		dest="replace_ratio",
		type=int,
		default=45,
		help=(
			"The ratio of code snippet relacement among all edits. "
			"Default: 45. "
			"This remaining edits will be swapping two subblocks. "
			"50 for 50%%"
		),
	)
	parser.add_argument(
		"-rc",
		dest="replace_prog_cap",
		type=int,
		default=3,
		help=(
			"The maximum program size for the new code snippet used "
			"to replace the old code snippet for the \"code snippet "
			"replacement\" edits.  Default: 3"
		),
	)
	parser.add_argument(
		"-es",
		dest="edit_subblock_cap",
		type=int,
		default=3,
		help=(
			"The maximum program size when selecting the old code "
			"snippet to edit for the \"code snippet replacement\" "
			"edits and the \"swap\" edits. Default: 3"
		),
	)
	return parser.parse_args()

def main(args: argparse.Namespace) -> None:
	"""The main program"""
	output_prefix = args.output_prefix
	if args.initial_json:
		initial_json = args.initial_json
		graph = json_to_nxGraph.json_to_nxGraph(args.initial_json, '')
		g1, g2 = gen_prog_pair_from_graph(
			graph,
			'',
			init_table_ratio=args.init_table_ratio, 
			init_subblock_cap=args.init_subblock_cap,
			edit_times=args.edit_times,
			add_table_ratio=args.add_table_ratio,
			add_cond_ratio=args.add_cond_ratio,
			replace_ratio=args.replace_ratio,
			replace_prog_cap=args.replace_prog_cap,
			edit_subblock_cap=args.edit_subblock_cap,
			# p4_file = "multicast.p4",  # This is to specify a single p4 subprogram to edit
		)
	else:
		g1, g2 = gen_synthetic_prog_pair(
			init_prog_size=args.init_prog_size,
			init_table_ratio=args.init_table_ratio, 
			init_subblock_cap=args.init_subblock_cap,
			edit_times=args.edit_times,
			add_table_ratio=args.add_table_ratio,
			add_cond_ratio=args.add_cond_ratio,
			replace_ratio=args.replace_ratio,
			replace_prog_cap=args.replace_prog_cap,
			edit_subblock_cap=args.edit_subblock_cap,
		)

	pickle.dump(g1, open(f'{args.output_prefix}_old.graph', 'wb'))
	pickle.dump(g2, open(f'{args.output_prefix}_new.graph', 'wb'))

if __name__ == "__main__":
	main(_configure())


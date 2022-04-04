import sys
import networkx as nx
import matplotlib.pyplot as plt
import random

def add_tnode_before(id2node, nextId, id):
	if id in id2node:
		print("Error: duplicated id: %d" % id)
		sys.exit(-1)
	id2node[id] = {
		'name'		: 'table'+str(id), 
		'id'		: id, 
		'key'		: [{'match_type': str(id)}], 
		'actions'	: [], 
		'myId'		: 't'+str(id), 
		'block_next'	: nextId,
		'block_prev'	: id2node[nextId]['block_prev'], 
		'block_parent'	: id2node[nextId]['block_parent']
	}
	if id2node[nextId]['block_prev'] != None:
		block_prev_id = id2node[nextId]['block_prev']
		id2node[block_prev_id]['block_next'] = id
	id2node[nextId]['block_prev'] = id

def add_tnode_after(id2node, prevId, id):
	if id in id2node:
		print("Error: duplicated id: %d" % id)
		sys.exit(-1)
	id2node[id] = {
		'name'		: 'table'+str(id), 
		'id'		: id, 
		'key'		: [{'match_type': str(id)}], 
		'actions'	: [], 
		'myId'		: 't'+str(id), 
		'block_next'	: id2node[prevId]['block_next'], 
		'block_prev'	: prevId, 
		'block_parent'	: id2node[prevId]['block_parent']
	}
	if id2node[prevId]['block_next'] != None:
		block_next_id = id2node[prevId]['block_next']
		id2node[block_next_id]['block_prev'] = id
	id2node[prevId]['block_next'] = id

def rec_find_parent_prev_id(id2node, id):
	cur_id = id
	while cur_id != None and id2node[cur_id]['block_prev'] == None:
		cur_id = id2node[cur_id]['block_parent']
	if cur_id != None:
		dstId = id2node[cur_id]['block_prev']
	else:
		print("Error: rec_find_parent_prev shouldn't get None")
		sys.exit(-1)
	return dstId


def add_cnode_before(id2node, nextId, id):
	block_parent = id2node[nextId]['block_parent']
	block_size = 1
	cur = nextId
	while id2node[cur]['block_next'] != None:
		cur = id2node[cur]['block_next']
		block_size += 1

	false_node_loc = random.randint(1, block_size)
	block_next_loc = random.randint(1, block_size)
	if false_node_loc > block_next_loc:
		temp = false_node_loc
		false_node_loc = block_next_loc
		block_next_loc = temp
	cur = nextId
	loc = 1
	false_node = None
	block_next = None
	id2node[cur]['block_parent'] = id
	while id2node[cur]['block_next'] != None:
		cur = id2node[cur]['block_next']
		if loc == block_next_loc:
			block_next = cur # leave false_node to be None
			break
		id2node[cur]['block_parent'] = id
		if loc == false_node_loc:
			false_node = cur
		loc += 1

	print("cnode's true:", nextId, "false:", false_node, "block_next:", block_next)

	id2node[id] = {
		'name='		: 'cond'+str(id), 
		'id'		: id, 
		'expression'	: {'type': 'hexstr', 'value':'0x01'+str(id)}, 
		'myId'		: 'c'+str(id), 
		'block_next'	: block_next, 
		'block_prev'	: id2node[nextId]['block_prev'], 
		'block_parent'	: block_parent, 
		'true_node'	: nextId, 
		'false_node'	: false_node
	}
	# between block_prev and cnode
	if id2node[nextId]['block_prev'] != None:
		block_prev = id2node[nextId]['block_prev']
		id2node[block_prev]['block_next'] = id
		id2node[nextId]['block_prev'] = None
	else:
		if block_parent != None:
			if id2node[block_parent]['true_node'] == nextId:
				id2node[block_parent]['true_node'] = id
			elif id2node[block_parent]['false_node'] == nextId:
				id2node[block_parent]['false_node'] = id
			else:
				print("Error: a nextId with no block_prev should always be a true_node or false_node of a cnode")
				sys.exit(-1)
		else:
			print("Error: all nextId node should have a parent")
			sys.exit(-1)
	# between last_true_node and first_false_node
	if false_node != None:
		last_true_node_id = id2node[false_node]['block_prev']
		id2node[false_node]['block_prev'] = None
		id2node[last_true_node_id]['block_next'] = None
	# between last_false_node and block_next
	if block_next != None:
		last_false_node_id = id2node[block_next]['block_prev'] # if false_node is None, this is actually last_true_node_id
		id2node[block_next]['block_prev'] = id
		id2node[last_false_node_id]['block_next'] = None
		
def rec_find_parent_next_myId(id2node, id):
	cur_id = id
	while cur_id != None and id2node[cur_id]['block_next'] == None:
		# print(cur_id)
		# print(id2node[cur_id])
		cur_id = id2node[cur_id]['block_parent']
	if cur_id != None:
		dstId = id2node[cur_id]['block_next']
		dstMyId = id2node[dstId]['myId']
	else:
		dstMyId = "s"
	return dstMyId


def synthetic_to_nxGraph(id2node):
	graph = nx.MultiDiGraph()
	for id in id2node:
		n = id2node[id]
		graph.add_nodes_from([(n['myId'], n)])
	graph.add_nodes_from([("s", {'myId': 's', 'name':'s'})])

	for id in id2node:
		src = id2node[id]
		if src['myId'][0] == 'r' or src['myId'][0] == 't':
			dstMyId = rec_find_parent_next_myId(id2node, id)
			graph.add_edges_from([(src['myId'], dstMyId, {'type': 'b_next'})])
		elif src['myId'][0] == 'c':
			trueNodeMyId = id2node[src['true_node']]['myId']
			graph.add_edges_from([(src['myId'], trueNodeMyId, {'type': 't_next'})])
			if src['false_node'] != None:
				falseNodeMyId = id2node[src['false_node']]['myId']
			else:
				falseNodeMyId = rec_find_parent_next_myId(id2node, id)
			graph.add_edges_from([(src['myId'], falseNodeMyId, {'type': 'f_next'})])
	return graph

def get_node_at(id2node, loc):
	count = 0
	for id in id2node:
		if id == 0: #skip root
			continue
		if count == loc:
			return id
		count += 1
	print("Error: loc", loc, "should be smaller than graph size", len(id2node), "minus 1")
	sys.exit(-1)
	return None

def gen_new_graph(idStart, size):
	id2node = {}
	id2node[0] = {'name': 'r', 'id': 0, 'myId': 'r0', 'block_next': None, 'block_prev': None, 'block_parent': None}
	idCount = idStart

	for i in range(0, size):
		graph_size = len(id2node)
		if i != 0:
			target = random.randint(0, 100)
			if target <= 70:
				loc = random.randint(0, graph_size-1)
				loc = 0 if loc == 0 else get_node_at(id2node, loc - 1)
				print("t", idCount, "after", loc)
				add_tnode_after(id2node, loc, idCount)
				idCount += 1
			else:
				loc = random.randint(0, graph_size-2)
				loc = get_node_at(id2node, loc)
				print("c", idCount, "before", loc)
				add_cnode_before(id2node, loc, idCount)
				idCount += 1
		else:
			print("t", idCount, "after", 0)
			add_tnode_after(id2node, 0, idCount)
			idCount += 1
	return (id2node, idCount)

def main():
	# random.seed(0)
	size = 10
	idCount = 1
	id2node, idCount = gen_new_graph(idCount, size)

	print("Create nxGraph...")
	graph = synthetic_to_nxGraph(id2node)
	#pos=nx.random_layout(graph)
	#pos=nx.kamada_kawai_layout(graph)
	#pos=nx.circular_layout(graph)
	pos=nx.planar_layout(graph)
	nx.draw(graph, node_size=5, with_labels=True)
	plt.savefig('foo3.pdf')
	print("Graph visualization output")

	editTimes = 1
	for i in range(0, editTimes):
		graphSize = len(id2node)
		target = random.randint(0, 100)
		if target <= 20:
			loc = random.randint(0, graph_size-1)
			origStartPrev = 0 if loc == 0 else get_node_at(id2node, loc - 1)
			origEndNext = origStartPrev
			origSize = 0
			added_subgraph, idCount = gen_new_graph(idCount, size)
			addedEndPrev = 0
			loc = len(added_subgraph)-1
			addedEndNext = get_nodes_at(added_subgraph, loc-1)
			print("Replace original's", origStartPrev, "'s next node to", origEndNext, "'s previous node with subgraph's",
				addedStartPrev, "'s next node to", addedEndNext "'s previous node")
			replace_subgraph_with(id2node, origStartPrev, origEndNext, added_subgraph, addedStartPrev, addedEndNext)
		elif target <= 30:
			loc = random.randint(0, graph_size-2)
			loc = get_node_at(id2node, loc)
			print("c", idCount, "before", loc)
			add_cnode_before(id2node, loc, idCount)
			idCount += 1
		elif target <= 70:
			loc = random.randint(0,idCount-1)
			origSize = random.randint(1, 5)
			newSize = random.randint(1, 5)
			id2node_new = gen_new_graph(idCount, newSize)
			print("t", idCount, "after", loc)
			replace(id2node, loc, id, size)
			idCount += 1

if __name__ == "__main__":
	print("Calling main()")
	main()

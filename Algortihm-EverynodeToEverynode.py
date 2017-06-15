import networkx as nx
import sys

#get folder containing the graph shapefiles
pathShape= raw_input("insert shapefile folder path:")
InitialGraph=nx.read_shp(pathShape)
G=InitialGraph.to_undirected()

attributeLength=nx.get_edge_attributes(G,'st_length')
#transform attribute length of the edge in time to travel it
for e,v,d in G.edges_iter(data=True):
	G.add_edge(e,v,time=(attributeLength[e,v]*51)/5594)

#initialize length function (length of shortest path will be calculated using dijkstra algorithm)
length=nx.all_pairs_dijkstra_path_length(G,cutoff=None, weight='time')
GraphPath=G

#add attribute totallength on each graph node and initialize it to 0
for n in GraphPath.nodes_iter():
	GraphPath.add_node(n,totalLength=0)

#get array containing the room names (nodes attribute)
shape=nx.get_node_attributes(GraphPath,'ShpName')

#start algorithm for every node
for node1,d in G.nodes_iter(data=True):
		for node2 in length[node1]:
			totalLength=nx.get_node_attributes(GraphPath,'totalLength')#get array totallength
			try: totalDis=totalLength[node2]+length[node1][node2] #add total length
			except KeyError: totalDis=length[node1][node2]#add total length for the first time
			GraphPath.add_node(node2,totalLength=totalDis)#assign totalLength

#search minor total length for every node
MinDistanceNode=0
MinDistance=100000000000000
totalLength=nx.get_node_attributes(GraphPath,'totalLength')
for n,d in GraphPath.nodes_iter(data=True):
	if totalLength[n]>1:
		if MinDistance>totalLength[n]: 
			MinDistance=totalLength[n]
			MinDistanceNode=n

#print out results
print "Node coordinates: "+str(MinDistanceNode)
print "Node total time: "+str(MinDistance)
import networkx as nx

path=raw_input("Insert shapefile folder path:")
InitialGraph=nx.read_shp(path)
G=InitialGraph.to_undirected()

attributeLength=nx.get_edge_attributes(G,'st_length')
#transform attribute length of the edge in time to travel it
for e,v,d in G.edges_iter(data=True):
	G.add_edge(e,v,time=(attributeLength[e,v]*51)/5594)

print 'Number of connected components: ' + str(nx.number_connected_components(G))
print 'Number of nodes: ' + str(nx.number_of_nodes(G))
print 'Number of edges: ' + str(nx.number_of_edges(G))
print 'Average degree: ' + str(float(sum(G.degree().values()))/float(G.number_of_nodes()))
print 'Density: ' + str(nx.density(G))
print 'Biconnected: ' + str(nx.is_biconnected(G))
#print 'Degree centrality: ' + str(nx.degree_centrality(G))
if not G.is_directed():
	print 'Average clustering coefficient (weight): ' + str(nx.average_clustering(G, weight='time'))
if nx.number_connected_components(G)==1:
	print 'Average shortest path length (weight): ' + str(nx.average_shortest_path_length(G, weight='time'))
print 'Average degree connectivity (weight): ' + str(nx.average_degree_connectivity(G, weight='time'))
print 'Betweenness centrality ' + str(nx.betweenness_centrality(G, weight='time'))

# From Planimetry to Graph - A First Step Towards the Implementation of an Efficient AED Program

## 1. SPATIAL QUERIES 

It has been assumed that the machine, which will run the script, has an available PostgreSQL database which contains a PostGIS installation.

The transformation from shapefiles into graphs has been thought in order to make the **GraphGenerator.py** script work on as many different planimetries as possible. However, it was impossible for the first queries to predict the field names of the input planimetry. Then, some arrangements are needed before running the script such as checking and adapting the queries responsible for the import of the shapefile fields into the dataset.

The script life-cycle can be summarized in three main steps:

1. Importing the filtered input shapefile into a PostgreSQL database.

2. Performing spatial queries on the just imported fields in order  to create two different views that will describe the graph, i.e. edges and nodes.

3. Exporting the views into two shapefiles, i.e. edges (lines) and nodes (points).

In particular this chapter is focused on the creation of the two views through spatial queries, explaining step by step their functionalities.

The first two queries filter the shapefiles fields in order to import into the database (“lines” and “points” tables) only useful data such as lines of the walls, doors and description points. Points are used to get information about the geometric shapes mapped by the lines, for example to know whether a shape represents a room or a corridor.

Note that there was the possibility to easily import all the shapefile fields into the dataset, but since a planimetry contains lot of useless information, especially coming from AutoCAD projects, the resulting database would be confused, making more difficult the development of next steps.

![image](https://user-images.githubusercontent.com/24565161/27175994-4169cd86-51c1-11e7-90f6-9a375a42ecb7.png)

Therefore, an effort has been made also for filter the shapefiles in the best and most minimal way.

Once created the two main tables “lines” and “points”, the script continues by selecting polygons resulting from the table “lines” and saves them into a new view. These polygons are labeled by using the points name that are contained into them. For reasons of simplifications, the script differentiates polygons only in two particular main classes: room and corridor.

Then, medial axis and centroids of the polygons are calculated. Centroids are used in the next steps of the algorithm as rooms references. On the other hand, medial axis are created in order to draw the graph edges represented by the corridor. Medial axis could be also useful in next upgrade of the project to retrieve more detailed information about the rooms structure.

![image](https://user-images.githubusercontent.com/24565161/27176041-64c96584-51c1-11e7-8cb5-e3da3e0e3a62.png)

At this point, the rooms and their property are defined but, in order to create the graph, there is the need to define the connection between them.

The biggest challenge for this part was to find and develop a general method, valid for every planimetry, in order to get the connection between the rooms each others, which means finding for each room its rooms neighbors. This is also the most important query of the project in fact it is the one that will define the graph structure.

The solution has been to extend the length of the doors lines, making sure that this line will intersect the room where the door actually leads. In this way, the room that contains the door and the room, or corridor, which intersects the extended door line, are neighbors.

Once found all the neighbors for each room, other queries are used in order to create the connections between the rooms centroids and their neighbors’ centroids.

For rooms that are instead connected to the corridor, the connections created are between the rooms centroids and the medial axis of the corridor.

At this point, the resulting views will represent a graph, where points represent rooms whereas lines represent edges. The figure gives an example regarding the resulting graph for FBK west building first floor’s planimetry.

![image](https://user-images.githubusercontent.com/24565161/27176085-89f0b7e0-51c1-11e7-9a36-20e964bd3fae.png)

As it can be noted, one of the problems of the graph is that the corridor is represented by only edges. Which means that, next functions would manage corridors as edges and not as nodes. This behavior could have compromised the success of the functions present in the second python script, since the algorithms based on graph data structures use only nodes as sensible points (start and end points).

The corridors has been therefore segmented in different parts, creating nodes where are presents the changes of directions thereof.

![image](https://user-images.githubusercontent.com/24565161/27176119-a9b2999a-51c1-11e7-94cf-9546adb77232.png)

Next queries are used to weight the edges created. Weight has been recorded as lines attribute.

The time required to walk an edge at medium speed was used as weight. This choice has been made because the distances present in the planimetry as lines information were not described using a unity measure but just by numbers, making impossible a conversion in meters without measure manually some corridors. However, the travel-time has been also clocked manually, but it was simpler for us to calculate it and to create a number/time conversion formula.

This formula could change for every different planimetry used based on the distance information present on it, then in order to simplify this possible modification, has been specifically created a python script that will convert the planimetry distance to any weight desired, by modifying the conversion formula.
Finally, last queries are used to filter the view resulted in order to clean the results.
The two views created are then extrapolated by the script in two different shapefiles which describe the planimetry graph: lines and points.

### Observations and possible optimizations

A possible optimization for this script could be improving the way in which the graph is weighted. In fact, in our case the graph is weighted based only on the length of the edges, without cover the facility or the speed in which an edge could be walked.

In addition, the algorithm does not support multiple floors planimetries, therefore does not take into account stairs or elevators. Currently, there is the need to execute the script on each floor separately, and then connect manually the graphs resulting in order to get a unique graph of a planimetry describing a building with multiple floors.

Anyway we advice to check every time the graph created by the script looking for some possible bugs due to planimerty errors or shortcomings.

## 2. ALGORITHMS

The goal of this scripts is to find the closest node to all other nodes present in an input graph represented by shapefiles. This node will define the optimal location where to position the semi-Automated External Defibrillator (AED) in a planimetry. However, it is easy to imagine for how many purpose this algorithm could be useful.

Since the project is centered on planimetries, it has been supposed that the graph will be undirected. However the algorithm could work also on directed graphs.

For this algorithm has been developed three different variants:

1. The first variant (**Algortihm-RoomToRoom.py**) calculates the closest node using as start and end nodes only the “rooms nodes”. This basically means that the algorithm calculates the output node taking into account only room-to-room paths. The resulting point will also be a room;

2. The second one (**Algortihm-EverynodeToRoom.py**) calculates the closest node using as start points both rooms and corridors nodes and as end point only room nodes. This means that it calculates the output node taking into account room-to-room and corridor-to-room paths. The resulting point will be a room;

3. Finally, the third one (**Algortihm-EverynodeToEverynode.py**) calculates the closest node using as start and end points both rooms and corridors nodes. Meaning that the algorithm calculates the output node taking into account room-to-room, room-to-corridor and corridor-to-corridor paths. The resulting point may be either a room or a corridor node.

These three variations have been developed in order to adapt the algorithm to the building needs. For example, if the AED can be located only in a room, the algorithm to use will be the second in the list, whereas, if the AED could be positioned everywhere then it will be used the third one.

Anyway, the scripts life-cycle for these three variants is basically the same and it has been summarized in four main steps

1. Importing and reading the graph shapefiles;

2. Initializing the graph;

3. Executing the algorithm;

4. Searching and printing out the result.

![image](https://user-images.githubusercontent.com/24565161/27176319-5a2fe17e-51c2-11e7-8e74-7b1a933c32d5.png)

### Import and reading the graph shapefiles

The free software python library [NetworkX](https://networkx.github.io/) has been used to process the graph.

NetworkX is a python language software package for the creation, manipulation, and study of the structure, dynamics, and functions of complex networks.

The import of the graph from shapefiles is handled through the read_shp() NetworkX function. This function generates a DiGraph class from shapefiles by translating point geometries into nodes and lines into edge. This function saves also the shapefile attributes, such as the weight or the name of lines and points.

### Initialization

The initialization consist in adding for each node a new attribute called “totalLength” and to initialize it to 0 in Lines 1-3 “totalLength” attribute is used to save the weight of the total path between two nodes in the destination node.

Since the algorithm will run a shortest path function starting from each node to all the others, the “totalLength” of a node will result the sum of the distance of all the nodes from the node itself in Line 6

### Algorithm execution

The algorithms executes, from each node, the Dijkstra’s shortest-path processed by the NetworkX all_pairs_dijkstra_path_length() function to all the other nodes present in the graph. As already mentioned, for every path calculated, it will be added the path weight just calculated in the “totalLength” attribute of the destination node of the path in Lines 4-8

### Searching and printing out the result

Finally the algorithm search the node which have the lowest “totalLength” attribute value. This node will be the closest node to all other nodes. At this time, the script will print out this node and its “total length” value in Line 9.

Since the algorithm save for every node its total length, we can easily know the n-nearest nodes to all the others by just searching the n nodes that have the lowest “totalLength” values.

### Observations and possible optimizations

For the algorithm implementations has not been thought about speed optimizations, in fact the execution time is equal to O(V^2E + V^3logV) where V represent the number of nodes contained in the graph and E the number of edges. However, planimetries do not usually contain such a large number of rooms that could make an important difference in term of running time.

Procedure | Complexity | Lines
--- | --- | --- |
Initialization |O(V) | 1 - 3
Nested cycles | O(V^2) | 4 - 8 (not 6)
Dijkstra’s Shortest Path | O(E + VlogV) | 6
Search Min totalLength | O(V) | 9
Total | O(V^2E + V^3logV) | 4 - 8

In addition, it was not taken into consideration some variables that could have a considerable significance for our AED goal such as the different concentration of rooms in different parts of the graph and the number of people present in each rooms. In fact, if a single room that contains just a small number of people is far away from all the others, this room will affect the algorithm result in the same way of other “more significant” rooms.

## 3. MEASURES

Finally, we created a simple python script (**GraphMeasures.py**) to extract few meaningful measures that characterize the output graph. We compare the output graph of the FBK first floor west building, after (A04) and before the manual refinement (A04-refined) where all nodes not connected to the main graph were removed. The results are shown in the following table.

Graph | Connected components	| Nodes	| Edges |	Average degree | Density	| Bi-connected	| Average path length
 --- | --- | --- | --- | --- | --- | --- | --- |
**A04** | 16	|251	| 308	|2,4541	| 0,0098	| False	| /
**A04-refined** | 1	| 228	| 300	| 2,6315	| 0,0116	| False	| 33,19

We manually removed all nodes which were not connected to the main corridor. However, the output graph has a plenty of nodes and edges, that is because the corridor is split in different parts and linked to one another by a node. The average degree of the graph, where the degree of a vertex of a graph is the number of edges incident to the vertex, prove that most of the room of the build are connected only with the corridor. This data is confirmed by the bi-connectivity and density (number of nodes divided by number of edges).

Moreover, another interesting measure is represented by the average shortest path length weighted by the time spent to travel an edge. This measure shows that average time to go from a node to another is 33,19 seconds. This measure can be calculated only if the graph is connected, for this reason we removed the disconnected nodes.

Finally, we found the betweenness centrality for each node of the refined graph (A04-refined). The betweenness centrality gives higher centralities to nodes that are on many shortest paths of other node pairs. In our case, the nodes with higher centralities are mainly located on the lower part of the graph, in the middle of the corridor. This information matches the result of our algorithm proving its correctness.

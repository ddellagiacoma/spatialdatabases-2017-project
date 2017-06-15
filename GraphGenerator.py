import psycopg2
import os,sys
import osgeo.ogr
import shapely
import shapely.wkt

#connection to postgres db 
connection = psycopg2.connect(database="<database-name>",user="<database-user>", password="<database-password>", host="<database-host>")
cursor = connection.cursor()
 
#delete tables in the case that the script has already been run 
cursor.execute("DROP TABLE IF EXISTS lines")
cursor.execute("DROP TABLE IF EXISTS points")

#create table for lines
cursor.execute("CREATE TABLE lines (gid INT PRIMARY KEY , layer VARCHAR, subclasses VARCHAR, extendeden VARCHAR DEFAULT NULL,linetype VARCHAR DEFAULT NULL ,entityhand VARCHAR,text VARCHAR DEFAULT NULL, geom GEOMETRY)")

#create table for points
cursor.execute("CREATE TABLE points (gid INT PRIMARY KEY , layer VARCHAR, subclasses VARCHAR, extendeden VARCHAR DEFAULT NULL,linetype VARCHAR DEFAULT NULL ,entityhand VARCHAR,text VARCHAR DEFAULT NULL, geom GEOMETRY)")

cursor.execute("SELECT postgis_full_version();")

connection.commit()

#get the lines shapefile to import
path= os.path.dirname(os.path.realpath(sys.argv[0]))+"/"

nameShape= raw_input("Insert shapefile name:")
totalPath=path+nameShape
shapefile = osgeo.ogr.Open(totalPath)
layer = shapefile.GetLayer(0)

#populate table getting lines-data from the shapefile just imported
cursor.execute("DELETE FROM lines")
for i in range(layer.GetFeatureCount()):
	feature = layer.GetFeature(i)
	layer2 = feature.GetField("Layer")
	entityhand = feature.GetField("EntityHand")
	subclasses = feature.GetField("SubClasses")
	extendeden= feature.GetField("ExtendedEn")
	text= feature.GetField("Text")
	linetype= feature.GetField("Linetype")
	geom = feature.GetGeometryRef()
	cursor.execute("INSERT INTO lines (gid, layer, subclasses, extendeden,linetype, entityhand, text, geom) VALUES ({},'{}','{}', '{}', '{}', '{}', '{}', ST_GeomFromText('{}'))".format(i,layer2, subclasses, extendeden, linetype, entityhand, text, geom))


#get the points shapefile to import
shapefile = osgeo.ogr.Open("/home/hduser/spatial_database/shape_dxf/piano2/punti.shp")
layer = shapefile.GetLayer(0)

#populate table getting lines-data from the shapefile just imported
cursor.execute("DELETE FROM points")
for i in range(layer.GetFeatureCount()):
	feature = layer.GetFeature(i)
	layer2 = feature.GetField("Layer")
	entityhand = feature.GetField("EntityHand")
	subclasses = feature.GetField("SubClasses")
	extendeden= feature.GetField("ExtendedEn")
	text= feature.GetField("Text")
	linetype= feature.GetField("Linetype")
	geom = feature.GetGeometryRef()
	cursor.execute("INSERT INTO points (gid, layer, subclasses, extendeden,linetype, entityhand, text, geom) VALUES ({},'{}','{}', '{}', '{}', '{}', '{}', ST_GeomFromText('{}'))".format(i,layer2, subclasses, extendeden, linetype, entityhand, text, geom))

#filter the lines table to get just useful data and create a view with these data
cursor.execute("SELECT layer::text FROM lines WHERE layer LIKE '%superfici_attuali_perimetro%' GROUP BY layer")
lays = cursor.fetchall()
i=1
for lay in lays:
	i=i+1
	if (lay!=('PT_N d-s superfici attuali perimetro',) and lay!=('PT_N d-s superfici attuali perimetro bar',)):

		cursor.execute("CREATE OR REPLACE VIEW primo_piano_stanze AS WITH bordi_stanze AS (SELECT row_number() OVER () AS gid,st_linemerge(lines.geom) AS geom FROM lines WHERE lines.layer::text = %s::text ), polygons AS (SELECT bordi_stanze.gid, st_makepolygon(bordi_stanze.geom) AS geom FROM bordi_stanze), corridoio AS (SELECT poly.gid,poly.geom FROM polygons poly,( SELECT points.gid,points.layer,points.subclasses,points.extendeden,points.linetype,points.entityhand,points.text,points.geom FROM points  WHERE points.text::text ~~* '%%corridoio%%'::text) p WHERE st_contains(poly.geom, p.geom)), stanze AS (SELECT poly.gid,'stanza'::text AS tipo,poly.geom FROM polygons poly WHERE NOT (poly.gid IN ( SELECT corridoio.gid FROM corridoio))) SELECT max(corridoio.gid) AS gid,'corridoio'::text AS tipo, st_union(corridoio.geom) AS geom FROM corridoio UNION SELECT stanze.gid,stanze.tipo,stanze.geom FROM stanze",(lay))

		#query used to get the centroid of the rooms
		#create and get poligon of the rooms
		#get centroid of the polygons
		cursor.execute("CREATE OR REPLACE VIEW primo_piano_stanze_centroidi AS SELECT primo_piano_stanze.gid AS stanza_id,row_number() OVER () AS id, st_centroid(primo_piano_stanze.geom) AS geom FROM primo_piano_stanze WHERE primo_piano_stanze.tipo = 'stanza'::text;")

		#create output folder
		if not os.path.exists(path+"output"):
			os.makedirs(path+"output")

		# start creation view of the centroids
		output = path+"output/nodes"+str(i)+".shp"

		out_driver = osgeo.ogr.GetDriverByName( 'ESRI Shapefile' )
		out_ds = out_driver.CreateDataSource(output)
		out_srs = None
		out_layer = out_ds.CreateLayer("centroidi", out_srs, osgeo.ogr.wkbPoint)
		out_layer.CreateField(osgeo.ogr.FieldDefn("stanza_id", osgeo.ogr.OFTInteger))
		out_layer.CreateField(osgeo.ogr.FieldDefn("id", osgeo.ogr.OFTInteger))

		cursor.execute("SELECT ST_AsText(geom) as geom,stanza_id,id FROM primo_piano_stanze_centroidi")
		rows = cursor.fetchall()
		for row in rows:
			feature = osgeo.ogr.Feature(out_layer.GetLayerDefn())
			feature.SetField("stanza_id", row[1])
			feature.SetField("id", row[2])
			geom= osgeo.ogr.CreateGeometryFromWkt(row[0])
			feature.SetGeometry(geom)
			out_layer.CreateFeature(feature)
			feature = None
		# end creation view of the centroids

		connection.commit()    


		#start creation of views used in order to get the connection between rooms each other and room-corridors
		#get the medial axis of the floor
		cursor.execute("CREATE OR REPLACE VIEW primo_piano_medial_axis AS SELECT row_number() OVER () AS id,st.gid AS stanza_id,tipo,st_approximatemedialaxis(st.geom) AS geom FROM primo_piano_stanze st;")

		#get the medial axis of the corridor
		cursor.execute("CREATE OR REPLACE VIEW medial_axis_corridoio AS SELECT row_number() OVER () AS id, st.gid AS stanza_id,ST_ApproximateMedialAxis(st.geom) AS geom FROM primo_piano_stanze st WHERE st.tipo LIKE 'corridoio';")

		#transform from multiline to single line the corridor medial axis 
		cursor.execute("CREATE OR REPLACE VIEW corridoio_single_line AS SELECT row_number() OVER () AS id,(st_dump(medial_axis_corridoio.geom)).geom AS the_geom FROM medial_axis_corridoio GROUP BY medial_axis_corridoio.id, ((st_dump(medial_axis_corridoio.geom)).geom);")

		#find the neighboring rooms
		cursor.execute("CREATE OR REPLACE VIEW vicini_tra_stanze AS WITH lati_porte AS (   SELECT row_number() OVER () AS id,   c.geom,   c.geomc   FROM primo_piano_stanze st,   ( SELECT st_centroid(unnest(st_clusterintersecting(st_buffer(l1.geom, 0.03::double precision)))) AS geomc,     l1.geom1 AS geom     FROM ( SELECT l.gid,       l.layer,       l.subclasses,       l.extendeden,       l.linetype,       l.entityhand,       l.text,       l.geom,       st_linemerge(l.geom) AS geom1       FROM lines l       WHERE l.layer::text LIKE '%porte%'::text AND l.subclasses::text = 'AcDbEntity:AcDbLine'::text AND st_length(l.geom) > 0.5::double precision) l1     GROUP BY l1.geom1) c  ), data_porte AS (   SELECT st_startpoint(lati_porte.geom) AS s,   st_endpoint(lati_porte.geom) AS e,   st_azimuth(st_startpoint(lati_porte.geom), st_endpoint(lati_porte.geom)) AS az1,   st_azimuth(st_endpoint(lati_porte.geom), st_startpoint(lati_porte.geom)) AS az2,   st_length(lati_porte.geom) + 0.3::double precision AS length,   lati_porte.geomc   FROM lati_porte  ), extended_line AS (   SELECT st_makeline(data_porte.s, st_translate(data_porte.e, sin(data_porte.az2) * data_porte.length, cos(data_porte.az2) * data_porte.length)) AS geom,   data_porte.geomc   FROM data_porte  ) SELECT DISTINCT p1.gid AS gid1, p2.gid AS gid2, el.geomc, p1.tipo AS tipo1,p2.tipo AS tipo2 FROM extended_line el, primo_piano_stanze p1, primo_piano_stanze p2 WHERE st_intersects(el.geom, p1.geom) AND st_intersects(el.geom, p2.geom) AND p1.gid < p2.gid ORDER BY p1.gid, p2.gid;")

		#create lines between each rooms neighbors found in the previous query
		cursor.execute("CREATE OR REPLACE VIEW collegamenti AS SELECT row_number() OVER () AS id, st_makeline(c.geom, v.geomc) AS geom FROM primo_piano_stanze_centroidi c, vicini_tra_stanze v WHERE v.gid1 = c.stanza_id OR v.gid2 = c.stanza_id;")

		#find rooms connected directly with the corridor
		cursor.execute("CREATE OR REPLACE VIEW corridoio_collegamenti AS SELECT row_number() OVER () AS id, st_makeline(v2.geomc, st_closestpoint(a.geom, v2.geomc)) AS st_makeline, st_endpoint(st_makeline(v2.geomc, st_closestpoint(a.geom, v2.geomc))) AS endpoint FROM vicini_tra_stanze v2, primo_piano_medial_axis a WHERE a.tipo LIKE 'corridoio' AND (v2.tipo1 LIKE 'corridoio'  OR v2.tipo2 LIKE 'corridoio');")

		#create lines as connection between rooms and corridor foundin the previous query
		cursor.execute("CREATE OR REPLACE VIEW collegamenti_stanze_corridoio AS SELECT corridoio_collegamenti.id, st_linemerge(corridoio_collegamenti.st_makeline) AS st_linemerge FROM corridoio_collegamenti;")

		#find endpoints of medial axis corridoio, calculate and create the line as connection between rooms and finally finds their endpoints
		cursor.execute("CREATE OR REPLACE VIEW endpoint_stanze_e_corridoio AS SELECT row_number() OVER () AS id, final.st_makeline, final.endpoint FROM ( SELECT st_makeline(v2.geomc, st_closestpoint(a.geom, v2.geomc)) AS st_makeline, st_endpoint(st_makeline(v2.geomc, st_closestpoint(a.geom, v2.geomc))) AS endpoint FROM vicini_tra_stanze v2, primo_piano_medial_axis a WHERE a.tipo LIKE 'corridoio' AND (v2.tipo1 LIKE 'corridoio' OR v2.tipo2 LIKE 'corridoio') UNION SELECT cs.the_geom AS st_makeline, st_endpoint(cs.the_geom) AS endpoint FROM corridoio_single_line cs UNION SELECT cs.the_geom AS st_makeline, st_startpoint(cs.the_geom) AS endpoint FROM corridoio_single_line cs) final;")
		#endcreation of views used in order to get the connection between rooms each other and room-corridors


		#start creation views used to split the corridor in more detailed pieces and find the new endpoints, and than, for each endpoint find his endpoint neighbors 
		#split the corridor,find endpoints, and find enpoint neighbors located on the same corridor's piece
		cursor.execute("CREATE OR REPLACE VIEW collegamenti_corridoio_sulla_stessa_riga AS SELECT final.id, final.endpoint1, final.endpoint2, final.distance,final.geom_line FROM ( SELECT row_number() OVER () AS id, tab3.row_number2, tab3.row_number, tab3.float1, tab3.collegamento1,tab3.endpoint1, tab3.float2, tab3.collegamento2, tab3.endpoint2,tab3.geom_line, tab3.distance FROM ( SELECT row_number() OVER (PARTITION BY tab2.geom_line, tab2.float1 ORDER BY (tab2.float1 - tab2.float2) DESC) AS row_number2, tab2.row_number, tab2.float1, tab2.collegamento1, tab2.endpoint1, tab2.float2, tab2.collegamento2,tab2.endpoint2, tab2.geom_line, tab2.distance FROM ( SELECT tab.row_number, tab.float1, tab.collegamento1, tab.endpoint1, tab.float2, tab.collegamento2,tab.endpoint2, tab.geom_line, tab.distance FROM ( SELECT row_number() OVER (PARTITION BY a.geom_line, a.floatonline ORDER BY (a.floatonline - b.floatonline)) AS row_number, a.floatonline AS float1, a.collegamentoid AS collegamento1, a.endpoint AS endpoint1, b.floatonline AS float2, b.collegamentoid AS collegamento2, b.endpoint AS endpoint2, b.geom_line, a.floatonline - b.floatonline AS distance FROM ( SELECT row_number() OVER () AS id, endpoint_stanze_e_corridoio.endpoint, st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint) AS floatonline, endpoint_stanze_e_corridoio.id AS collegamentoid, prova.the_geom AS geom_line FROM endpoint_stanze_e_corridoio, ( SELECT corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint FROM corridoio_single_line, endpoint_stanze_e_corridoio endpoint_stanze_e_corridoio_1 WHERE st_intersects(corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint) = true) prova WHERE prova.endpoint = endpoint_stanze_e_corridoio.endpoint ORDER BY prova.the_geom, (st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint))) a,( SELECT row_number() OVER () AS id, endpoint_stanze_e_corridoio.endpoint, st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint) AS floatonline, endpoint_stanze_e_corridoio.id AS collegamentoid, prova.the_geom AS geom_line FROM endpoint_stanze_e_corridoio, ( SELECT corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint FROM corridoio_single_line, endpoint_stanze_e_corridoio endpoint_stanze_e_corridoio_1 WHERE st_intersects(corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint) = true) prova WHERE prova.endpoint = endpoint_stanze_e_corridoio.endpoint ORDER BY prova.the_geom, (st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint))) b WHERE b.geom_line = a.geom_line AND (a.floatonline - b.floatonline) > 0::double precision ORDER BY b.geom_line, (a.floatonline - b.floatonline)) tab WHERE tab.row_number = 1 UNION SELECT tab.row_number, tab.float1, tab.collegamento1, tab.endpoint1, tab.float2, tab.collegamento2, tab.endpoint2, tab.geom_line, tab.distance FROM ( SELECT row_number() OVER (PARTITION BY a.geom_line, a.floatonline ORDER BY (a.floatonline - b.floatonline)) AS row_number, a.floatonline AS float1, a.collegamentoid AS collegamento1, a.endpoint AS endpoint1, b.floatonline AS float2, b.collegamentoid AS collegamento2, b.endpoint AS endpoint2, b.geom_line, a.floatonline - b.floatonline AS distance FROM ( SELECT row_number() OVER () AS id, endpoint_stanze_e_corridoio.endpoint, st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint) AS floatonline, endpoint_stanze_e_corridoio.id AS collegamentoid, prova.the_geom AS geom_line FROM endpoint_stanze_e_corridoio, ( SELECT corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint FROM corridoio_single_line, endpoint_stanze_e_corridoio endpoint_stanze_e_corridoio_1 WHERE st_intersects(corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint) = true) prova WHERE prova.endpoint = endpoint_stanze_e_corridoio.endpoint ORDER BY prova.the_geom, (st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint))) a, ( SELECT row_number() OVER () AS id, endpoint_stanze_e_corridoio.endpoint, st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint) AS floatonline, endpoint_stanze_e_corridoio.id AS collegamentoid, prova.the_geom AS geom_line FROM endpoint_stanze_e_corridoio, ( SELECT corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint FROM corridoio_single_line, endpoint_stanze_e_corridoio endpoint_stanze_e_corridoio_1 WHERE st_intersects(corridoio_single_line.the_geom, endpoint_stanze_e_corridoio_1.endpoint) = true) prova WHERE prova.endpoint = endpoint_stanze_e_corridoio.endpoint ORDER BY prova.the_geom, (st_linelocatepoint(prova.the_geom, endpoint_stanze_e_corridoio.endpoint))) b WHERE b.geom_line = a.geom_line AND (a.floatonline - b.floatonline) = 0::double precision ORDER BY b.geom_line, (a.floatonline - b.floatonline)) tab WHERE tab.row_number = 1) tab2) tab3 WHERE tab3.row_number2 = 1) final;")

		#calculate distance of each pair of neighbors on the same corridor piece just found
		cursor.execute("CREATE OR REPLACE VIEW collegamenti_corridoio_sulla_stessa_riga_con_distanza AS SELECT collegamenti_corridoio_sulla_stessa_riga.id, collegamenti_corridoio_sulla_stessa_riga.endpoint1, collegamenti_corridoio_sulla_stessa_riga.endpoint2, st_length(collegamenti_corridoio_sulla_stessa_riga.geom_line) * collegamenti_corridoio_sulla_stessa_riga.distance AS distance FROM collegamenti_corridoio_sulla_stessa_riga;")

		#find the corridor endpoint neighbors of endpoints situated on different corridor's pieces, calculate also the distance between each pair of neighbor just found
		cursor.execute("CREATE OR REPLACE VIEW collegamenti_corridoio_su_righe_diverse_con_distanza AS SELECT row_number() OVER () AS id, tab1.endpoint AS endpoint1, tab2.endpoint AS endpoint2, tab1.id * 0 AS distance FROM endpoint_stanze_e_corridoio tab1 JOIN endpoint_stanze_e_corridoio tab2 ON st_intersects(tab1.endpoint, tab2.endpoint) AND st_equals(tab1.st_makeline, tab2.st_makeline) = false AND tab1.id > tab2.id;")

		#union of the neighbors of the same corridor pieces (with length) with the neighbors of different corridor pieces (with length) (union of the result of the last 3 query)
		cursor.execute("CREATE OR REPLACE VIEW collegamenti_corridoio_completo_con_distanza AS SELECT row_number() OVER () AS id, tab.endpoint1,tab.endpoint2, tab.distance FROM ( SELECT collegamenti_corridoio_sulla_stessa_riga_con_distanza.id, collegamenti_corridoio_sulla_stessa_riga_con_distanza.endpoint1, collegamenti_corridoio_sulla_stessa_riga_con_distanza.endpoint2, collegamenti_corridoio_sulla_stessa_riga_con_distanza.distance FROM collegamenti_corridoio_sulla_stessa_riga_con_distanza UNION SELECT collegamenti_corridoio_su_righe_diverse_con_distanza.id, collegamenti_corridoio_su_righe_diverse_con_distanza.endpoint1, collegamenti_corridoio_su_righe_diverse_con_distanza.endpoint2, collegamenti_corridoio_su_righe_diverse_con_distanza.distance FROM collegamenti_corridoio_su_righe_diverse_con_distanza) tab;")

		#create a line between each neighbros, recreating the corridor(avoiding in this way graphical problems of the planimetry)
		cursor.execute("CREATE OR REPLACE VIEW recreation_corridoio AS SELECT collegamenti_corridoio_completo_con_distanza.id, st_makeline(collegamenti_corridoio_completo_con_distanza.endpoint1, collegamenti_corridoio_completo_con_distanza.endpoint2) AS st_makeline FROM collegamenti_corridoio_completo_con_distanza;")
		#end creation views used to split the corridor in more detailed pieces and find the new endpoints, and than, for each endpoint find his endpoint neighbors 


		#start creation views used to filter the views created in order to get just the useful data in order to finally create the graph
		#get the useful data of the previous query calculating the distance of each line 
		cursor.execute("CREATE OR REPLACE VIEW distanza_corridoio AS SELECT recreation_corridoio.id, recreation_corridoio.st_makeline as geom, st_length(recreation_corridoio.st_makeline) AS st_length FROM recreation_corridoio;")

		#get the useful data of the connection between corridor and rooms and calculate the distance for each line
		cursor.execute("CREATE OR REPLACE VIEW distanza_collegamenti_corridoio AS SELECT collegamenti_stanze_corridoio.id, collegamenti_stanze_corridoio.st_linemerge as geom, st_length(collegamenti_stanze_corridoio.st_linemerge) AS st_length FROM collegamenti_stanze_corridoio;")

		#get the useful data of the connection between rooms each others and calculate the distance for each line
		cursor.execute("CREATE OR REPLACE VIEW distanza_collegamenti_camere AS SELECT collegamenti.id, collegamenti.geom , st_length(collegamenti.geom) AS st_length FROM collegamenti;")
		#end creation views used to filter the views created in order to get just the useful data in order to finally create the graph

		connection.commit()

  		#create shapefile for lines used to save the graph edges created 
		output = path+"output/edges"+str(i)+".shp"

		#define shapefile attributes
		out_driver = osgeo.ogr.GetDriverByName( 'ESRI Shapefile' )
		out_ds = out_driver.CreateDataSource(output)
		out_srs = None
		out_layer = out_ds.CreateLayer("edges", out_srs, osgeo.ogr.wkbLineString)
		out_layer.CreateField(osgeo.ogr.FieldDefn("id", osgeo.ogr.OFTInteger))
		out_layer.CreateField(osgeo.ogr.FieldDefn("st_length", osgeo.ogr.OFTInteger))

		#populate shapefile
		cursor.execute("SELECT ST_AsText(geom) as geom,id,st_length FROM distanza_collegamenti_camere UNION SELECT ST_AsText(geom) as geom,id,st_length FROM distanza_collegamenti_corridoio UNION SELECT ST_AsText(geom) as geom,id,st_length FROM distanza_corridoio")
		rows = cursor.fetchall()
		for row in rows:
			feature = osgeo.ogr.Feature(out_layer.GetLayerDefn())
			feature.SetField("id", row[1])
			feature.SetField("st_length", row[2])
			geom= osgeo.ogr.CreateGeometryFromWkt(row[0])
			feature.SetGeometry(geom)
			out_layer.CreateFeature(feature)
			feature = None

		connection.commit()    
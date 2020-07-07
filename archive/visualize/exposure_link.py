
import geopandas as gpd
import contextily as ctx
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import LineString
from shapely.wkt import loads
from math import inf

from icarus.util.sqlite import SqliteUtil


database = SqliteUtil('database.db')


query = '''
    SELECT 
        link_id AS link,
        line, 
        COUNT(*) AS util
    FROM links
    INNER JOIN output_events
    USING(link_id) 
    GROUP BY link_id;
'''

database.cursor.execute(query)
data = database.cursor.fetchall()


links = []
minfreq = inf
maxfreq = 0

for link_id, line, util in data:
    geometry = LineString(loads(line))
    x, y = geometry.coords.xy
    if util > 200:
        util = 200
    maxfreq = max(maxfreq, util)
    minfreq = min(minfreq, util)
    if min(x) > 0.5e6 and max(x) < 0.85e6 and min(y) > 0.8e6 and max(y) < 1.0e6:
        maxfreq = max(maxfreq, util)
        minfreq = min(minfreq, util)
        links.append((link_id, util, geometry))
del data

df = pd.DataFrame(links, columns=('link_id', 'util', 'line'))
df['line'] = gpd.GeoSeries(df['line'], crs='EPSG:2223')

gpdf = gpd.GeoDataFrame(df, geometry='line', crs='EPSG:2223')
gpdf = gpdf.to_crs(epsg=3857)

fig, ax = plt.subplots(1, figsize=(20, 12))

plot = gpdf.plot(column='util', cmap='YlOrRd', linewidth=0.5, 
    ax=ax, alpha=1)

ax.set_title('Maricopa County Pedestrian & Bike Traffic',
    fontdict={'fontsize': '18', 'fontweight' : '3'})

ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

sm = plt.cm.ScalarMappable(cmap='YlOrRd', 
    norm=plt.Normalize(vmin=minfreq, vmax=maxfreq))
sm._A = []
cbar = fig.colorbar(sm)

fig.savefig('result/network_usage.png', bbox_inches='tight')


########################################


# query = '''
#     SELECT
#         nodes.point, 
#         MIN(COUNT(*), 200) AS util
#     FROM links
#     INNER JOIN output_events
#     USING(link_id)
#     INNER JOIN nodes
#     ON links.source_node = nodes.node_id 
#     GROUP BY link_id;
# '''

# database.cursor.execute(query)
# links = ((loads(point), util) for point, util in database.fetch_rows())

# df = pd.DataFrame(links, columns=('geometry', 'util'))
# df['geometry'] = gpd.GeoSeries(df['geometry'], crs='EPSG:2223')
# gdf = gpd.GeoDataFrame(df, geometry='geometry', crs='EPSG:2223')

# axes = gplt.kdeplot(gdf, cmap='Reds', shade=True, shade_lowest=True)
# plot = axes.get_figure()
# plot.savefig('result/network_usage.png', bbox_inches='tight')

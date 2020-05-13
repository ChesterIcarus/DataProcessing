
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import pandas as pd
from shapely.wkt import loads

from icarus.util.sqlite import SqliteUtil


def xy(point: str) -> tuple:
    return tuple(map(float, point[7:-1].split(' ')))


database = SqliteUtil('database.db')

query = '''
    SELECT
        centroid_id,
        temperature_id,
        temperature,
        center,
        region
    FROM centroids
    INNER JOIN temperatures
    USING(temperature_id)
    WHERE temperature_idx = 30;'''

database.cursor.execute(query)


data = database.cursor.fetchall()
centroids = []
vmin = 100
vmax = 0
for centroid_id, temperature_id, temperature, center, region in data:
    x, y = xy(center)
    polygon = loads(region)
    if x > 0.5e6 and x < 0.85e6 and y > 0.8e6 and y < 1.0e6:
        vmin = min(vmin, temperature)
        vmax = max(vmax, temperature)
        centroids.append((centroid_id, temperature_id, temperature, polygon))

del data

df = pd.DataFrame(centroids, 
    columns=('centroid_id', 'temperature_id', 'temperature', 'region'))
df['region'] = gpd.GeoSeries(df['region'], crs='EPSG:2223')

gpdf = gpd.GeoDataFrame(df, geometry='region', crs='EPSG:2223')
gpdf = gpdf.to_crs(epsg=3857)


fig, ax = plt.subplots(1, figsize=(20, 12))

plot = gpdf.plot(column='temperature', cmap='OrRd', linewidth=0, 
    ax=ax, edgecolor='0.8', alpha=0.5)

ax.set_title('Maricopa Temperatures (181, 15:00)',
    fontdict={'fontsize': '18', 'fontweight' : '3'})

ctx.add_basemap(plot, source=ctx.providers.Stamen.TonerLite)

sm = plt.cm.ScalarMappable(cmap='OrRd', 
    norm=plt.Normalize(vmin=vmin, vmax=vmax))
sm._A = []
cbar = fig.colorbar(sm)

fig.savefig('results/daymet_map.png', dpi=600, bbox_inches='tight')
from urllib.request import urlopen
import json

import geopandas


if __name__ == "__main__":
    print('Fetching NYC GeoJSON')
    url = 'https://raw.githubusercontent.com/veltman/snd3/master/data/nyc-neighborhoods.geo.json'
    with urlopen(url) as response:
        neighborhoods = json.load(response)

    neighborhood_df = geopandas.read_file(url)

    print('Reducing GeoJSON resolution')
    neighborhood_df['geometry'] = neighborhood_df['geometry'].simplify(.0005)

    print('Saving as csv')
    neighborhood_df.to_csv('data/neighborhood_geometry.csv', index=False)

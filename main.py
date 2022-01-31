"""Setup script.
This downloads all the necessary data and creates the necessary files to ensure
that all the notebooks work straight away.

Run this before the notebooks.

Before running this script, please fill in the env_vars.json file with the appropriate values.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import json
import geojson
import rasterio
import rasterio.mask

sys.path.append("forestry_yield_estimation")
import vistools, utils
from preprocessing import read_images, read_raw_polygons_data, get_catalog, get_aoi, load_environment_variables

pd.options.mode.chained_assignment = None

root = Path(".")
data_path = root / "data"

# Load environment variables to download images.
load_environment_variables("env_vars.json")

# Define subroutines
def produce_aois(data_path):
    for zone in ["south", "north"]:
        polygons, _ = read_raw_polygons_data(data_path, zone, offset_correction=(0, 0))
        
        # Get all the coords of polygons from the zone into a single array to extract bounding box
        coords = np.concatenate([
            np.array(np.concatenate(x)).squeeze()
            for x in polygons
        ])
        
        # Construct aoi as a table first
        aoi = pd.DataFrame({"min": coords.min(axis=0), "max": coords.max(axis=0)}, index=["easting", "northing"])
        aoi.loc["lon"], aoi.loc["lat"] = utils.utm_to_lonlat(aoi.loc["easting"], aoi.loc["northing"], epsg=32721)
        aoi["center"] = (aoi["max"] + aoi["min"])/2
        aoi["size"] = aoi["max"] - aoi["min"]
        
        print(f"ZONE: {zone}")
        print(aoi.applymap("{0:.5f}".format))
        print("")
        
        aoi.to_csv(data_path/f"aoi_{zone}.csv")
        aoi_json = {
            "type":"Polygon",
            "coordinates":[[
                [aoi.loc["lon", "min"],aoi.loc["lat", "min"]],
                [aoi.loc["lon", "min"],aoi.loc["lat", "max"]],
                [aoi.loc["lon", "max"],aoi.loc["lat", "max"]],
                [aoi.loc["lon", "max"],aoi.loc["lat", "min"]],
                [aoi.loc["lon", "min"],aoi.loc["lat", "min"]],
            ]]
        }
        aoi_json["center"] = np.mean(aoi_json["coordinates"][0][:4], axis=0).tolist()
        with open(data_path/f"aoi_{zone}.json", "w") as file:
            json.dump(aoi_json, file)

def download_crops(data_path):
    # Download south zone crops
    _ = get_catalog(data_path, "south", download_crops=True, start_date="2008-01-01", end_date="2018-12-31")
    # Download new_forest
    _ = get_catalog(data_path, "new_forest", download_crops=True, start_date="2008-01-01", end_date="2021-04-10")
    # Get an expanded catalog for the south zone, to have image ids used to restrict the montenativo crops we download.
    south_catalog = get_catalog(data_path, "south", download_crops=False, start_date="2008-01-01", end_date="2021-04-10")
    # Download Montenativo using those ids
    _ = get_catalog(data_path, "montenativo", download_crops=True, start_date="2008-01-01", end_date="2021-04-10", ids_to_keep=south_catalog["id"])

    return south_catalog

def save_montenativo(data_path):
    # Load images
    raw_images, filenames, srcs = read_images(data_path, "montenativo")
    images = np.log(raw_images)
    is_vv = np.array([f.endswith("vv") for f in filenames])

    # Load aoi as a polygon
    aoi_utm = get_aoi(data_path, "montenativo", convert_to_utm=True)
    offset_correction = (-40, 20)
    aoi_polygon = [
        [[easting + offset_correction[0], northing + offset_correction[1]] for easting, northing in sublist]
        for sublist in aoi_utm["coordinates"]
    ]
    mask, _, _ = rasterio.mask.raster_geometry_mask(srcs[0], [geojson.Polygon(aoi_polygon)], invert=True)
    masks = np.repeat(mask[np.newaxis, ...], len(images), axis=0)

    aggregated_backscatter = pd.DataFrame({
        "date": [f[:10] for f in filenames],
        "polarisation": ["vv" if vv else "vh" for vv in is_vv],
        "mean_backscatter": (images * masks).mean((1, 2)),
        "median_backscatter": np.median(images * masks, axis=(1, 2)),
    })
    aggregated_backscatter.to_csv(data_path/"montenativo.csv", index=False)


print("Producing aois for the north and south zone...")
produce_aois(data_path)

print("Downloading crops for the south, new_forest and montenativo zones...")
south_catalog = download_crops(data_path)

print("Extracting montenativo means and saving them to csv...")
save_montenativo(data_path)
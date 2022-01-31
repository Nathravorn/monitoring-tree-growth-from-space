from pathlib import Path
from datetime import datetime
import os
from timeit import default_timer as timer

import rasterio
import pandas as pd
import numpy as np
import geojson
import json
import tsd
from tqdm.auto import tqdm

from utils import utm_to_lonlat, lonlat_to_utm


def find_range_in_sorted_array(array, left_value, right_value=None):
    """Find indices where left_value <= array <= right_value.
    Leave right_value as None to find indices where array == left_value.
    Extremely fast thanks to binary search.
    """
    if right_value is None:
        right_value = left_value
    return np.arange(
        np.searchsorted(array, left_value),
        np.searchsorted(array, right_value, side="right")
    )


def filter_df_on_sorted_column(df, column, value):
    """Return a subset of the rows of a DataFrame where df[column] == value.
    df[column] MUST BE SORTED for this to work. This will not be checked.
    
    Args:
        df (pd.DataFrame): DataFrame to filter.
        column (str): Name of the column to filter on. `df` must be sorted by this column.
        value (object): Value to search for in the column.
    
    Returns:
        pd.DataFrame: Filtered DF.
    """
    return df.iloc[find_range_in_sorted_array(df[column], value), :]


def load_environment_variables(path):
    """Load environment variables from a json file.
    """
    with open(path, "r") as file:
        env_vars = json.load(file)
    
    for k, v in env_vars.items():
        os.environ[k] = v


def get_image_folder_path(data_path, zone):
    return Path(data_path) / "images" / zone


def get_polygons_file_path(data_path):
    return Path(data_path) / "polygons" / "export.geojson"


def get_points_file_path(data_path):
    return Path(data_path) / "points" / "export.csv"


def read_raw_points_data(data_path, epsg=32721):
    """Read raw points data (exported to csv from QGIS) and preprocess it.
    See the notebook "Raw data exploration" for explanations on some of the preprocessing.

    Args:
        data_path (str or Path): Path to the project data folder.
        epsg (int): UTM zone to use to project coords to lon-lat.
            Default: 32721.
    
    Returns:
        pd.DataFrame
    """
    path = get_points_file_path(data_path)
    df = pd.read_csv(path).rename(columns=str.lower)
    df = df.rename(columns={
        "x": "easting",
        "y": "northing",
        "vol_mdp8": "volume",
        "dcr_nucleo": "zone",
        "data_rodal": "plant_date",
        "edad": "age",
        "data_medic": "date",
        "g": "basal_area",
        "dapmed": "diameter",
        "htmed": "height",
        "htdom": "dominant_height",
    })

    # Process columns
    df["zone"] = df["zone"].replace("Pandule", "south").replace("Pdu Norte", "north")
    df["date"] = pd.to_datetime(df["date"], format="%Y/%m/%d")
    df["plant_date"] = pd.to_datetime(df["plant_date"], format="%Y/%m/%d")
    df["lon"], df["lat"] = utm_to_lonlat(df["easting"], df["northing"], epsg)
    df["pre_cut"] = df["programaci"].str.startswith("Pre Cosecha")

    # To distinguish between rodals with the same number in different zones,
    # we will set the rodals in the north to negative numbers.
    # This is because a rodal has no meaning without its associated zone,
    # since it represents a geographical unit.
    df.loc[df["zone"] == "north", "rodal"] *= -1

    # Select and order columns
    df = df[[
        "date",
        "zone",
        "rodal",
        "lon",
        "lat",
        "easting",
        "northing",
        "plant_date",
        "age",
        "volume",
        "diameter",
        "basal_area",
        "height",
        "dominant_height",
        "pre_cut",
        "objetivo",
        "nfustes",
        "nfustes8",
        "bloque",
    ]]

    return df


def read_raw_polygons_data(data_path, zone="south", offset_correction=(-40, 20)):
    """Read raw polygons data (exported to GeoJSON from QGIS) and preprocess it.

    Args:
        data_path (str or Path): Path to the project data folder.
        zone (str): "north" or "south". Which zone to get polygons for.
            Default: "south".
        offset_correction (2-tuple of numbers): (easting, northing) correction to apply to input
            polygon coordinates before returning.
            Default: (-40, 20).

    Returns:
        list: Read polygons.
        list: Corresponding "rodal" numbers.
    """
    path = get_polygons_file_path(data_path)

    # Read polygons
    with open(path, "r") as file:
        raw_polygons = geojson.load(file)

    polygons = []
    rodals = []
    for polygon in raw_polygons["features"]:
        # Only consider the selected zone
        if polygon["properties"]["NUCLEO"] != ("Pandule" if zone=="south" else "Paysandu Norte"):
            continue
        
        coords = polygon["geometry"]["coordinates"][0]
        # Apply offset correction
        coords = [
            [[easting + offset_correction[0], northing + offset_correction[1]] for easting, northing in sublist]
            for sublist in coords
        ]
        polygons.append(coords)
        rodals.append(int(polygon["properties"]["RODAL"]))

    return polygons, rodals


def get_aoi(data_path, zone, convert_to_utm=False, epsg=32721):
    """Read the aoi json file for a zone and optionally convert it to utm.
    Also add a "center" entry for ease of use.

    Args:
        data_path (str or Path): Path to the project data folder.
        zone (str): Which zone to get an aoi for (e.g. "north", "south", "new_forest", "montenativo").
        convert_to_utm (bool): Whether to convert the coordinates (which are in lonlat) to UTM.
            Default: False.
        epsg (int): EPSG used for conversion to UTM.
            Only used if convert_to_utm is set to True.
            Default: 32721.

    Returns:
        dict: aoi with keys "coordinates" and "center".
    """
    with open(data_path/f"aoi_{zone}.json", "r") as file:
        aoi = json.load(file)
    
    if convert_to_utm:
        lon, lat = zip(*aoi["coordinates"][0])
        e, n, _ = lonlat_to_utm(lon, lat, epsg)
        aoi["coordinates"] = [list(zip(e, n))]

        if "center" in aoi:
            lon, lat = aoi["center"]
            e, n, _ = lonlat_to_utm(lon, lat, epsg)
            aoi["center"] = [float(e), float(n)]

    if "center" not in aoi:
        aoi["center"] = np.mean(aoi["coordinates"][0][:4], axis=0).tolist()

    return aoi


def get_catalog(data_path, zone, download_crops=False, ids_to_keep=None, start_date="2008-01-01", end_date="2018-12-31"):
    """Use tsd to get an image catalog for the selected zone.
    Optionally download the corresponding images, or filter by id or date.

    Args:
        data_path (str or Path): Path to the project data folder.
        zone (str): Which zone to get a catalog for (e.g. "north", "south", "new_forest", "montenativo").
        convert_to_utm (bool): Whether to download the crops in the catalog to the appropriate image folder.
            Default: False.
        ids_to_keep (list of strings or None): Image ids to filter on.
            This can be used to ensure the crops downloaded are only extracted from certain source images.
            If None, no filtering is applied.
            Default: None.
        start_date (str): Only get crops after this date.
            Format: "YYYY-MM-DD".
            Default: "2008-01-01".
        start_date (str): Only get crops before this date.
            Format: "YYYY-MM-DD".
            Default: "2018-12-31".
    
    Returns:
        pd.DataFrame: Catalog of crops with various metadata.
    """
    data_path = Path(data_path)
    image_path = get_image_folder_path(data_path, zone)
    aoi = get_aoi(data_path, zone)

    raw_catalog = tsd.get_sentinel1.search(
        aoi,
        start_date=datetime.strptime(start_date, "%Y-%m-%d"),
        end_date=datetime.strptime(end_date, "%Y-%m-%d"),
        product_type="GRD"
    )

    if ids_to_keep is not None:
        ids_to_keep = set(ids_to_keep)
        raw_catalog = [
            element
            for element in raw_catalog
            if element["id"] in ids_to_keep
        ]

    if download_crops:
        tsd.get_sentinel1.download_crops(raw_catalog, aoi, "aws", image_path, 4)
    
    catalog = pd.DataFrame.from_records(raw_catalog)

    # Distinguish between vv and vh images (double the number of lines)
    catalog = pd.concat([
        catalog.assign(polarisation="vv", filename=catalog.filename + "_vv"),
        catalog.assign(polarisation="vh", filename=catalog.filename + "_vh"),
    ])

    get_image_path = lambda filename: image_path / (filename+".tif")
    catalog["exists"] = catalog["filename"].apply(lambda filename: os.path.exists(get_image_path(filename)))
    catalog = catalog.sort_values("filename")

    return catalog


def read_images(data_path, zone):
    """Read .tif images and return them as an array for a given zone.

    Args:
        data_path (str or Path): Path to the project data folder.
        zone (str): Which zone to get images for (e.g. "north", "south", "new_forest", "montenativo").

    Returns:
        np.array: Images as an array with shape (n_images, height, width).
        list: Filenames as a list of strings
        list: Rasterio "src" objects, which can be used e.g. to convert pixels to geographical coordinates.
    """
    image_path = get_image_folder_path(data_path, zone)
    filenames = sorted(os.listdir(image_path))

    images = []
    srcs = []
    for filename in tqdm(filenames):
        with rasterio.open(image_path/filename, "r") as src:
            img = src.read().squeeze()
            images.append(img)
            srcs.append(src)
            
            # # Read the pixels in each polygon
            # out = []
            # for polygon in polygons:
            #     mask, _, _ = rasterio.mask.raster_geometry_mask(src, [geojson.Polygon(polygon)], invert=True)
            #     out.append(img[mask])
            # polygon_pixels.append(out)

    filenames = np.array([f[:-4] for f in filenames])
    return np.array(images), filenames, srcs


def get_timeseries(data_path, zone, load_weather=True):
    """Read images for the north or south zone, extract the pixel values in the various polygons,
    and calculate statistics on them.

    Args:
        data_path (str or Path): Path to the project data folder.
        zone (str): Which zone to get the timeseries for ("north" or "south").
        load_weather (bool): Whether to also load weather information.
            Default: True.

    Returns:
        np.array: Images as an array with shape (n_images, height, width).
        list: Filenames as a list of strings
        list: Rasterio "src" objects, which can be used e.g. to convert pixels to geographical coordinates.
    """
    data_path = Path(data_path)
    polygons, rodals = read_raw_polygons_data(data_path, zone=zone)

    image_path = get_image_folder_path(data_path, zone)
    filenames = os.listdir(image_path)

    catalog = get_catalog(data_path, zone).sort_values("filename")

    polygon_pixels = []
    for filename in tqdm(filenames, desc="Reading images"):
        with rasterio.open(image_path/filename, "r") as src:
            img = src.read().squeeze()
            
            # Read the pixels in each polygon
            out = []
            for polygon in polygons:
                mask, _, _ = rasterio.mask.raster_geometry_mask(src, [geojson.Polygon(polygon)], invert=True)
                out.append(img[mask])
            polygon_pixels.append(out)

    filenames = [f[:-4] for f in filenames]
    timeseries = []
    for filename, pixels in zip(filenames, polygon_pixels):
        timeseries.append(pd.DataFrame({
            "date": filter_df_on_sorted_column(catalog, "filename", filename)["date"].squeeze(),
            "filename": filename,
            "polarisation": filename[-2:],
            "rodal": rodals,
            "raw_pixels": pixels,
        }))
    timeseries = pd.concat(timeseries, ignore_index=True)

    timeseries["pixels"] = timeseries["raw_pixels"].apply(lambda x: np.log(x))
    timeseries["n_pixels"] = timeseries["pixels"].apply(len)
    timeseries["mean"] = timeseries["pixels"].apply(np.mean)
    timeseries["median"] = timeseries["pixels"].apply(np.median)
    timeseries["std"] = timeseries["pixels"].apply(np.std)
    timeseries[["lower_bound", "upper_bound"]] = timeseries["pixels"].apply(lambda px: pd.Series(np.percentile(px, (5, 95))))
    
    # Associate to each date and polarisation the corresponding mean
    timeseries = timeseries.sort_values(["date", "rodal", "polarisation"])
    montenativo = (
        pd.read_csv(data_path/"montenativo.csv")
        .set_index(["date", "polarisation"])["mean_backscatter"]
        .to_dict()
    )
    #rodal_0_mean = timeseries.query("rodal == 0").set_index(["date", "polarisation"])["mean"].to_dict()
    timeseries["montenativo_mean"] = timeseries.apply(
        lambda row: montenativo[(str(row["date"].date()), row["polarisation"])],
        axis=1
    )
    timeseries["norm_mean"] = timeseries["mean"] - timeseries["montenativo_mean"]

    if load_weather:
        weather = load_paysandu_weather(data_path, columns=["rain", "humidity"], cutoff_time="09:05:00")
        timeseries = timeseries.merge(
            weather,
            left_on=timeseries["date"].dt.date,
            right_on=weather.index
        ).drop(columns="key_0")

    return timeseries

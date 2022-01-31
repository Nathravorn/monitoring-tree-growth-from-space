"""
* GeoTIFF read and write
* extract metadata: datetime, RPC,
* miscelaneous functions for crop
* wrappers for gdaltransform and gdalwarp

Copyright (C) 2018, Gabriele Facciolo <facciolo@cmla.ens-cachan.fr>
Copyright (C) 2018, Carlo de Franchis <carlo.de-franchis@ens-paris-saclay.fr>
"""
import numpy as np
import pyproj

def lonlat_to_utm(lons, lats, force_epsg=None):
    """
    Convert longitude, latitude to UTM coordinates.

    Args:
        lons (float or list): longitude, or list of longitudes
        lats (float or list): latitude, or list of latitudes
        force_epsg (int): optional EPSG code of the desired UTM zone

    Returns:
        eastings (float or list): UTM easting coordinate(s)
        northings (float or list): UTM northing coordinate(s)
        epsg (int): EPSG code of the UTM zone
    """
    lons = np.atleast_1d(lons)
    lats = np.atleast_1d(lats)
    if force_epsg:
        epsg = force_epsg
    else:
        epsg = compute_epsg(lons[0], lats[0])
    e, n = pyproj_lonlat_to_epsg(lons, lats, epsg)
    return e.squeeze(), n.squeeze(), epsg


def utm_to_lonlat(eastings, northings, epsg):
    """
    Convert UTM coordinates to longitude, latitude.

    Args:
        eastings (float or list): UTM easting coordinate(s)
        northings (float or list): UTM northing coordinate(s)
        epsg (int): EPSG code of the UTM zone

    Returns:
        lons (float or list): longitude, or list of longitudes
        lats (float or list): latitude, or list of latitudes
    """
    eastings = np.atleast_1d(eastings)
    northings = np.atleast_1d(northings)
    lons, lats = pyproj_epsg_to_lonlat(eastings, northings, epsg)
    return lons.squeeze(), lats.squeeze()


def utm_zone_to_epsg(utm_zone, northern_hemisphere=True):
    """
    Args:
        utm_zone (int):
        northern_hemisphere (bool): True if northern, False if southern

    Returns:
        epsg (int): epsg code
    """
    # EPSG = CONST + ZONE where CONST is
    # - 32600 for positive latitudes
    # - 32700 for negative latitudes
    const = 32600 if northern_hemisphere else 32700
    return const + utm_zone


def epsg_to_utm_zone(epsg):
    """
    Args:
        epsg (int):

    Returns:
        utm_zone (int): zone number
        northern_hemisphere (bool): True if northern, False if southern
    """
    if (32600 < epsg <= 32660):
        return epsg % 100, True
    elif (32700 < epsg <= 32760):
        return epsg % 100, False
    else:
        raise Exception("Invalid UTM epsg code: {}".format(epsg))


def compute_epsg(lon, lat):
    """
    Compute the EPSG code of the UTM zone which contains
    the point with given longitude and latitude

    Args:
        lon (float): longitude of the point
        lat (float): latitude of the point

    Returns:
        int: EPSG code
    """
    # UTM zone number starts from 1 at longitude -180,
    # and increments by 1 every 6 degrees of longitude
    zone = int((lon + 180) // 6 + 1)

    return utm_zone_to_epsg(zone, lat > 0)


def pyproj_transform(x, y, in_crs, out_crs, z=None):
    """
    Wrapper around pyproj to convert coordinates from an EPSG system to another.

    Args:
        x (scalar or array): x coordinate(s), expressed in in_crs
        y (scalar or array): y coordinate(s), expressed in in_crs
        in_crs (pyproj.crs.CRS or int): input coordinate reference system or EPSG code
        out_crs (pyproj.crs.CRS or int): output coordinate reference system or EPSG code
        z (scalar or array): z coordinate(s), expressed in in_crs

    Returns:
        scalar or array: x coordinate(s), expressed in out_crs
        scalar or array: y coordinate(s), expressed in out_crs
        scalar or array (optional if z): z coordinate(s), expressed in out_crs
    """
    transformer = pyproj.Transformer.from_crs(in_crs, out_crs, always_xy=True)
    if z is None:
        return transformer.transform(x, y)
    else:
        return transformer.transform(x, y, z)


def pyproj_lonlat_to_epsg(lon, lat, epsg):
    return pyproj_transform(lon, lat, 4326, epsg)


def pyproj_epsg_to_lonlat(x, y, epsg):
    return pyproj_transform(x, y, epsg, 4326)


def pyproj_lonlat_to_utm(lon, lat, epsg=None):
    if epsg is None:
        epsg = compute_epsg(np.mean(lon), np.mean(lat))
    x, y = pyproj_lonlat_to_epsg(lon, lat, epsg)
    return x, y, epsg


def utm_bounding_box_from_lonlat_aoi(aoi):
    """
    Computes the UTM bounding box (min_easting, min_northing, max_easting,
    max_northing)  of a projected AOI.

    Args:
        aoi (geojson.Polygon): GeoJSON polygon representing the AOI expressed in (long, lat)

    Return:
        min_easting, min_northing, max_easting, max_northing: the coordinates
        of the top-left corner and lower-right corners of the aoi in UTM coords
    """
    lons, lats  = np.array(aoi['coordinates'][0]).T
    east, north, zone = lonlat_to_utm(lons, lats)
    pts = list(zip(east, north))
    emin, nmin, deltae, deltan = bounding_box2D(pts)
    return emin, emin+deltae, nmin, nmin+deltan


def simple_equalization_8bit(im, percentiles=5):
    """
    Simple 8-bit requantization by linear stretching.

    Args:
        im (np.array): image to requantize
        percentiles (int): percentage of the darkest and brightest pixels to saturate

    Returns:
        numpy array with the quantized uint8 image
    """
    import numpy as np
    mi, ma = np.percentile(im[np.isfinite(im)], (percentiles, 100 - percentiles))
    im = np.clip(im, mi, ma)
    im = (im - mi) / (ma - mi) * 255   # scale
    return im.astype(np.uint8)


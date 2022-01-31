"""
* simplified map interaction using ipyleaflet
* display images in the notebook

Copyright (C) 2017-2018, Gabriele Facciolo <facciolo@cmla.ens-cachan.fr>
"""

import folium
import folium.plugins


def foliummap(location = [48.790153, 2.327395], zoom_start = 13 ):
    """
    creates a folium map centered at the indicated location (lat, long) and zoom
    level indicated by zoom_start. 
    The following widgets are also activated: 
      - drawing polygons and exporting the corresponding geojson 
      - show lat/long of the clicked position   
    Args:
        location (list): list containing lat and long of the center of the map 
        zoom_start (int): zoom level default 13

    Returns:
        handle to the folium.Map object (can be used to add overlays)          
    """
    f = folium.Figure(width='90%')
    m = folium.Map().add_to(f)
    # we can move the map to any position by indicating its (latitude, longitude)
    m.location   = location   # i.e. Paris, France
    m.zoom_start = zoom_start

    folium.features.LatLngPopup().add_to(m)
    folium.plugins.Draw(export=True).add_to(m)
    
    return m 


def add_identity_to_plot(ax, legend=True):
    lower_left, upper_right = zip(*[ax.get_xlim(), ax.get_ylim()])
    lims = (max(lower_left), min(upper_right))
    ax.plot(lims, lims, ls="--", c="gray", label="identity")
    if legend:
        ax.legend()
    return ax


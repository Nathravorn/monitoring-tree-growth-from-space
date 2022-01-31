---
title: Forestry Yield Prediction Using Sentinel-1 Images
author: Etienne Boisseau
theme: metropolis
mainfont: "Open Sans"
section-titles: true
aspectratio: 169
header-includes:
    \usepackage{subcaption}
    \newcommand{\R}{\mathbb{R}}
    \renewcommand{\L}{\mathcal{L}}
    \newcommand{\M}{\mathcal{M}}
    \renewcommand{\S}{\mathcal{S}}
    \newcommand{\chevrons}[1]{\langle#1\rangle}
    \newcommand{\paren}[1]{\left(#1\right)}
---
## Introduction

![Pandule forest area, Paysandu, Uruguay](img/illustration/forest.png){width=90%}

## Related work
Main insights:

- There is definitely exploitable information in Sentinel-1 images
- The problem of saturation is serious and particularly affects S1

Goals:

- Verify that there is no exploitable information about the AGB of an already mature forest ;
- In doing so, establish methods which could be applied to larger wavelengths ;
- Identify and correct for sources of variation in the radar measurements ;
- Confirm that Sentinel-1 images contain useful information for young forests and try to estimate the saturation point in years.

# Data
## Summary
Data:

- Measurements (ground truth)
- Images
- Polygons
- Weather

Zones:

- North
- South
- New Forest
- Montenativo

## Measurements: Exploration
Two zones:

- North
- South

Main fields:

- Date
- Coordinates
- Rodal (segment of forest)
- Height
- Diameter
- Basal area
- Volume

## Measurements: Exploration
![Volume measurements for the 12 most represented rodals](img/eda/volume_by_rodal.png){width=70%}

## Measurements: Exploration
![Pairwise relationships between measurements](img/eda/pairplot.png){width=50%}

## Measurements: Units
![Correspondence between AGB estimation in Mg/hectare and the data](img/eda/agb.png){width=50%}

## Measurements: Choosing a zone
| year   | north   | south   |
|:-------|--------:|--------:|
| 2013   | 103     | 151     |
| 2016   | 103     | 147     |
| 2017   | 0       | 176     |
| 2018   | 144     | 0       |
| Total  | 350     | 474     |

Table: Number of measurements for each year in the north and south zone

## Measurements: Choosing a zone
![Comparison of the north and south zones](img/eda/zone_comparison.png){width=70%}

## Images
| zone        |   n_images | resolution   | first_date   | end_date   |
|:------------|-----------:|:-------------|:-------------|:-----------|
| south       |         61 | 588x372      | 2017-01-04   | 2018-12-25 |
| new_forest  |        116 | 480x288      | 2017-01-04   | 2021-04-01 |
| montenativo |        116 | 972x348      | 2017-01-04   | 2021-04-01 |

## Images and Polygons: South
![Image of the South zone on 2017-01-04, in VV polarisation](img/images/south.png){width=80%}

## Images and Polygons: South
![Mean image of the South zone, with its polygons (rodals)](img/polygons/south.png){width=80%}

## Images and Polygons: New forest
![Image of the New forest zone on 2017-01-04, in VV polarisation](img/images/new_forest.png){width=80%}

## Images and Polygons: New forest
![Mean image of the New forest zone, with its polygon](img/polygons/new_forest.png){width=80%}

## Images and Polygons: Montenativo
![Image of the Montenativo zone on 2017-01-04, in VV polarisation](img/images/montenativo.png){width=80%}

## Images and Polygons: Montenativo
![Mean image of the Montenativo zone, with its polygon](img/polygons/montenativo.png){width=80%}

## Weather
![worldweatheronline.com historical weather page](img/illustration/scraping.png){width=40%}

# Methods and Results
## Normalisation: South
![Correlation between South zone backscatter and Montenativo](img/normalization/south_correlation.png){width=55%}

## Normalisation: South
![South zone weather effect before and after normalization](img/normalization/south_rain_effect.png){width=55%}

## Normalisation: New forest
![Correlation between New forest zone backscatter and Montenativo](img/normalization/new_forest_correlation.png){width=55%}

## Normalisation: New forest
![New forest zone weather effect before and after normalization](img/normalization/new_forest_rain_effect.png){width=55%}

## New Forest backscatter
![VV and VH backscatter over time in New Forest](img/new_forest/timeseries.png){width=55%}

## New Forest backscatter
![VH / VV backscatter over time, before and after normalization](img/new_forest/timeseries_ratio.png){width=90%}

## AGB prediction on the South Zone
Three scales:

- Whole zone
- Rodal (forest segment)
- Tree

## Theoretical saturation threshold
![Saturation threshold according to the literature](img/eda/saturation.png){width=50%}

## Zone scale
![VV and VH backscatter over time in South zone](img/volume_prediction/zone_scale_timeseries.png){width=90%}

## Zone scale
![VH / VV backscatter over time in South zone](img/volume_prediction/zone_scale_timeseries_ratio.png){width=90%}

## Rodal scale
![VV and VH backscatter per rodal](img/volume_prediction/rodal_scale_timeseries.png){width=70%}

## Rodal scale
![VH / VV backscatter per rodal](img/volume_prediction/rodal_scale_timeseries_ratio.png){width=60%}

## Rodal scale
![Relationship between VH backscatter and volume](img/volume_prediction/rodal_scale_lr_vh.png){width=50%}

## Rodal scale
![Relationship between VH/VV backscatter ratio and volume](img/volume_prediction/rodal_scale_lr_ratio.png){width=50%}

## Single-tree scale
![Relationship between per-tree measurement and volume](img/volume_prediction/tree_scale.png){width=50%}

## Conclusion
- We established a method (normalization, 3-scale analysis) for assessing the relationship between backscatter intensities and volume
- The C-band is indeed saturated for our forest
- The saturation point could be around 3 years of age for our species
- Reference-area normalization helps reduce variation a lot but is terrain-specific

## Future work
- **Use a larger wavelength**
- Use a more adaptive normalization method that does not leave residual weather effects in young forest
- Make a more precise estimate of the saturation point for our case (using more ground truth data)

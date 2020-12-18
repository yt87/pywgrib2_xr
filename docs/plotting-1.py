import xarray as xr
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import pywgrib2_xr as pywgrib2
from pywgrib2_xr.utils import localpath

file = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012512_P000.grib2')
tmpl = pywgrib2.make_template(file)
ds = pywgrib2.open_dataset(file, tmpl)
country_boundary = cfeature.NaturalEarthFeature(category='cultural', name='admin_0_countries', scale='110m', facecolor='none')
map_crs = ccrs.AzimuthalEquidistant(central_longitude=249)
t = ds['TMP.700_mb']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6),
                               subplot_kw={'projection': map_crs})
_ = t.plot(x='longitude', y='latitude', ax=ax1, transform=ccrs.PlateCarree(),
           add_colorbar=False, add_labels=False)
proj = ds.wgrib2.get_grid()
globe = ccrs.Globe(ellipse="sphere", semimajor_axis=proj.globe["earth_radius"],
                   semiminor_axis=proj.globe["earth_radius"])
data_crs = ccrs.Stereographic(globe=globe,
                              central_latitude=proj.crs['latitude_of_projection_origin'],
                              central_longitude=proj.crs['straight_vertical_longitude_from_pole'],
                              true_scale_latitude=proj.crs['standard_parallel'])
_ = t.plot(x='x', y='y', ax=ax2, transform=data_crs, add_colorbar=False,
           add_labels=False)
for ax in ax1, ax2:
    _ = ax.add_feature(country_boundary, edgecolor='black')
    _ = ax.gridlines()
fig.suptitle('Temperature at 700 hPa', fontsize=20)
plt.show()
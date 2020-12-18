import xarray as xr
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
import metpy.calc
from metpy.units import units
import pywgrib2_xr as pywgrib2
from pywgrib2_xr.utils import remotepath

def predicate(i):
    return (i.varname in ('RH', 'TMP', 'UGRD', 'VGRD', 'HGT') and
            i.bot_level_code == 100 and 10000 <= i.bot_level_value < 1000000)

file = remotepath('nam.t00z.awak3d00.tm00.grib2')
tmpl = pywgrib2.make_template(file, predicate, vertlevels='isobaric')
var_names = {'RH.isobaric': 'relative_humidity',
             'TMP.isobaric': 'temperature',
             'UGRD.isobaric': 'u',
             'VGRD.isobaric': 'v',
             'HGT.isobaric': 'height',
            }
ds = pywgrib2.open_dataset(file, tmpl).rename(var_names)
data = ds.metpy.parse_cf()
x, y = data['temperature'].metpy.coordinates('x', 'y')
data_crs = data['temperature'].metpy.cartopy_crs
data['temperature'].metpy.convert_units('degC')
vertical, = data['temperature'].metpy.coordinates('vertical')
data_level = data.metpy.loc[{vertical.name: 500. * units.hPa}]

fig, ax = plt.subplots(1, 1, figsize=(12, 8), subplot_kw={'projection': data_crs})
rh = ax.contourf(x, y, data_level['relative_humidity'], levels=[60, 70, 80, 100],
                 colors=['#99ff00', '#00ff00', '#00cc00'])
wind_slice = slice(20, -20, 20)
_ = ax.barbs(x[wind_slice], y[wind_slice],
             data_level['u'].metpy.unit_array[wind_slice, wind_slice].to('knots'),
             data_level['v'].metpy.unit_array[wind_slice, wind_slice].to('knots'),
             length=6)
h_contour = ax.contour(x, y, data_level['height'], colors='k',
                       levels=range(5000, 6200, 60))
_ = h_contour.clabel(fontsize=8, colors='k', inline=1, inline_spacing=8,
                     fmt='%i', rightside_up=True, use_clabeltext=True)
t_contour = ax.contour(x, y, data_level['temperature'], colors='xkcd:red',
                       levels=range(-50, 4, 5), alpha=0.8, linestyles='--')
_ = t_contour.clabel(fontsize=8, colors='xkcd:deep blue', inline=1, inline_spacing=8,
                     fmt='%i', rightside_up=True, use_clabeltext=True)
_ = ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor=cfeature.COLORS['land'])
_ = ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor=cfeature.COLORS['water'])
_ = ax.add_feature(cfeature.STATES.with_scale('50m'), edgecolor='#c7c783', zorder=0)
_ = ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor=cfeature.COLORS['water'],
                   edgecolor='#c7c783', zorder=0)
time = data['temperature'].metpy.time
vtime = data.reftime + time
_ = ax.set_title('500 hPa Heights (m), Temperature (\u00B0C), Humidity (%) at '
                 + vtime.dt.strftime('%Y-%m-%d %H:%MZ').item(),
                 fontsize=20)
plt.show()
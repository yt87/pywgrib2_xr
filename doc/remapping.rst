
Remapping Dataset
=================

Datasets created by **pywgrib2** can be remapped to cover smaller area.
This might be important to save on storage or compute time. For forecast
verification model data is compared to observations at a finite set of points.
The interpolation methods are provided by **xarray** dataset_accessor ``wgrib2``. 

Interpolation to grid
---------------------

To interpolate to a new grid, one has to define first that grid parameters.
**pywgrib2** provides two functions: :py:func:`~pywgrib2_xr.grid_fromdict`
and :py:func:`~pywgrib2_xr.grid_fromstring`. The latter follows
`wgrib2 style <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/new_grid.html>`_
and is easier to use. The argument is a single string (unlike three passed to
**wgrib2**) which specifies projection type and basic parameters. Additional,
optional arguments allow to specify vector orientation and Earth shape.

To obtain the neccessary values from a grid in a GRIB2 file, run **wgrib2**
with the arguments ``-V -radius``:

.. code-block:: console

    wgrib2 data/CMC_glb_WIND_TGL_10_ps30km_2020012500_P000.grib2 -end -V -radius

.. parsed-literal::

    1:0:vt=2020012500:10 m above ground:anl:UGRD U-Component of Wind [m/s]:
      ndata=49400:undef=0:mean=0.943856:min=-22.8:max=22.5
      grid_template=20:winds(grid):
          polar stereographic grid: (247 x 200) input WE:SN output WE:SN res 8
          North pole lat1 32.549114 lon1 225.385728 latD 60.000000 lonV 249.000000 dx 30000.000000 m dy 30000.0
    :code3.2=6 sphere predefined radius=6371229.0 m

The format for polar stereographic grid is ``nps:lov:lad lon0:nx:dx lat0:ny:dy``.
For the above grid the first argument would be
``nps:249:60 225.385728:247:30000 32.549114:200:30000``.
Since the argument ``winds`` defaults to 'grid'. Earth shape is the same as NCEP
default, only one argument is needed.

**iplib** provides five interpolation methods: nearest neighbour, bilinear, bicubic,
budget and spectral. Unfortunately, there is no official documentation describing
the algorithms. Few hints based on experience:

  - nearest neighbour: use for categorical, surface variables if you are going to
    look at the surface budgets, and properties.
  - bilinear: fast and ok for similar scale interpolations. Bad for high-res -> low-res.
    for example reducing 1000x1000 grid to 100x100 (same area, lower resolution).
    Will pick up small scale noise and reduce the forecast skill.
  - bicubic: theoretically more precise than bilinear, but it may introduce negative
    values where none exist. Not recommended.
  - budget: it does 25 bilinear interpolations on a 5x5 grid and computes the average.
    Use on precipitation fields to retain global average precipation.  Also good
    for going from 1000x1000 -> 100x100 grid. See 
    `Accadia et al. <https://doi.org/10.1175/1520-0434(2003)018%3C0918:SOPFSS%3E2.0.CO;2>`_
  - spectral: with the right parameters, can be the most accurate method. Like bicubic,
    can create negative values where none exist. Not to be used for snow,
    precipitation, relative humidity or surface pressure (ringing?).

See also the **wgrib2** documentation on the argument
`-new_grid <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/new_grid_intro.html>`_.

The following code extracts 3-hour accumulated precipitation, surface model elevation,
ceiling and heights at pressure levels, within a smaller area. The data variables are
renamed before remapping.

**pywgrib2** allows interpolation type to depend on variable. The specification
is a dictionary: ``variable -> interpolation_type``. The ``default`` entry is for
all remaining variables, in this case ``elev`` and ``height``.

.. code-block:: python

    from datetime import timedelta
    import pywgrib2_xr as pywgrib2
    from pywgrib2_xr.utils import remotepath

    file = remotepath('nam.t00z.awak3d06.tm00.grib2')
    grid_desc = 'nps:225:60 227:40:8000 57:40:8000'

    def pcp_pred(i):
        return i.varname in ['APCP', 'ACPCP'] and \
               i.end_ft - i.start_ft == timedelta(hours=3)

    def elev_pred(i):
        return i.varname == 'HGT' and i.level_str == 'surface'

    def ceil_pred(i):
        return i.varname == 'HGT' and i.level_str == 'cloud ceiling'

    def height_pred(i):
        return i.varname == 'HGT' and i.level_code == 100

    template = pywgrib2.make_template(file, pcp_pred, elev_pred, ceil_pred,
                                      height_pred, vertlevels='isobaric')
    names = {'APCP.surface.3_hour_acc': '3h_pcp',
             'ACPCP.surface.3_hour_acc': '3h_cum_pcp',
             'HGT.surface': 'elev',
             'HGT.cloud_ceiling': 'ceil',
             'HGT.isobaric': 'height',
            }
    ds = pywgrib2.open_dataset(file, template).rename(names)

    iptype = {'3h_pcp': 'budget',
              '3h_conv_pcp': 'budget',
              'ceil': 'neighbour',
              'default': 'bilinear',
             }
    new_grid = pywgrib2.grid_fromstring(grid_desc)
    ds_grd = ds.wgrib2.grid(new_grid, iptype=iptype)
    ds_grd.coords['polar_stereographic'].attrs

.. parsed-literal::

    {'grid_mapping_name': 'polar_stereographic',
     'straight_vertical_longitude_from_pole': 225.0,
     'standard_parallel': 60.0,
     'latitude_of_projection_origin': 90.0,
     'shape': 'sphere',
     'earth_radius': 6371229.0,
     'code': 6,
     'GRIB_gdtnum': <GDTNum.POLAR_STEREO: 20>,
     'GRIB_gdtmpl': [6,
      0,
      0,
      0,
      0,
      0,
      0,
      553,
      425,
      30000000,
      187000000,
      56,
      60000000,
      225000000,
      11250000,
      11250000,
      0,
      64],
     'GRIB_Npts': 235025,
     'GRIB_Nx': 553,
     'GRIB_Ny': 425,
     'GRIB_La1': 30.0,
     'GRIB_Lo1': 187.0,
     'GRIB_LaD': 60.0,
     'GRIB_LoV': 225.0,
     'GRIB_winds': 'grid',
     'GRIB_Dx': 11250.0,
     'GRIB_Dy': 11250.0,
     'GRIB_LaO': 90.0}

Interpolation to points
-----------------------

The method :py:meth:`~pywgrib2_xr.Wgrib2DatasetAccessor.location` creates 
a dataset with all data variables interpolated to an arbitrary sequence of
locations within the original grid area (i.e. no extrapolation). Available
interpolation type can be nearest neighbour, bilinear and bicubic.

To specify point locations, use :py:class:`~pywgrib2_xr.Point`. The constructor
accepts longitudes, latitudes and, optionally, coordinate labels.

.. code-block:: python

    # Coordinates from https://www.aviationweather.gov/docs/metar/stations.txt
    sites = ["PAFA", "PAJN", "PANC"]
    lons = [360 - (147 + 52/60),  360 - (134 + 33/60), 360 - (150 + 1/60)]
    lats = [64 + 48/60, 58 + 21/60, 61 + 10/60]
    locs = pywgrib2.Point(lons, lats, ('stid', sites, {'long_name': 'site identifier'}))
    # Budget interpolation to points is not supported
    iptype = {'3h_pcp': 'neighbour',
              '3h_conv_pcp': 'neighbour',
              'ceil': 'neighbour',
              'default': 'bilinear',
             }

    ds_pts = ds.wgrib2.location(locs, iptype=iptype)
    ds_pts.coords

.. parsed-literal::

    Coordinates:
        points     int64 0
        longitude  (stid) float64 212.1 225.4 210.0
        latitude   (stid) float64 64.8 58.35 61.17
      * stid       (stid) <U4 'PAFA' 'PAJN' 'PANC'
      * isobaric1  (isobaric1) int64 100000 97500 95000 92500 ... 10000 7500 5000
        reftime    datetime64[ns] 2020-09-07
        time1      timedelta64[ns] 06:00:00

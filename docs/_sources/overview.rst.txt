
Overview
========

**pywgrib2_xr** uses wgrib2_ as a background engine. It provides following
functionality:

  1. A low-level interface to **wgrib2** C-API. This is the one to use to write
     GRIB2 files.
  2. A GRIB2 backend to xarray_, similar to cfgrib_. The decoded messages are
     assembled as **xarray** datasets.
  3. Remapping the resulting datasets to a different grid or to an arbitrary set
     of locations. It uses Fortran library iplib_, which is a part of **wgrib2**
     distribution.

Low-level interface
-------------------

Suppose the task is to write grib file containing surface temperature and wind from
a large grib file. This can be achieved with a **wgrib2** call:

.. code-block:: console

    wgrib2 nam.t12z.awak3d18.tm00.grib2 -match \
    ':(TMP:2 m above ground|[U|V]GRD:10 m above ground):' \
    -out /tmp/subset.grib2

The equivalent Python code is:

.. _example-1:

.. code-block:: python

    import pywgrib2_xr as pywgrib2 

    in_file = 'nam.t12z.awak3d18.tm00.grib2'
    out_file = '/tmp/subset.grib2'

    match_str = ':(TMP:2 m above ground|[U|V]GRD:10 m above ground):'
    pywgrib2.wgrib(in_file, '-inv', '/dev/null', '-match', match_str, '-grib', out_file)
    pywgrib2.free_files(in_file, out_file)

We can check the output file contain requested data. The **wgrib2** call:

.. code-block:: console

    wgrib2 /tmp/subset.grib2

translates to Python as:

.. code-block:: python

    with pywgrib2.MemoryBuffer() as buf:
        pywgrib2.wgrib(out_file, '-inv', buf)
        buf.get('s')

The class :py:class:`~pywgrib2_xr.MemoryBuffer` used in this example is a wrapper
around **wgrib2** C-API functions
``int wgrib2_get_mem_buffer(unsigned char *my_buffer, size_t size, int n)`` and
``int wgrib2_set_mem_buffer(const unsigned char *my_buffer, size_t size, int n)`` to
transfer data between the calling program and the API "superfunction"
``int wgrib2(int argc, const char **argv)``. The argument ``'s'`` means ``buf.get()``
should return a string.

Section :ref:`Writing GRIB2 files <writing_grib_files>` shows a an example of storing
calculated weather element in a GRIB2 file.

Xarray backend
--------------

Conversion of GRIB2 messages to an **xarray** dataset is a task that can not have
a fully satisfactory solution. Each GRIB2 message is a self-contained unit,
essentially a 2-dimensional data, plus attributes, while an **xarray** dataset is
a collection of multidimensional arrays that may share some dimensions.

The first difficulty are element, or variable names. Model output usually contains
many geopotential height variables: pressure or sigma levels, cloud base/top,
tropopause, etc. All have the same name, ``HGT`` (NCEP mnemonic), and can only be 
distinguishad by attributes. A dataset can have only one variable named ``HGT``.
**cfgrib** solves the issue by forcing different heights to be in separate datasets.
This leads to proliferation of number of datasets for each model output.

**pywgrib2_xr** uses attributes to define variable name. Thus variables
``HGT.isobaric`` and ``HGT.cloud_ceiling`` can both coexist in the same dataset.

The next issue is dimension handling. Different variables can have different
time and vertical dimensions. Temperature is provided for all forecast times,
accumulated precipitation is not available at initial (analysis) time. Wind
and vorticity do not have the same number of vertical levels. **cfgrib** needs
to put those elements in separate datasets.

The third issue stems from the way GRIB2 messages are distributed.
`MSC Datamart <https://dd.weather.gc.ca/>`__ makes one file per message while
`NCEP <ftp://ftp.ncep.noaa.gov/pub/data/nccf/com>`__
files group messages by reference and forecast times. Each file can contain hundreds
of messages.  **xarray** has a concept of a `datastore`, which essentially
means a single file storing the data. A dataset is build from datastore.
Those datasets can then be combined, there are two combining
functions: :py:func:`xarray.combine_by_coords` and :py:func:`xarray.combine_nested`.
The latter, the most flexible, requires user to partition input files into
nested lists. This is not simple and may not be even possible when some
of the files are missing. Consider the following example:

.. code-block:: python

    import xarray as xr
    from pywgrib2_xr.utils import localpath

    f_10_0_00 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012500_P000.grib2')
    f_10_3_00 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012500_P003.grib2')
    f_7_0_00 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012500_P000.grib2')
    f_7_3_00 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012500_P003.grib2')
    ds = xr.open_mfdataset([[f_10_0_00, f_10_3_00], [f_7_0_00, f_7_3_00]],
                           engine='cfgrib', combine='nested',
                           concat_dim=['level', 'step'])
    ds

.. parsed-literal::

    <xarray.Dataset>
    Dimensions:        (level: 2, step: 2, x: 247, y: 200)
    Coordinates:
        time           datetime64[ns] 2020-01-25
    * step           (step) timedelta64[ns] 00:00:00 03:00:00
        isobaricInhPa  (level) int64 1000 700
        latitude       (y, x) float64 dask.array<chunksize=(200, 247), meta=np.ndarray>
        longitude      (y, x) float64 dask.array<chunksize=(200, 247), meta=np.ndarray>
        valid_time     (step) datetime64[ns] 2020-01-25 2020-01-25T03:00:00
    Dimensions without coordinates: level, x, y
    Data variables:
        t              (step, level, y, x) float32 dask.array<chunksize=(1, 1, 200, 247), meta=np.ndarray>
    Attributes:
        GRIB_edition:            2
        GRIB_centre:             cwao
        GRIB_centreDescription:  Canadian Meteorological Service - Montreal 
        GRIB_subCentre:          0
        Conventions:             CF-1.7
        institution:             Canadian Meteorological Service - Montreal 
        history:                 2020-10-29T19:45:43 GRIB to CDM+CF via cfgrib-0....

This works as expected. But if a file is missing, the above code will fail:

.. code-block:: python
  
    ds = xr.open_mfdataset([[f_10_0_00, f_10_3_00], [f_7_0_00]], engine='cfgrib',
                           combine='nested', concat_dim=['level', 'step'])

.. parsed-literal::

    The supplied objects do not form a hypercube because sub-lists do not have consistent lengths along dimension0


**pywgrib2_xr** attempts to solve this problem by the concept of a template,
borrowed from **AWIPS1**. 
The template defines logical dataset structure. The logical dataset contains messages
sharing horizontal grid and ``reference time``, coded in
`Section 1 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_sect1.shtml>`__ 
of a GRIB2 message. Vertical and time coordinates may differ. Conceptually this means
that the logical dataset corresponds to one model run.

To build a template, one has to have a coplete set of files for one model run,
In most cases an archive will contain such a set. Once the template is built,
the logical datasets can be concatenated over dimension `reference time`.
Missing files will result in respective chunks set to NaNs.

What this means, however, is that **pywgrib2_xr** cannot be simply implemented as
another backend for **xarray**. It does attempt to have the same interface,
the function :py:func:`pywgrib2_xr.open_dataset` is ported from the `backends`
module of **xarray**. 
There is no need for ``open_mfdataset()``, the logic of combining input files
is included in ``open_dataset()``:

.. code-block:: python

    from datetime import timedelta
    import pywgrib2_xr as pywgrib2
    from pywgrib2_xr.utils import localpath

    f_10_0_00 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012500_P000.grib2')
    f_10_3_00 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012500_P003.grib2')
    f_7_0_00 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012500_P000.grib2')
    f_7_3_00 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012500_P003.grib2')
    f_10_0_12 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012512_P000.grib2')
    f_10_3_12 = localpath('CMC_glb_TMP_ISBL_1000_ps30km_2020012512_P003.grib2')
    f_7_0_12 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012512_P000.grib2')
    f_7_3_12 = localpath('CMC_glb_TMP_ISBL_700_ps30km_2020012512_P003.grib2')

    f_12Zrun = [f_10_0_12, f_10_3_12, f_7_0_12, f_7_3_12]   # complete set for template
    f_all = [f_10_0_00, f_10_3_00, f_7_0_00] + f_12Zrun     # simulate missing file
    tmpl = pywgrib2.make_template(f_12Zrun, vertlevels='isobaric')
    ds = pywgrib2.open_dataset(f_all, tmpl)
    ds

.. parsed-literal::

    <xarray.Dataset>
    Dimensions:              (isobaric1: 2, reftime: 2, time1: 2, x: 247, y: 200)
    Coordinates:
        longitude            (y, x) float64 dask.array<chunksize=(200, 247), meta=np.ndarray>
        latitude             (y, x) float64 dask.array<chunksize=(200, 247), meta=np.ndarray>
      * x                    (x) float64 -2.61e+06 -2.58e+06 ... 4.74e+06 4.77e+06
      * y                    (y) float64 -5.97e+06 -5.94e+06 ... -3.022e+04 -216.1
      * isobaric1            (isobaric1) int64 100000 70000
      * time1                (time1) timedelta64[ns] 00:00:00 03:00:00
      * reftime              (reftime) datetime64[ns] 2020-01-25 2020-01-25T12:00:00
        polar_stereographic  int64 ...
    Data variables:
        TMP.isobaric         (reftime, time1, isobaric1, y, x) float32 dask.array<chunksize=(1, 2, 2, 200, 247), meta=np.ndarray>
    Attributes:
        Projection:             polar_stereographic
        Originating centre:     54 - Canadian Meteorological Service - Montreal (...
        Originating subcentre:  0
        History:                Created by pywgrib2_xr-0.2.1

.. code-block:: python

    ds['TMP.isobaric'].sel({'reftime': '2020-01-25T00:00:00',
                            'time1': timedelta(hours=3),
                            'isobaric1': 70000}).values

.. parsed-literal::

    array([[nan, nan, nan, ..., nan, nan, nan],
           [nan, nan, nan, ..., nan, nan, nan],
           [nan, nan, nan, ..., nan, nan, nan],
           ...,
           [nan, nan, nan, ..., nan, nan, nan],
           [nan, nan, nan, ..., nan, nan, nan],
           [nan, nan, nan, ..., nan, nan, nan]], dtype=float32)

The decoder handles the following grids:

 * Equidistant Cylindrical, also known as latitude-longitude
 * Rotated latitude-longitude
 * Mercator
 * Polar Stereographic
 * Lambert Conformal Conic
 * Gaussian
 * Space View

Creation af a dataset from GRIB2 files is a three stage process:

 1. Create inventory for each input file.
 2. Create template.
 3. Read all input files.

The first step was done implicitly in the above example. When the same GRIB2 files
are processed multiple times, it makes sense (to save time) to save each inventory
to a disk file. The whole process is described in the :ref:`User Guide <user_guide>`.

Remapping
---------

**pywgrib2_xr** comes with interpolation library iplib_ which allows to remap dataset
to different grid, or to a set of arbitrary points.
Remapping are implemented as methods of **xarray** data accessor 
:py:class:`~pywgrib2_xr.Wgrib2DatasetAccessor`, registered as an attribute ``wgrib2``.
The next example shows how to remap dataset to a set of locations.

.. code-block:: python

   lons = [-77.03, -150.02, -78.62] 
   lats = [38.85, 61.17, 43.57]
   ids = ['KDCA', 'PANC', 'CYYZ']
   sites = pywgrib2.Point(lons, lats, ('airport', ids, {}))
   ds2 = ds.wgrib2.location(sites)
   tmp = ds2['TMP.isobaric'].compute()
   tmp.sel(airport='CYYZ')

.. parsed-literal::

    <xarray.DataArray 'TMP.isobaric' (reftime: 2, time1: 2, isobaric1: 2)>
    array([[[279.4096 , 268.39636],
            [280.62656,       nan]],

           [[275.98114, 266.69205],
            [275.85538, 264.9516 ]]], dtype=float32)
    Coordinates:
        points     int64 0
        longitude  float64 -78.62
        latitude   float64 43.57
        airport    <U4 'CYYZ'
      * reftime    (reftime) datetime64[ns] 2020-01-25 2020-01-25T12:00:00
      * time1      (time1) timedelta64[ns] 00:00:00 03:00:00
      * isobaric1  (isobaric1) int64 100000 70000
    Attributes:
        short_name:    TMP
        long_name:     Temperature
        units:         K
        grid_mapping:  points

**iplib** supports all grids handled by the decoder with the exception of `Space View`.

CF support
----------

**pywgrib2_xr** does not follow CF conventions at this time. Standard names are set
only for coordinate variables, not data. Also, composite units are as provided by
wgrib2 code. For example, speed units are ``m/s``, not ``m s-1``, as mandated
`here <http://cfconventions.org/Data/cf-standard-names/current/build/cf-standard-name-table.html>`__.

.. code-block:: python

   import cf_xarray
   ds.cf.describe()

.. parsed-literal::

    Axes:
	X: ['x']
	Y: ['y']
	Z: ['isobaric1']
	T: []

    Coordinates:
	    longitude: ['longitude']
	    latitude: ['latitude']
	    vertical: ['isobaric1']
	    time: []

    Cell Measures:
	    area: unsupported
	    volume: unsupported

    Standard Names:
	    forecast_period: ['time1']
	    projection_x_coordinate: ['x']
	    projection_y_coordinate: ['y']
	    reference_time: ['reftime']


.. _xarray: http://xarray.pydata.org/
.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _ecCodes: https://confluence.ecmwf.int/display/ECC/ecCodes+Home
.. _wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml

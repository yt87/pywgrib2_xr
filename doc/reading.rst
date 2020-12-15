
Reading GRIB2 files
===================

The function :py:func:`~pywgrib2_xr.open_dataset` creates a dataset from one
or more files. Mandatory arguments are:

 * one (string) or more (iterable of strings) GRIB2 files.
 * template created by a call to :py:func:`~pywgrib2_xr.make_template`.
 * location of inventory files, if not collocated with data files. If not specified
   and the inventory cannot be found, it will be created.

Remaining optional arguments: ``chunks``, ``preprocess``, ``parallel`` and ``cache``
are the same as for :py:func:`xarray.open_mfdataset`.
To continue the example from the previous section:

.. code-block:: python

    import glob
    import pywgrib2_xr as pywgrib2

    files = sorted(glob.glob('nam.t00z.afwahi??.tm00.grib2'))
    tmpl = pywgrib2.make_template(files, lambda x: x.varname == 'APCP')
    ds = pywgrib2.open_dataset(files, tmpl)
    ds

.. parsed-literal::

    <xarray.Dataset>
    Dimensions:                   (latitude: 231, longitude: 278, time1: 1, time2: 2, time3: 2, time4: 2, time5: 8)
    Coordinates:
      * longitude                 (longitude) float64 190.0 190.1 ... 219.8 219.9
      * latitude                  (latitude) float64 8.133 8.241 ... 32.86 32.97
      * time1                     (time1) timedelta64[ns] 00:00:00
      * time5                     (time5) timedelta64[ns] 03:00:00 ... 1 days 00:...
      * time2                     (time2) timedelta64[ns] 06:00:00 18:00:00
      * time3                     (time3) timedelta64[ns] 09:00:00 21:00:00
      * time4                     (time4) timedelta64[ns] 12:00:00 1 days
        reftime                   datetime64[ns] ...
        latitude_longitude        int64 ...
    Data variables:
        APCP.surface              (time1, latitude, longitude) float32 ...
        APCP.surface.3_hour_acc   (time5, latitude, longitude) float32 ...
        APCP.surface.6_hour_acc   (time2, latitude, longitude) float32 ...
        APCP.surface.9_hour_acc   (time3, latitude, longitude) float32 ...
        APCP.surface.12_hour_acc  (time4, latitude, longitude) float32 ...
    Attributes:
        Projection:             latitude_longitude
        Originating centre:     7 - US National Weather Service - NCEP (WMC)
        Originating subcentre:  0
        History:                Created by pywgrib2_xr-0.2.1

.. note::

    The data variables are always in WE:SN order, regardless of the order in GRIB2 file.
    This follows **wgrib2** default behaviour.


Performance
===========

**pywgrib2** uses **wgrib2** code. It is iteresting to compare performance of
those two on common tasks.

The first task is converting GRIB2 file to netCDF. The GRIB2 file is GDAS 2m temperature
data for whole month that can be obtained
`here <ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/monthly/time>`_
The file size is about 20 MB. We compare run times of **wgrib2** and Python scripts
**cfgrib** and **pywgrib2**. The tests were ran several times, with no significant
differences in lapsed times:

.. code-block:: console

  time wgrib2 tmp2m.gdas.l.201912.grib2 -inv /dev/null -netcdf x.nc

.. parsed-literal::

  real	0m9.814s
  user	0m9.696s
  sys	0m0.100s

.. code-block:: console

  time cfgrib to_netcdf -o y.nc tmp2m.l.gdas.202002.grib2

.. parsed-literal::

  real	0m16.451s
  user	0m15.146s
  sys	0m0.714s

.. code-block:: console

  time pywgrib2 template -t '2019-12-01T00' -o tmp2m.tmpl tmp2m.l.gdas.201912.grib2

  real	0m1.160s
  user	0m1.210s
  sys	0m0.417s

.. code-block:: console

  time pywgrib2 to_nc -T tmp2m.tmpl -o tmp2m-pywgrib.nc tmp2m.l.gdas.201912.grib2

.. parsed-literal::

  real	0m12.577s
  user	0m12.401s
  sys	0m0.868s

**wgrib2** is the fastest, followed by **pywgrib2** and **cfgrib**.
One has to note that **wgrib2** does not handle this dataset correctly: it uses
forecast valid time as the time coordinate. The datafile contains analysis
and 1 to 6 hour forecast, every 6 hours:

.. code-block:: console

  wgrib2 tmp2m.gdas.l.202002.grib2

.. parsed-literal::

  1:0:d=2020020100:TMP:2 m above ground:anl:
  2:26025:d=2020020100:TMP:2 m above ground:1 hour fcst:
  3:52040:d=2020020100:TMP:2 m above ground:2 hour fcst:
  4:77996:d=2020020100:TMP:2 m above ground:3 hour fcst:
  5:103976:d=2020020100:TMP:2 m above ground:4 hour fcst:
  6:129840:d=2020020100:TMP:2 m above ground:5 hour fcst:
  7:155730:d=2020020100:TMP:2 m above ground:6 hour fcst:
  8:181608:d=2020020106:TMP:2 m above ground:anl:
  9:207509:d=2020020106:TMP:2 m above ground:1 hour fcst:
  10:233451:d=2020020106:TMP:2 m above ground:2 hour fcst:
  11:259410:d=2020020106:TMP:2 m above ground:3 hour fcst:
  . . .

This means that the 6 hour forecast is overwritten by the next forecast analysis.

In the following example we compute mean temperature over two consecutive months.
Calculation is done twice, first with :py:func:`pywgrib2_xr.open_dataset`, then
:py:func:`xarray.open_mfdataset` and ``engine=cfgrib``:

.. code-block:: python

    import sys
    import time
    from dask.distributed import Client
    import numpy as np
    import xarray as xr
    import pywgrib2_xr as pywgrib2

    f1 = '/tmp/tmp2m.l.gdas.201912.grib2'
    f2 = '/tmp/tmp2m.l.gdas.202001.grib2'

    def pywgrib2_():
        tmpl = pywgrib2.make_template(f2, reftime='2020-01-01T00:00:00')
        ds = pywgrib2.open_dataset([f1, f2], tmpl)
        tmp = ds['TMP.2_m_above_ground'][:,:-1,...]
        ds.close()
        return tmp.mean(['reftime', 'time1']).compute()

    def cfgrib():
        ds = xr.open_mfdataset([f1, f2], engine='cfgrib') # , chunks={'time': 1})
        tmp = ds['t2m'][:,:-1,...]
        ds.close()
        return tmp.mean(['time', 'step']).compute()

    if __name__ == '__main__':
        if sys.argv[1] == 'dask':
            client = Client()
            print(client)
        t = time.time()
        tmp1 = pywgrib2_()
        print('pywgrib2:', time.time() - t)
        t = time.time()
        tmp2 = cfgrib()
        print('cfgrib:', time.time() - t)
        assert np.allclose(tmp1.values[::-1,:], tmp2.values)  

The last line compares results. Since **pywgrib2** always converts grid orientation
to WE:SN, the y-axis has to be swapped. The first run is single-threaded, the second
uses dask distributed scheduler. **pywgrib2_xr** inventory and **cfgrib** index files
already exist. The timing is done on an 8-core AMD FX-8350 processor:

.. code-block:: console

    python example1.py single

.. parsed-literal::

    pywgrib2: 30.7
    cfgrib: 20.8

**cfgrib** is substantially faster. This is mostly due to the default chunking by
**pywgrib2_xr**, that is one chunk per model reference time. When analogous chunks
are set in the call to ``xr.open_mfdataset``, **cfgrib** run time increases to 30 s.

.. code-block:: console

    python example1.py dask

.. parsed-literal::

    <Client: 'tcp://127.0.0.1:38535' processes=4 threads=8, memory=33.56 GB>
    pywgrib2: 8.3
    cfgrib: 11.1

Here situation is reversed. There are only two files, so only two processes are
used by **cfgrib**. However with chunking, **cfgrib** is faster, the run time
is about 7 s.

The next example illustrates performance with with a typical archive, where each
data file contains weather elements for model run and one forecast time. We will
calculate average minimum temperature in the atmosphere over a period of one month.
The input files are GFS model with latitude-longitude projection at 0.5 deg resolution.
File is about 60 MB. We select mudel runs at 00Z and 12Z and forecast hours 0
(i.e. analysis), 3, 6 and 9. This gives valid times at every 3 hours. There are
31 * 2 * 4 = 248 files. The timing code calculates minimum temperature in a vertical
column 1000 to 100 hPa, then averages it over time:

.. code-block:: python

    import glob
    import sys
    import time
    from dask.distributed import Client
    import numpy as np
    import xarray as xr
    import pywgrib2_xr as pywgrib2

    files = sorted(glob.glob('gfs_4_201801??_?[02]*_00[0369].grb2'))
    
    def pywgrib2_():
        p = lambda x: x.varname == 'TMP' and x.level_code == 100
        tmpl = pywgrib2.make_template(files[:4], p, vertlevels='isobaric')
        ds = pywgrib2.open_dataset(files, tmpl) # , chunks={'time1': 1})
        tmp = ds['TMP.isobaric'][:,:,:21,:,:]
        ds.close()
        return tmp.min('isobaric1').mean(['reftime', 'time1']).compute()

    def cfgrib():
        args = {'filter_by_keys': {'typeOfLevel': 'isobaricInhPa', 'shortName': 't'}}
        nested = [files[::4], files[1::4], files[2::4], files[3::4]]
        ds = xr.open_mfdataset(nested, engine='cfgrib', backend_kwargs=args,
                                combine='nested', concat_dim=['step', 'time'])
        tmp = ds['t'][:,:,:21,:,:]
        ds.close()
        return tmp.min('isobaricInhPa').mean(['time', 'step']).compute()

    if __name__ == '__main__':
        if sys.argv[1] == 'dask':
            client = Client()
            print(client)
        t = time.time()
        tmp1 = pywgrib2_()
        print('pywgrib2: {:.1f} s'.format(time.time() - t))
        t = time.time()
        tmp2 = cfgrib()7.019040584564209
        print('cfgrib: {:.1f} s'.format(time.time() - t))
        assert np.allclose(tmp1.values[::-1,:], tmp2.values)
        ny = tmp1.shape[0]
        print('South Pole: {:.2f} degC'.format(tmp1[0,:].mean().values - 273.15))
        print('Equator: {:.2f} degC'.format(tmp1[ny//2+1,:].mean().values - 273.15))
        print('North Pole: {:.2f} degC'.format(tmp1[ny-1,:].mean().values - 273.15))

The most time consuming part is creation of inventory/index files. The reported times
are for runs where the inventory/index files have been created.

.. code-block:: console

    python example2.py single

.. parsed-literal::

    pywgrib2: 48.0 s
    cfgrib: 254.3 s

.. code-block:: console

    python example2.py dask

.. parsed-literal::

    pywgrib2: 23.4 s
    cfgrib: 98.5 s
    South Pole: -52.90 degC
    Equator: -81.05 degC
    North Pole: -69.65 degC

In this case, **cfgrib** default ``step`` chunk is 1. If the equivalent **pywgrib2**
chunk ``time1`` is also set to 1, the run time for single tread increases to
about 48 s, which is still much faster than **cfgrib** 4 min. The dask run time 
stays at about 23 s.

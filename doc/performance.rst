
Performance
===========

**pywgrib2** uses **wgrib2** code. It is iteresting to compare performance of
those two on common tasks.

The first task is converting GRIB file to netCDF. The GRIB file is GDAS 2m temperature
data for whole month that can be obtained
`here <ftp://ftp.ncep.noaa.gov/pub/data/nccf/com/cfs/prod/monthly/time>`_
The file size is about 20 MB. We compare run times of **wgrib2** and Python scripts
**cfgrib** and **pywgrib2**. The tests were ran several times, with no significant
differences in lapsed times::

  $ time wgrib2 tmp2m.gdas.l.201912.grib2 -inv /dev/null -netcdf x.nc

  real	0m9.814s
  user	0m9.696s
  sys	0m0.100s

  $ time cfgrib to_netcdf -o y.nc tmp2m.l.gdas.202002.grib2

  real	0m16.451s
  user	0m15.146s
  sys	0m0.714s

  $ time pywgrib2 template -t '2019-12-01T00' -o tmp2m.tmpl tmp2m.l.gdas.201912.grib2

  real	0m1.160s
  user	0m1.210s
  sys	0m0.417s

  time pywgrib2 to_nc -T tmp2m.tmpl -o tmp2m-pywgrib.nc tmp2m.l.gdas.201912.grib2

  real	0m12.577s
  user	0m12.401s
  sys	0m0.868s

**wgrib2** is the fastest, followed by **pywgrib2** and **cfgrib**.
One has to note that **wgrib2** does not handle this dataset correctly: it uses
forecast valid time as the time coordinate. The datafile contains analysis
and 1 to 6 hour forecast, every 6 hours::

  $ wgrib2 tmp2m.gdas.l.202002.grib2
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
:py:func:`xarray.open_mfdataset` and ``engine=cfgrib``::

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
      return tmp.mean(['reftime', 'time0']).compute()

  def cfgrib():
      ds = xr.open_mfdataset([f1, f2], engine='cfgrib')
      tmp = ds['t2m'][:,:-1,...]
      ds.close()
      return tmp.mean(['time', 'step']).compute()

  if __name__ == '__main__':
      if sys.argv[1] == 'dask':
          client = Client()
          print(client)
      t = time.time()
      tmp1 = ca()
      print('pywgrib2:', time.time() - t)
      t = time.time()
      tmp2 = it()
      print('cfgrib:', time.time() - t)
      assert np.allclose(tmp1.values[::-1,:], tmp2.values)  

The last line compares results. Since **pywgrib2** always converts grid orientation
to WE:SN, the y-axis has to be swapped. The first run is single-threaded, the second
uses dask distributed scheduler::

  $ python ex1.py single
  pywgrib2: 22.932976722717285
  cfgrib: 27.309120655059814

  $ python ex1.py dask
  pywgrib2: 8.07763957977295
  cfgrib: 12.438084363937378

  _ = dask.config.set(scheduler='single-threaded')
  file = '/tmp/tmp2m.l.gdas.202002.grib2'
  'pywgrib2'
  %time tmpl = pywgrib2.make_template(file, reftime='2020022900', collapse_names=True)
  %time pwg_ds = pywgrib2.open_dataset(file, tmpl)
  %time pwg_t2m = pwg_ds['TMP'][:,1:,...].mean(axis=(0, 1)).compute()
  pwg_ds
  'cfgrib'
  %time cfg_ds = xr.open_dataset(file, engine='cfgrib', chunks={'time': 1})
  %time cfg_t2m = cfg_ds['t2m'][:,1:,...].mean(axis=(0, 1)).compute()
  cfg_ds
  np.allclose(pwg_t2m, cfg_t2m)

The ``chunks`` argument to ``xr.open_mfdataset`` is added to make the dast arrays 
the same. Both pwgrib2 inventory and cfgrib index files were created earlier.
The output is::

  'pywgrib2'

  CPU times: user 10.7 ms, sys: 7.72 ms, total: 18.4 ms
  Wall time: 14.9 ms
  CPU times: user 600 ms, sys: 7.46 ms, total: 607 ms
  Wall time: 606 ms
  CPU times: user 5.53 s, sys: 343 ms, total: 5.88 s
  Wall time: 5.68 s

  <xarray.Dataset>
  Dimensions:    (latitude: 94, longitude: 192, reftime: 116, time0: 7)
  Coordinates:
      gaussian   int64 0
    * latitude   (latitude) float32 88.54195 86.65317 ... -86.65317 -88.54195
    * time0      (time0) timedelta64[ns] 00:00:00 01:00:00 ... 05:00:00 06:00:00
    * longitude  (longitude) float32 0.0 1.875 3.75 ... 354.375 356.25 358.125
    * reftime    (reftime) datetime64[ns] 2020-02-01 ... 2020-02-29T18:00:00
  Data variables:
      TMP        (reftime, time0, latitude, longitude) float32 dask.array<chunksize=(1, 7, 94, 192), meta=np.ndarray>
  Attributes:
      Projection:             gaussian
      Originating centre:     US National Weather Service - NCEP (WMC)
      Originating subcentre:  0
      History:                Created by pywgrib2-0.1.0
  
  'cfgrib'
  
  CPU times: user 166 ms, sys: 9.02 ms, total: 175 ms
  Wall time: 239 ms
  CPU times: user 8.56 s, sys: 39.8 ms, total: 8.6 s
  Wall time: 8.6 s

  <xarray.Dataset>
  Dimensions:            (latitude: 94, longitude: 192, step: 7, time: 116)
  Coordinates:
    * time               (time) datetime64[ns] 2020-02-01 ... 2020-02-29T18:00:00
    * step               (step) timedelta64[ns] 00:00:00 01:00:00 ... 06:00:00
      heightAboveGround  int64 ...
    * latitude           (latitude) float64 88.54 86.65 84.75 ... -86.65 -88.54
    * longitude          (longitude) float64 0.0 1.875 3.75 ... 354.4 356.2 358.1
      valid_time         (time, step) datetime64[ns] dask.array<chunksize=(1, 7), meta=np.ndarray>
  Data variables:
      t2m                (time, step, latitude, longitude) float32 dask.array<chunksize=(1, 7, 94, 192), meta=np.ndarray>
  Attributes:
      GRIB_edition:            2
      GRIB_centre:             kwbc
      GRIB_centreDescription:  US National Weather Service - NCEP 
      GRIB_subCentre:          0
      Conventions:             CF-1.7
      institution:             US National Weather Service - NCEP 
      history:                 2020-03-11T18:24:32 GRIB to CDM+CF via cfgrib-0....

  True

The same code running under dask distributed cluster::

  'pywgrib2'

  CPU times: user 14.1 ms, sys: 7.17 ms, total: 21.3 ms
  Wall time: 17.1 ms
  CPU times: user 723 ms, sys: 38 ms, total: 761 ms
  Wall time: 724 ms
  CPU times: user 635 ms, sys: 52.2 ms, total: 687 ms
  Wall time: 2.72 s
  . . .

  'cfgrib'

  CPU times: user 315 ms, sys: 31.4 ms, total: 346 ms
  Wall time: 396 ms
  CPU times: user 642 ms, sys: 62.6 ms, total: 704 ms
  Wall time: 2.99 s

In the single-theaded mode pywgrib2 was marginally faster, with dask distributed
the times are about the same.

The next example illustrates perforamance with with a typical archive, where each
data file contains weather elements for model run and one forecast time. We will
calculate average minimum temperature in the atmosphere over a period of one month.
The input files are GFS model with latitude-longitude projection at 0.5 deg resolution.
File is about 60 MB. We select mudel runs at 00Z and 12Z and forecast hours 0
(i.e. analysis), 3, 6 and 9. This gives valid times at every 3 hours. There are
31 * 2 * 4 = 248 files. The timing code is::

  import glob
  import sys
  import time
  from dask.distributed import Client
  import numpy as np
  import xarray as xr
  import pywgrib2_xr as pywgrib2

  files = sorted(glob.glob('/mnt/sdc1/work/grib/gfs/gfs_4_201801??_?[02]*_00[0369].grb2'))

  def mk_inv():
      for f in files:
          pywgrib2.save_inventory(pywgrib2.make_inventory(f), f)
    
  def pywgrib2_():
      p = lambda x: x.varname == 'TMP' and x.level_code == 100
      tmpl = pywgrib2.make_template(files[:4], p, vertlevels='isobaric')
      ds = pywgrib2.open_dataset(files, tmpl, chunks={'time0': 1})
      tmp = ds['TMP.isobaric'][:,:,:21,:,:]
      ds.close()
      return tmp.min('isobaric0').mean(['reftime', 'time0']).compute()

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
      tmp2 = cfgrib()
      print('cfgrib: {:.1f} s'.format(time.time() - t))
      assert np.allclose(tmp1.values[::-1,:], tmp2.values)
      ny = tmp1.shape[0]
      print('South Pole: {:.2f} degC'.format(tmp1[0,:].mean().values - 273.15))
      print('Equator: {:.2f} degC'.format(tmp1[ny//2+1,:].mean().values - 273.15))
      print('North Pole: {:.2f} degC'.format(tmp1[ny-1,:].mean().values - 273.15))

The most time consuming part is creation of inventory/index files. The first run takes
substantially longer than subsequent ones::

  $ python bar.py single
  pywgrib2: 189.4 s
  cfgrib: 552.1 s

  $ time python bar.py single
  pywgrib2: 49.4 s
  cfgrib: 243.4 s

  $ time python bar.py dask
  <Client: 'tcp://127.0.0.1:41603' processes=4 threads=8, memory=33.56 GB>
  pywgrib2: 18.0 s
  cfgrib: 96.4 s
  South Pole: -52.90 degC
  Equator: -81.05 degC
  North Pole: -69.65 degC


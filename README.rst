pywgrib2: GRIB2 library based on wgrib2
=======================================

.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml
.. _xarray: http://xarray.pydata.org
.. _wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2

**pywgrib2_xr** is a Python package to manipulate GRIB2 files.
The background engine is wgrib2_. **wgrib2**  is usually known as a standalone
executable. Recent releases contain C and Fortran library API. Version 3.0 comes
with low-level Python package **pywgrib2_s** (s for simple).
**pywgrib2_xr** (xr for xarray) decodes GRIB2 files to xarray datasets.
9It is influenced by cfgrib_, another Python package to read GRIB (version 1 and 2)
files, while trying to address **cfgrib** issues with some data files originating
at NCEP.

The process of reading GRIB2 files is done in two stages. The first one is creation
of a ``template``. The template is built by scanning a full set of data files
(i.e. without missing data) for a single arbitrary reference time, subject to
selection criteria.
Template encapsulates dataset structure. The idea comes from *AWIPS1* NetCDF template
files used to instantiate storage of gridded data.

In the second stage, GRIB2 files are decoded, each message fills a slice in the dataset
built from the template. the function ``open_dataset`` simply concatenates datasets
along the first dimension ``reftime``. This greatly simplifies handling of missing
data files.

**pywgrib2_xr** low-level interface provides the same capabilities as *wgrib2*
executable, including built-in remapping library iplib_.

Documentation
-------------

The documentation is on GitHub pages https://yt87.github.io/pywgrib2_xr

Licence
-------
**pywgrib2** is is released under
BSD Zero Clause Licence https://choosealicense.com/licenses/0bsd

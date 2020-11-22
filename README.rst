pywgrib2: GRIB2 library based on wgrib2
=======================================

.. _cartopy: https://scitools.org.uk/cartopy
.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml
.. _MetPy: https://unidata.github.io/MetPy/
.. _xarray: http://xarray.pydata.org
.. _wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2

**pywgrib2** is a Python package to convert GRIB2 files to xarray_ datasets.  
Those datasets can be visualised by cartopy_ and MetPy_. It comes with its own,
based on National Centers for Environmental Prediction (NCEP) library iplib_.

The background engine is wgrib2_: the Swiss army knife of tools for GRIB2.
Recently **wgrib2** added Fortran and C library programming interfaces.
**pywgrib2** adds Python to the list. The design is influenced by cfgrib_,
another Python package to read GRIB files, while trying to address **cfgrib**
shortfalls.

**pywgrib2** provides methods to read GRIB2 files (writing GRIB2 files is planned).
The high-level interface mimics xarray's functions :py:func:`xarray.open_dataset` and
:py:func:`xarray.open_mfdataset`. It is **not** another GRIB backend such as
**cfgrib**, due to a different concept of `datastore`.
**xarray** datastore is a file, the dataset obtained by reading that file
consists of a proper subset of messages in the file, subject to
selection criteria, if there is any. **pywgrib2** considers a datastore as
a logical unit, represented by one or more files. The only contraints are:
the reference time, coded in
`Section 1 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_sect1.shtml>`__
of a GRIB message and Grid Definition Template, that is 
`Section 1 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_sect3.shtml>`__
have to be the same for all messages in the datastore.

The process of reading GRIB files is done in two stages. The first one is creation
of a ``template``. The template is built by scanning a full set of data files
(i.e. without missing data) for a single arbitrary reference time, subject to
selection criteria.
Template encapsulates dataset structure. The idea comes from AWIPS1 NetCDF template
files used to instantiate storage of gridded data.

In the second stage, GRIB2 files are decoded, each message fills a slice in the dataset
built from the template. the function ``open_dataset`` simply concatenates datasets
along the first dimension ``reftime``. This greatly simplifies handling of missing
data files.

License
-------
**pywgrib2** is is released under
`MIT Licence <https://choosealicense.com/licenses/mit>__.

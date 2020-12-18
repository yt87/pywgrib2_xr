.. pywgrib2_xr documentation master file, created by
   sphinx-quickstart on Sun Oct 27 21:01:00 2019.

pywgrib2_xr: GRIB2 library based on wgrib2
==========================================

.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml
.. _xarray: http://xarray.pydata.org
.. _wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2

**pywgrib2_xr** is a Python package to manipulate GRIB2 files.
The background engine is wgrib2_. **wgrib2**  is known as an executable, recent 
releases added C and Fortran library API. Version 3.0 comes with low-level Python
package **pywgrib2_s** (s for simple). **pywgrib2_xr** (xr for xarray) decodes
GRIB2 files to xarray datasets. It is influenced by cfgrib_, another Python package
to read GRIB files, while trying to address **cfgrib** issues with some data files
originating at NCEP.

The low-level interface to **wgrib2** C-API can be used to write GRIB2 files. 

**pywgrib2_xr** comes with its own remapping library iplib_.


Documentation
-------------

**Getting Started**

* :doc:`overview`
* :doc:`installing`

.. toctree::
   :maxdepth: 1

   overview
   installing
..   :hidden:
..   :caption: Getting Started:

.. _user_guide:

**User Guide**

* :doc:`inventory`
* :doc:`template`
* :doc:`reading`
* :doc:`plotting`
* :doc:`remapping`
* :doc:`memory-buffers`
* :doc:`logging-and-exceptions`
* :doc:`writing-grib-files`
* :doc:`performance`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: User Guide

   inventory
   template
   reading
   plotting
   remapping
   memory-buffers
   logging-and-exceptions
   writing-grib-files
   performance


**Reference**

* :doc:`whats-new`
* :doc:`api`
* :doc:`pywgrib2`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Reference

   whats-new
   api
   pywgrib2

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/psf/black


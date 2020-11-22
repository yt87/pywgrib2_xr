.. pywgrib2 documentation master file, created by
   sphinx-quickstart on Sun Oct 27 21:01:00 2019.

pywgrib2: GRIB2 library based on wgrib2
=======================================

.. _cartopy: https://scitools.org.uk/cartopy
.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml
.. _MetPy: https://unidata.github.io/MetPy/
.. _xarray: http://xarray.pydata.org
.. _wgrib2: https://confluence.ecmwf.int/display/ECC/ecCodes+Home

**pywgrib2_xr** is a Python package to convert GRIB2 files to xarray_ datasets.  
Those datasets can be visualised by cartopy_ and MetPy_. It comes with its own,
based on National Centers for Environmental Prediction (NCEP) library iplib_.

The background engine is wgrib2_. Recently **wgrib2** - the Swiss army knife
of tools for GRIB2 added Fortran and C library interfaces. **pywgrib2** introduces
Python. It is heavily influenced by cfgrib_, another Python package to read GRIB
files, while trying to address **cfgrib** shortfalls.


Documentation
-------------

**Getting Started**

* :doc:`overview`
* :doc:`installing`

.. toctree::
   :maxdepth: 1
   :hidden:
   :caption: Getting Started:

   overview
   installing

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


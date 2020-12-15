.. currentmodule:: pywgrib2_xr

#############
API reference
#############

This page provides an auto-generated summary of pywgrib2's API. For more
details and examples, refer to the relevant chapters in the main part of the
documentation.

wgrib2 Interface
================

Memory Buffer
-------------

.. autosummary::
   :toctree: generated/

   MemoryBuffer
   MemoryBuffer.get
   MemoryBuffer.set
   MemoryBuffer.close
   MemoryBuffer.usage

RPNRegister
-----------

.. autosummary::
   :toctree: generated/

   RPNRegister
   RPNRegister.get
   RPNRegister.set
   RPNRegister.close
   RPNRegister.usage

Top-level functions
-------------------

.. autosummary::
   :toctree: generated/

   free_files
   status_open
   wgrib
   read_msg
   decode_msg
   write_msg

iplib Interface
===============

This is a Python interface to NCEP Interpolation library
`iplib <https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml>`__

.. autosummary::
   :toctree: generated/

   earth2grid_points
   grid2earth_grid
   grid2earth_points
   ips_grid
   ips_points
   ipv_grid
   ipv_points

Dataset
=======

Reading GRIB2 files
-------------------

.. autosummary::
   :toctree: generated/

   open_dataset

Accessors
---------

.. autosummary::
   :toctree: generated/

   Wgrib2DatasetAccessor
   Wgrib2DatasetAccessor.get_grid
   Wgrib2DatasetAccessor.location
   Wgrib2DatasetAccessor.grid
   Wgrib2DatasetAccessor.winds

Inventory
=========

Data structures
---------------

.. autosummary::
   :toctree: generated/

   MetaData
   MetaData.level_code
   MetaData.level_value

Creating inventory
------------------

.. autosummary::
   :toctree: generated/

   make_inventory
   save_inventory
   load_inventory
   load_or_make_inventory


Projection
==========

Creating a projection
---------------------

GRIB2 defines projection in terms of Grid Definition Template (Section 3 in
GRIB2 message), which includes also grid parameters such as number of points
and cell size. **pywgrib2** wraps it in a class :py:class:`pywgrib2_xr.Grid`.

.. autosummary::
   :toctree: generated/

   Point
   Grid
   grid_fromgds
   grid_fromdict
   grid_fromstring

Attributes
----------

.. autosummary::
   :toctree: generated/

   Grid.cfname
   Grid.gdtnum
   Grid.attrs
   Grid.coords
   Grid.crs
   Grid.dims
   Grid.globe
   Grid.params
   Grid.shape

Template
========

.. autosummary::
   :toctree: generated/

   Template
   make_template

Utilities
=========

Functions in this module are used to retrieve data for the test suite 
and documentation.

.. autosummary::
   :toctree: generated/

   utils.localpath
   utils.localpaths
   utils.remotepath



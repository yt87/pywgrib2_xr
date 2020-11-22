.. _installing:

Installation
============

Required dependencies
---------------------

* Required
   - Python (3.7 or later)
   - `xarray <http://xarray.pydata.org/>`__
   - `dask <http://dask.pydata.org>`__
   - `mypy_extensions <https://github.com/python/mypy_extensions>`__ (only for python-3.7)
   - `python-blosc <https://github.com/Blosc/python-blosc>`__
   - `wurlitzer <https://github.com/minrk/wurlitzer>`__
   - `wgrib2 <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/>`__

* Build
   - `Cython <https://cython.org/>`__
   - gfortran_linux-64 from conda. Recommended when building in conda environment.

* Optional, used only by :ref:`pywgrib2 <pywgrib2>` and the test suite.
   - `netcdf4 <https://github.com/Unidata/netcdf4-python>`__
   - `zarr <https://github.com/zarr-developers/zarr-python>`__

* Testing
   - `pytest <https://github.com/pytest-dev/pytest>`__
   - `dill <https://pypi.org/project/dill/>`__

* Documentation
   - `sphinx <https://www.sphinx-doc.org/en/master/>`__
   - `sphinx_rtd_theme <https://github.com/readthedocs/sphinx_rtd_theme>`__
   - `sphinxcontrib-programoutput <https://sphinxcontrib-programoutput.readthedocs.io/en/latest/>`__
   - `ipython <https://ipython.readthedocs.io/en/stable/index.html>`__
   - `matplotlib <https://matplotlib.org/>`__
   - `cfgrib <https://github.com/ecmwf/cfgrib>`__
   - `cf_xarray <https://cf-xarray.readthedocs.io/en/latest/index.html>`__
   - `metpy <https://unidata.github.io/MetPy/latest/index.html>`__

Instructions
------------

From the wheel
^^^^^^^^^^^^^^

This is a quick start for those who want to have a quick look at the package.
**pywgrib2_xr** and its dependencies will be installed in a separate conda environment.
Python wheels for 3.6 throught 3.9 are included with this distribution in directory
``wheels``. For Python 3.8 the steps are::

  $ conda create -n pywgrib2-test python=3.9
  $ conda activate pywgrib2-test
  (pywgrib2-test) $ pip install <path-to>pywgrib2-0.2.0-cp38-cp38-linux_x86_64.whl

From the source
^^^^^^^^^^^^^^^

The best way to proceed is to install all required dependencies with conda::

  $ conda create -n pywgrib2-test python=3.8 cython
  $ conda install gfortran_linux-64             # Linux, see below
  $ conda activate pywgrib2-test
  $ conda install dask python-blosc wurlitzer xarray
  $ conda install pytest dill netcdf4 zarr      # to run tests

The first step is to build shared library.

Building wgrib2 library
+++++++++++++++++++++++

**pywgrib2_xr** requires **wgrib2 3.0.0**. After downloading
`source code <ftp://ftp.cpc.ncep.noaa.gov/wd51we/wgrib2/>`__, edit top-level
makefile and ensure that ``MAKE_SHARED_LIB=1`` and ``USE_OPENMP=0`` (not strictly
neccessary, one can always set ``OMP_NUM_THREADS=1`` to avoid competition for
resources with dask). To save build time and disk space, set ``USE_NETCDF3=0``
and ``MAKE_FTN_API=0``. This can be achieved also by ``sed`` as shown below.

Linux
"""""

On Linux is advisable to use conda-provided compiler to build **wgrib2** shared library.
On Fedora-32 there is a conflict between system libgfortran.so.5.0.0 and the same
version installed by conda. When the shared library is built with gcc/gfortran-10,
import of pywgrib2_xr will fail because of missing symbol ``GFORTRAN_10``.
Conda compilers are available via environmental variables ``GCC`` and ``GFORTRAN``::

  $ export CC=$GCC
  $ export FC=$GFORTRAN
  $ unset FFLAGS
  $ export COMP_SYS=gnu_linux
  $ sed -i 's/^MAKE_FTN_LIB=1/MAKE_FTN_LIB=0/;s/^USE_OPENMP=1/USE_OPENMP=0/;s/^USE_NETCDF3=1/USE_NETCDF3=0/' makefile
  $ make lib

.. note::
   conda defines environmental variables CFLAGS and FFLAGS providing compiler
   optimizations that conflict with values set in **wgrib2** ``makefile``.
   A diligent merge can be made, the imperative is to remove ``-fopenmp``. 
   The easiest way to do it is to unset conda provided ``FFLAGS`` as shown above.

MaxOS
"""""

Mac does not not come with a Fortran compiler. The C default compiler, confusingly
named gcc, is Apple's clang implementation. The real gcc/gfortran can be installed
with **brew**. The most recent version is 10.2. The steps are::

  $ export CC=/usr/local/bin/gcc-10
  $ export FC=/usr/local/bin/gfortran
  $ export COMP_SYS=gnu_mac
  $ sed -i '.backup' 's/^MAKE_FTN_LIB=1/MAKE_FTN_LIB=0/;s/^USE_OPENMP=1/USE_OPENMP=0/;s/^USE_NETCDF3=1/USE_NETCDF3=0/' makefile
  $ make lib
  $ install_name_tool -id @rpath/libwgrib2.dylib lib/libwgrib2.dylib

See 
`stackoverflow <https://stackoverflow.com/questions/19123623/python-runtime-library-dirs-doesnt-work-on-mac>`__
for an explanation of the last step.

Building pywgrib2_xr
++++++++++++++++++++

Edit `setup.cfg` to set ``library_dir`` and ``include_dir``. Then run::

  $ python setup.py develop

**pywgrib2_xr** comes with the test suite. To run the tests::

  $ pytest tests

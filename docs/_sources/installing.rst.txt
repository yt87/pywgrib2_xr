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
   - `libwgrib2 <https://github.com/yt87/libwgrib2>`__

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
   - `matplotlib <https://matplotlib.org/>`__
   - `cfgrib <https://github.com/ecmwf/cfgrib>`__
   - `cf_xarray <https://cf-xarray.readthedocs.io/en/latest/index.html>`__
   - `metpy <https://unidata.github.io/MetPy/latest/index.html>`__

..   - `ipython <https://ipython.readthedocs.io/en/stable/index.html>`__

Instructions
------------

With conda
^^^^^^^^^^

From within conda environment:

.. parsed-literal::

    conda install -c yt87 pywgrib2_xr

From the source
^^^^^^^^^^^^^^^

The best way to proceed is to install all required dependencies with conda:

.. parsed-literal::

    conda create -n test python=3.8 cython gcc_linux-64 numpy
    conda activate test
    conda install dask python-blosc wurlitzer xarray
    conda install pytest dill netcdf4 zarr      # to run tests
    conda install -c yt87 libwgrib2

Then, from the base of the source directory:

.. parsed-literal::

    python setup.py develop

The conda compiler will find *libwgrib2* and its header files. Native gcc works
as well, but one has to set ``library_dir`` and ``include_dir`` in *setup.cfg*.

**pywgrib2_xr** comes with the test suite. To run the tests, execute:

.. parsed-literal::

    pytest tests

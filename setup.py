#!/usr/bin/env python

import configparser
import platform
import os
import sys
from setuptools import setup, find_packages
from distutils.extension import Extension

try:
    from Cython.Build import cythonize
except ImportError:
    use_cython = False
else:
    use_cython = True
cython_ext = "pyx" if use_cython else "c"

import numpy

DISTNAME = "pywgrib2_xr"
LICENCE = "Public Domain"
AUTHOR = "George Trojan"
AUTHOR_EMAIL = "george.trojan@gmail.com"
URL = "one"
DESCRIPTION = "Python API for wgrib2"
LONG_DESCRIPTION = """
**pywgrib2** is a Python package to convert GRIB2 files to xarray_ datasets.  
Those datasets can be visualised by cartopy_ and MetPy_. It comes with its own,
based on National Centers for Environmental Prediction (NCEP) library iplib_.

The background engine is wgrib2_: the Swiss army knife of tools for GRIB2.
Recently **wgrib2** added Fortran and C library programming interfaces.
**pywgrib2** adds Python to the list. The design is influenced by cfgrib_,
another Python package to read GRIB files, while trying to address **cfgrib**
shortfalls.

**pywgrib2** provides methods to read and write GRIB2 files.
The high-level interface mimics xarray's functions ``xarray.open_dataset`` and
``xarray.open_mfdataset``. It is **not** another GRIB backend such as
**cfgrib**, due to a different concept of ``datastore``.
**xarray** datastore is a file, the dataset obtained by reading that file
consists of a proper subset of messages in the file, subject to
selection criteria, if there is any. **pywgrib2** considers a datastore as
a logical unit, represented by one or more files. 
The only contraints are: the reference time, coded in
`Section 1 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_sect1.shtml>`__
of a GRIB message and Grid Definition Template, that is 
`Section 1 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_sect3.shtml>`__
have to be the same for all messages in the datastore.

The process of reading GRIB files is done in two stages. The first one is creation of
a `template`. The template is built by scanning a full set of data files (i.e. without
missing data) for a single arbitrary reference time, subject to selection criteria.
Template encapsulates dataset structure. The idea comes from AWIPS1 NetCDF template
files used to instantiate storage of gridded data.

In the second stage, GRIB files are decoded, each message fills a slice in the dataset
built from the template. The function ``open_dataset`` simply concatenates datasets along
the first dimension `reftime`. This greatly simplifies handling of missing data files.

.. _cartopy: https://scitools.org.uk/cartopy
.. _cfgrib: https://github.com/ecmwf/cfgrib
.. _iplib: https://www.nco.ncep.noaa.gov/pmb/docs/libs/iplib/ncep_iplib.shtml
.. _MetPy: https://unidata.github.io/MetPy/
.. _xarray: http://xarray.pydata.org
.. _wgrib2: https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2
"""
CLASSIFIERS = [
    "Development Status :: 3 - Alpha",
    "License :: Public Domain",
    "Operating System :: POSIX :: Linux",
    "Operating System :: MacOS :: MacOS X",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python",
    "Programming Language :: Python :: 3.7",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Topic :: Scientific/Engineering",
]
PYTHON_REQUIRES = ">= 3.6"
SETUP_REQUIRES = ["numpy >= 1.16"]
INSTALL_REQUIRES = [
    "xarray >= 0.14",
    "dask >= 2.11",
    "blosc >= 1.9",
    "wurlitzer >= 2",
    # "toolz >= 0.1",    # import from dask fails, pywgrib2_xr does not use toolz yet.
]
if sys.version_info < (3, 8): 
    INSTALL_REQUIRES.append("mypy_extensions >= 0.4.3")
TESTS_REQUIRE = ["pytest >= 3", "netcdf4 >= 1.4"]

MAJOR = 0
MINOR = 2
MICRO = 1
VERSION = "{:d}.{:d}.{:d}".format(MAJOR, MINOR, MICRO)

numpy_incdir = numpy.get_include()

# to retrieve wgrib2 library location
setup_cfg = "setup.cfg"
config = configparser.ConfigParser()
config.read(setup_cfg)
d = config.get("paths", "library_dir", fallback=None)
library_dir = os.path.abspath(d) if d else None
d = config.get("paths", "include_dir", fallback=None)
include_dir = os.path.abspath(d) if d else None
fc_macro = config.get("compilers", "fc_macro", fallback="GFORTRAN")


def get_extensions():
    extra_link_args = []
    library_dirs = []
    if library_dir:
        library_dirs = runtime_library_dirs = [library_dir]
        # https://stackoverflow.com/questions/19123623/python-runtime-library-dirs-doesnt-work-on-mac
        if platform.system() == 'Darwin':
            extra_link_args = ["-Wl,-rpath,{:s}".format(library_dir)]
    include_dirs=[numpy_incdir]
    if include_dir:
        include_dirs.append(include_dir)
    extns = [
        Extension(
            name="pywgrib2_xr._wgrib2",
            sources=[
                "pywgrib2_xr/geolocation.c",
                "pywgrib2_xr/_wgrib2.{:s}".format(cython_ext)
                ],
            # macros needed to process wgrib2_api.h/ipolates.h
            define_macros=[(fc_macro, None),
                           ("USE_IPOLATES", "3"),
                           # For future Cython
                           # ("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION"),
                          ],
            include_dirs=include_dirs,
            library_dirs=library_dirs,
            runtime_library_dirs=library_dirs,
            extra_compile_args=["-g"],
            extra_link_args=extra_link_args,
            libraries=["wgrib2"],
        )
    ]
    compiler_directives = {"language_level": sys.version_info[0]}
    return (
        cythonize(extns, compiler_directives=compiler_directives, gdb_debug=False)
        if use_cython
        else extns
    )


console_scripts = ["pywgrib2 = pywgrib2_xr.script:main"]

metadata = dict(
    name=DISTNAME,
    description=DESCRIPTION,
    long_description_content_type="text/x-rst",
    long_description=LONG_DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENCE,
    classifiers=CLASSIFIERS,
    platforms=["Linux", "MacOS X"],
    packages=find_packages(),
    ext_modules=get_extensions(),
    test_suite="tests",
    version=VERSION,
    python_requires=PYTHON_REQUIRES,
    setup_requires=SETUP_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    entry_points={"console_scripts": console_scripts},
    zip_safe=False,
)


def write_version(filename="pywgrib2_xr/version.py"):
    with open(filename, "w") as fp:
        fp.write('version = "%s"\n' % VERSION)


if __name__ == "__main__":
    write_version()
    setup(**metadata)

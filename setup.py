#!/usr/bin/env python

import configparser
import platform
import os
import sys

import versioneer
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
LICENCE = "BSD-0-Clause"
AUTHOR = "George Trojan"
AUTHOR_EMAIL = "george.trojan@gmail.com"
URL = "one"
DESCRIPTION = "Python API for wgrib2"
LONG_DESCRIPTION = """
pywgrib2 is a Python package to convert GRIB2 files to xarray_ datasets.  
Those datasets can be visualised by cartopy and MetPy. It comes with its own
remapping capability, based on NCEP library iplib.

The background engine is wgrib2: the Swiss army knife of tools for GRIB2.
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
PYTHON_REQUIRES = ">= 3.7"
SETUP_REQUIRES = ["numpy >= 1.16"]
INSTALL_REQUIRES = [
    "xarray >= 0.16",
    "dask >= 2.11",
    "blosc >= 1.9",
    "wurlitzer >= 2",
]
if sys.version_info < (3, 8): 
    INSTALL_REQUIRES.append("mypy_extensions >= 0.4.3")
TESTS_REQUIRE = ["pytest >= 3", "netcdf4 >= 1.4"]

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

setup(
    name=DISTNAME,
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
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
    python_requires=PYTHON_REQUIRES,
    setup_requires=SETUP_REQUIRES,
    install_requires=INSTALL_REQUIRES,
    tests_require=TESTS_REQUIRE,
    entry_points={"console_scripts": console_scripts},
    zip_safe=False,
)

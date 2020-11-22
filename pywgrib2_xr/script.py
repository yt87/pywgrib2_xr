"""This is a stand-alone script installed as **pywgrib2**.
It provides the following functionality:

    1. List content of a GRIB2 file (same as **wgrib2** without options).
    2. Create inventory files.
    3. List content of inventory files.
    4. Convert GRIB2 files to netCDF4.
    5. Convert GRIB2 files to zarr.
    6. Emulates **wgrib2** executable.
"""

from functools import partial
import getopt
import glob
from multiprocessing.pool import Pool
import pickle
import os
import sys
from typing import List, Optional  # , Sequence

from .inventory import (
    FileMetaData,
    MetaData,
    load_inventory,
    make_inventory,
    save_inventory,
)
from .template import make_template
from .wgrib2 import wgrib
from .xarray_store import open_dataset

_inv_ext = ".binv"

USAGE = """USAGE: pywgrib2 [-h] | [command [option ...]] argument ...

where:
    -h
        Print this message and exit.

    When command is not specified, the script emulates wgrib2 executable.

    command:
        list_inv
            Displays content of GRIB file(s).

            Options:
                -L
                    Long listing (all metadata). Default is short

            Arguments:
                gribfile ...
                    One or more GRIB files.

        make_inv
            Makes inventory file[s]

            Options:
                -i inv-dir
                    Directory for inventory files. Will be created if does not exist.
                    Intended for read-only GRIB directories.
                -n num-procs
                    Number of processes in multiprocessing mode. Default is 1.
                -p pattern
                    "glob.glob" pattern.
                -r
                    Recursively search grib-dir subdirectories.

            Arguments:
                gribfile ...
                    Zero (only if -r or -p is specified) or more GRIB files.

        cat_inv
            Lists content of inventory file[s].
            Use when inventories coexist with GRIB files.

            Options:
                -d dir
                    Directory of GRIB files
                -r
                    Recursively search subdirectories for inventory files.

            Arguments:
                gribfile ...
                    Zero or more GRIB files. The extension ".binv" does not need
                    to be included.

            The final list of files comprises directory entries and explicit
            paths.

        cat_hash
            Lists content of inventory file[s].
            Use when inventories are not collocated with GRIB files
            (i.e. -i inv_dir was specified for make_inv).

            Arguments:
                invfile ...
                    One or more GRIB files. The extension ".binv" does not need
                    to be included.

        template:
            Writes template file.

            Options:
                -i inv_dir
                    Location of inventory files, if different from GRIB files.
                -t reftime
                    Reference time, necessary when GRIB files have messages
                    with more than one reference time.
                -o template
                    Output file name. Must be specified.

            Arguments:
                gribfile ...
                    One or more GRIB files.

        to_nc:
            Writes netcdf file.

            Options:
                -c
                    Compress file, with zlib and compression level 1.
                -o ncfile
                    Output file name. Must be specified.
                -T template
                    Template file name. Must be specified.

            Arguments:
                gribfile ...
                    One or more GRIB files.

        to_zarr:
            Writes zarr group.

            Options:
                -c level
                    Compression level, an integer between 1 and 4. Default is 1.
                -o store
                    Output directory. Must be specified.
                -T template
                    Template file name. Must be specified.

            Arguments:
                gribfile ...
                    One or more GRIB files.
"""


def _print_inventory(inventory: Optional[List[MetaData]], listing: str) -> None:
    if not inventory:
        return
    if listing == "full":
        for i in inventory:
            print(i)
        return
    file = inventory[0].file
    file_inv = FileMetaData(file, inventory)
    if listing == "long":
        print(repr(file_inv))
    else:
        print(file_inv)


def list_inv(args: List[str]) -> None:
    opts, pargs = getopt.getopt(args, "L")
    kwds = dict(opts)
    listing = kwds.get("-L", "short")
    for p in pargs:
        if os.path.isfile(p):
            inventory = make_inventory(p)
            if inventory:
                _print_inventory(inventory, listing)
            else:
                print("No GRIB messages in {:s}".format(p))
        else:
            print("{:s} is not a file".format(p))


def _f(p, d):
    save_inventory(make_inventory(p), p, d)


def make_inv(args: List[str]) -> None:
    opts, pargs = getopt.getopt(args, "hi:n:p:")
    kwds = dict(opts)
    recursive = "-r" in kwds
    inv_dir = kwds.get("-i")
    num_processes = int(kwds.get("-n", 1))
    if not 1 <= num_processes <= 4:
        raise ValueError("Number of processes must be between 1 and 4")
    pattern = kwds.get("-p")
    if pattern:
        files = [
            p
            for p in glob.glob(pattern, recursive=recursive)
            if os.path.isfile(p) and not p.endswith(_inv_ext)
        ]
    else:
        files = []
    files.extend(pargs)

    fun = partial(_f, d=inv_dir)

    if num_processes == 1:
        for file in files:
            fun(file)
    else:
        with Pool(num_processes) as pool:
            pool.map(fun, files)


def cat_inv(args: List[str]) -> None:
    opts, pargs = getopt.getopt(args, "d:hi:Lr")
    kwds = dict(opts)
    recursive = "-r" in kwds
    data_dir = kwds.get("-d")
    listing = kwds.get("-L", "short")
    if data_dir:
        if recursive:
            pattern = os.path.join(data_dir, "**", "*" + _inv_ext)
        else:
            pattern = os.path.join(data_dir, "*" + _inv_ext)
        files = glob.glob(pattern, recursive=recursive)
    else:
        files = []
    files.extend(pargs)
    for file in files:
        base, ext = os.path.splitext(file)
        f = base if ext == _inv_ext else file
        inventory = load_inventory(f)
        _print_inventory(inventory, listing)


def cat_hash(args: List[str]) -> None:
    opts, pargs = getopt.getopt(args, "L")
    kwds = dict(opts)
    listing = kwds.get("-L", "short")
    for arg in pargs:
        base, ext = os.path.splitext(arg)
        file = base if ext == _inv_ext else arg
        inventory = load_inventory(file)
        _print_inventory(inventory, listing)


def mk_tmpl(args) -> None:
    opts, pargs = getopt.getopt(args, "i:o:t:v:")
    kwds = dict(opts)
    inv_dir = kwds.get("-i")
    tmplfile = kwds.get("-o")
    if tmplfile is None:
        raise ValueError("Missing output file")
    reftime = kwds.get("-t")
    vertlevel = kwds.get("-v")
    template = make_template(
        pargs, reftime=reftime, invdir=inv_dir, vertlevels=vertlevel
    )
    with open(tmplfile, "wb") as fp:
        pickle.dump(template, fp)


def to_nc(args: List[str]) -> None:
    opts, pargs = getopt.getopt(args, "co:T:")
    kwds = dict(opts)
    compress = "-c" in kwds
    ncfile = kwds.get("-o")
    if ncfile is None:
        raise ValueError("Missing output file")
    tmplfile = kwds.get("-T")
    if tmplfile is None:
        raise ValueError("Missing template file")
    with open(tmplfile, "rb") as fp:
        template = pickle.load(fp)
    ds = open_dataset(pargs, template=template)
    vars = list(ds.data_vars.keys())
    vars.extend(["longitude", "latitude"])
    encoding = dict.fromkeys(vars, {"zlib": True, "complevel": 1}) if compress else None
    ds.to_netcdf(ncfile, engine="netcdf4", encoding=encoding)


def to_zarr(args: List[str]) -> None:
    import zarr

    opts, pargs = getopt.getopt(args, "c:o:T:")
    kwds = dict(opts)
    clevel = int(kwds.get("-c", 1))
    if not 1 <= clevel <= 9:
        raise ValueError("Invalid compression level {:d}".format(clevel))
    zarrdir = kwds.get("-o")
    if zarrdir is None:
        raise ValueError("Missing output file")
    tmplfile = kwds.get("-T")
    if tmplfile is None:
        raise ValueError("Missing template file")
    with open(tmplfile, "rb") as fp:
        template = pickle.load(fp)
    ds = open_dataset(pargs, template=template)
    compressor = zarr.Blosc(cname="zstd", shuffle=-1, clevel=clevel)
    vars = list(ds.data_vars.keys())
    vars.extend(["longitude", "latitude"])
    encoding = dict.fromkeys(vars, {"compressor": compressor})
    ds.to_zarr(zarrdir, consolidated=True, encoding=encoding)


commands = {
    "list_inv": list_inv,
    "make_inv": make_inv,
    "cat_inv": cat_inv,
    "cat_hash": cat_hash,
    "template": mk_tmpl,
    "to_nc": to_nc,
    "to_zarr": to_zarr,
}


def main(argv: Optional[List[str]] = None):
    if not argv:
        argv = sys.argv[1:]
    if argv[0] == "-h":
        print(USAGE)
        raise SystemExit
    # if (f := commands.get(argv[1])):
    f = commands.get(argv[0])
    if f:
        f(argv[1:])
    else:
        wgrib(*argv)


if __name__ == "__main__":
    main()

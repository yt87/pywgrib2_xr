from datetime import datetime
import logging

import numpy as np

from . import WgribError, UNDEFINED
from .wgrib2 import MemoryBuffer, RPNRegister, wgrib, free_files

logger = logging.getLogger(__name__)


def read_msg(gribfile, num_or_meta):
    """Returns single message from GRIB2 file as bytes.

    Parameters
    ----------
    gribfile : str or MemoryBuffer
        Destination file.
    num_or_meta : message number or MetaData
        message number or MetaData for the message in the template.

    Returns
    -------
    msg : bytes
        Undecoded GRIB2 message.

    Raises
    ------
    pywgrib2_xr.WgribError
        When wgrib call fails.
    """
    if isinstance(num_or_meta, int) or isinstance(num_or_meta, str):
        offset = num_or_meta
    else:
        offset = num_or_meta.offset
    with MemoryBuffer() as buf:
        args = [
            gribfile,
            "-rewind_init",
            gribfile,
            "-inv",
            "/dev/null",
            "-d",
            offset,
            "-grib",
            buf,
        ]
        try:
            wgrib(*args)
            return buf.get()
        except WgribError:
            raise
        finally:
            free_files(gribfile)


def decode_msg(gribfile, meta):
    """Returns decoded GRIB2 file as numpy array.

    Parameters
    ----------
    gribfile : str or MemoryBuffer
        Destination file.
    meta : MetaData
        MetaData for the message in the template.

    Returns
    -------
    arr : np.ndarray
        GRIB2 message data.

    Raises
    ------
    pywgrib2_xr.WgribError
        When wgrib call fails.
    """
    offset = meta.offset
    with MemoryBuffer() as buf:
        args = [
            gribfile,
            "-rewind_init",
            gribfile,
            "-inv",
            "/dev/null",
            "-d",
            offset,
            "-no_header",
            "-bin",
            buf,
        ]
        try:
            wgrib(*args)
            return buf.get("a").reshape((meta.ny, meta.nx))
        except WgribError:
            raise
        finally:
            free_files(gribfile)


def write_msg(gribfile, tmplfile, num_or_meta, data=None, append=False, **kwargs):
    """Writes message to a GRIB2 file.

    Parameters
    ----------
    gribfile : str or MemoryBuffer
        Destination GRIB file.
    tmplfile : str or MemoryBuffer
        Template GRIB file.
    num_or_meta : int or MetaData
        Message number or Metadata for the message in the template.
    append : bool
        Append message to gribfile. Default is False.
    data : array_like or None
        Data to be written. When None, only metadata is updated.
    **kwargs
        Optional arguments setting metadata: item=value, which results in
        arguments `set_item, value` passed to `wgrib2`.
        Valid items are:

        - metadata : metadata string, see https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/set_metadata.html
        - date : reference time (datetime or ISO format str)
        - ftime : forecast time (wgrib2 format str)
        - var : variable name
        - lev : level
        - grib_type : compression = {'jpeg', 'simple', 'complex[1|2|3]', 'aec', 'same'}
        - bin_prec : precision ECMWF style, in bits <= 24

    Raises
    ------
    pywgrib2_xr.WgribError
        When wgrib call fails

    Examples
    --------
      Update forecast time, preserve data values::

        write_msg(outfile, tmplfile, meta, ftime=ftime)

      Write average RH in a layer using metadata of RH at some level::

        write_msg(outfile, tmplfile, meta, data=rh_ave, lev='surface - 700 mb', bin_prec=8)

    """
    if isinstance(num_or_meta, int) or isinstance(num_or_meta, str):
        offset = num_or_meta
    else:
        offset = num_or_meta.offset
    args = [tmplfile, "-rewind_init", tmplfile, "-d", offset, "-inv", "/dev/null"]
    valid_args = set(
        ["metadata", "date", "var", "lev", "ftime", "grib_type", "bin_prec"]
    )
    out = "-grib" if data is None else "-grib_out"
    # metadata is first source, var, lev are applied afterwards
    if "metadata" in kwargs:
        v = kwargs.pop("metadata")
        args.extend(["-set_metadata_str", v])
    if "date" in kwargs:
        v = kwargs.pop("date")
        if isinstance(v, str):
            v = datetime.fromisoformat(v)
        v = v.strftime("%Y%m%d%H%M%S")
        args.extend(["-set_date", v])
    if "var" in kwargs:
        v = kwargs.pop("var")
        args.extend(["-set_var", v])
    if "lev" in kwargs:
        v = kwargs.pop("lev")
        args.extend(["-set_lev", v])
    if "ftime" in kwargs:
        v = kwargs.pop("ftime")
        args.extend(["-set_ftime", v])
    if "grib_type" in kwargs:
        v = kwargs.pop("grib_type")
        args.extend(["-set_grib_type", v])
        out = "-grib_out"

    try:
        # set grid point data
        # -rpn will clear scaling parameters, so set grid point data first
        if data is not None:
            reg = RPNRegister()
            data = np.asarray(data)
            data[np.isnan(data)] = UNDEFINED
            reg.set(data)
            args.extend(["-rpn_rcl", reg])
        else:
            reg = None
        if "bin_prec" in kwargs:
            args.extend(["-set_grib_max_bits", 24])
            v = kwargs.pop("bin_prec")
            args.extend(["-set_bin_prec", v])
        if append:
            args.append("-append")
        args.extend([out, gribfile])
        wgrib(*args)
    except WgribError:
        raise
    finally:
        free_files(tmplfile, gribfile)
        if reg is not None:
            reg.close()
        


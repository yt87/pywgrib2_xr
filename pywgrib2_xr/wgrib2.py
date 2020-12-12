import functools
from io import StringIO
import logging
import os
import warnings

import numpy as np
from wurlitzer import pipes

from . import WgribError, _wgrib2  # type: ignore

# from wgrib2.h: N_mem_buffers and N_RPN_REGS
N_MEM_BUF = 30  # Number of memory buffers
N_RPN_REG = 20  # Number of RPN registers

logger = logging.getLogger(__name__)

# Private exception that should be raised by functions decorated by organs on error
class _WgribError(Exception):
    pass


# Wurlitzer organs
def organs(func):
    """Decorator to capture of C-emitted output to stderr."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args:
            logger.debug("args: {!r}".format(args))
        if kwargs:
            logger.debug("kwargs: {!r}".format(kwargs))
        _err = StringIO()
        with pipes(stdout=None, stderr=_err):
            try:
                ret = func(*args, **kwargs)
            except _WgribError as e:
                import time
                time.sleep(0.2)  # Wurlitzer.flush_interval
                raise WgribError(_err.getvalue()) from e
        err = _err.getvalue()
        if err:
            warnings.warn("\n" + err, stacklevel=2)
        # FIXME: testing overhead
        # ret = func(*args, **kwargs)
        # if ret is None:
        # Fatal error, by convention
        #     raise WgribError('Some error')
        return ret

    return wrapper


# def set_num_threads(nthreads):
#    """Set number of threads for `wgrib2`.
#
#    Parameters
#    ----------
#    nthreads: int
#        Number of threads.
#    """
#    _wgrib2.set_num_threads(nthreads)
def set_num_threads(num_threads):
    if num_threads < 1:
        num_threads = 1
    os.environ["OMP_NUM_THREADS"] = str(num_threads)


class MemoryBuffer:
    """Encapsulates `wgrib2` memory buffer.

    Keeps track of `wgrib2` memory buffers. Implemented as a context manager.

    Examples
    --------
    >>> with MemoryBuffer() as reg:
    ...     do_something_with(buf)

    or (does the same thing)

    >>> buf = MemoryBuffer()
    >>> do_something_with(buf)
    >>> buf.close()
    """

    _buflen = N_MEM_BUF
    _buffers = [0] * _buflen

    def __init__(self):
        """Finds available buffer.

        Maximum number of buffers is 30.

        Raises
        ------
        WgribError
            If there are no free buffers left.
        """
        self._n = self._bind()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._buffers[self._n] = 0

    def __repr__(self):
        return "@mem:{:d}".format(self._n)

    @classmethod
    def usage(cls):
        """Returns copy of buffer array.

        Intended for debugging resource leaks.

        Returns
        -------
        list
            Content of internal buffer array. One means buffer in use.
        """
        return cls._buffers.copy()

    @classmethod
    def _bind(cls):
        for i in range(0, cls._buflen):
            if cls._buffers[i] == 0:
                cls._buffers[i] = 1
                return i
        raise WgribError("No free buffers")

    def get(self, rtype="b"):
        """Returns buffer content.

        Parameters
        ----------
        rtype : str
            Return type. One of 'a' - np.ndarray, 'b' - bytes, 's' - str.
            Default is 'b'.
        """
        bytes = _wgrib2.get_mem_buf(self._n)
        if bytes is None:
            raise WgribError("wgrib2_get_mem_buffer failed")
        if rtype == "b":
            return bytes
        elif rtype == "s":
            return bytes.decode()
        elif rtype == "a":
            return np.frombuffer(bytes, dtype=np.float32)
        else:
            raise ValueError(
                "Invalid argument {:s}, must be 'a', 'b' or 's')".format(rtype)
            )

    def set(self, data):
        """Initialises buffer with `data`.

        Parameters
        ----------
        data : bytes, str or ndarray
        """
        if isinstance(data, str):
            data = data.encode()
        elif isinstance(data, np.ndarray):
            data = np.ascontiguousarray(data, dtype=np.float32).tobytes()
        ret = _wgrib2.set_mem_buf(self._n, data)
        if ret:
            raise WgribError("wgrib2_set_mem_buffer (malloc) failed")

    def close(self):
        """Makes buffer free for reuse."""
        self._buffers[self._n] = 0


class RPNRegister:
    """Encapsulates `wgrib2` RPN register.

    Keeps track of `wgrib2` registers. Implemented as a context manager.

    Examples
    --------
    >>> with RPNRegister() as reg:
        ... do_something_with(reg)

    or (does the same thing)

    >>> reg = RPNRegister()
    >>> do_something_with(reg)
    >>> reg.close()
    """

    _buflen = N_RPN_REG
    _buffers = [0] * _buflen

    def __init__(self):
        """Finds available register.

        Maximum number of registers is 20.

        Raises
        ------
        WgribError
            If there are no free registers left.
        """
        self._n = self._bind()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._buffers[self._n] = 0

    def __repr__(self):
        return str(self._n)

    # def __str__(self):
    #    return str(self._n)

    @classmethod
    def usage(cls):
        """Returns copy of register array.

        Intended for debugging resource leaks.

        Returns
        -------
        list
            Content of internal register array. Ones mean registers in use.
        """
        return cls._buffers.copy()

    @classmethod
    def _bind(cls):
        for i in range(cls._buflen):
            if cls._buffers[i] == 0:
                cls._buffers[i] = 1
                return i
        raise WgribError("No free buffers")

    def get(self):
        """Returns content of the register.

        Returns
        -------
        np.array
            Register data as 1-D array
        """
        arr = _wgrib2.get_reg_data(self._n)
        if arr is None:
            raise WgribError("wgrib2_get_reg_data failed")
        return arr

    def set(self, arr):
        """Initialises register with data.

        Parameters
        ----------
        arr : array-like
        """
        arr = np.ascontiguousarray(arr, dtype=np.float32).ravel()
        ret = _wgrib2.set_reg_data(self._n, arr)
        if ret:
            raise WgribError("wgrib2_set_reg (malloc) failed")

    def close(self):
        """Makes register free for reuse."""
        self._buffers[self._n] = 0


@organs
def free_files(*files, delete=False):
    """Closes and removes `files` from wgrib2 linked list.

    Optionally unlinks those files.

    Parameters
    ----------
    *files : str
        Name(s) of files to close.
    delete: bool
        Unlink closed files. Default is False.
    """
    for file in files:
        _wgrib2.free_file(file.encode())
        if delete:
            try:
                os.unlink(file)
            except OSError as e:
                logger.warning("Failed to remove {:s}: {!r}".format(file, e))


@organs
def status_open():
    """Prints open files to stderr.

    This is a debug utility function.
    """
    _wgrib2.status_open()


@organs
def wgrib(*args):
    """Mimics `wgrib2` executable.

    `wgrib2` output is captured. If it exits with non-zero status,
    the output is passed to :py:exc:`~pywgrib2_xr.WgribError`,
    else a warning is emmited.

    Parameters
    ----------
    args : str
        Arguments passed to wgrib2.

    Raises
    ------
    WgribError
        When `wgrib2` exits with non-zero status.

    Notes
    -----
    The files opened by `wgrib2` are not closed on exit.
    Use :py:func:`free_files` to close.

    Examples
    --------
    >>> try:
    ...     wgrib(*args)
    >>> except WgribError as e:
    ...     print("wgrib2 error: {!r}".format(e))
    >>> finally:
    ...     free_files(gribfile)
    """
    rc = _wgrib2.wgrib(args)
    # 8 means help (i.e. no arguments)
    if rc != 0 and rc != 8:
        raise _WgribError
    return None


@organs
def latlon2xy(sec3, grid_lon, grid_lat, lon, lat):
    """Computes grid coordinates.

    Parameters
    ----------
    sec3 : bytes
           Section 3 of GRIB2 message.
    grid_lon, grid_lat : array_like
          Longitudes and latitudes of grid points.
    lon, lat : array_like
          Longitudes and latitudes to compute x and y coordinates.

    Returns
    -------
    x, y : tuple
          x and y coordinates in grid units.

    Raises
    ------
    WgribError
        When the C function exits with non-zero status.
    """
    grid_lon = grid_lon.astype(np.float64)
    grid_lat = grid_lat.astype(np.float64)
    lon = np.atleast_1d(lon).astype(np.float64)
    lat = np.atleast_1d(lat).astype(np.float64)

    ret = _wgrib2.latlon2xy(sec3, grid_lon, grid_lat, lon, lat)
    if ret is None:
        raise _WgribError
    return ret


@organs
def latlon(sec3, npoints):
    """Computes latitudes and longitudes of grid points.

    Parameters
    ----------
    sec3 : bytes
           Section 3 of GRIB2 message.
    npoints : int
           Number of points in grid.

    Returns
    -------
    lon, lat : tuple
          Longitudes and latitudes of grid points.

    Raises
    ------
    WgribError
        When the C function exits with non-zero status.
    """
    ret = _wgrib2.latlon(sec3, npoints)
    if ret is None:
        raise _WgribError
    return ret

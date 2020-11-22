from typing import Any, Optional, Sequence, Union

import numpy as np

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any
from xarray.backends.locks import SerializableLock

from . import _wgrib2, WgribError  # type: ignore

# iplib is double precision
DTYPE = np.dtype("float64")
# Interpolation type codes
IP_Types = dict(bilinear=0, bicubic=1, neighbor=2, neighbour=2, budget=3, spectral=4)
# Interpolation options array size
IPOPT_SIZE = 20

IP_LOCK = SerializableLock()


def gdswzd(
    gdtnum: int,
    gdtmpl: ArrayLike,
    opt: int,
    xpts: ArrayLike,
    ypts: ArrayLike,
    lon: ArrayLike,
    lat: ArrayLike,
):
    crot = np.empty_like(xpts)
    srot = np.empty_like(xpts)
    xlon = np.empty_like(xpts)
    xlat = np.empty_like(xpts)
    ylon = np.empty_like(xpts)
    ylat = np.empty_like(xpts)
    area = np.empty_like(xpts)
    nret = _wgrib2.gdswiz(
        gdtnum,
        gdtmpl,
        opt,
        xpts.ravel(),
        ypts.ravel(),
        lon.ravel(),
        lat.ravel(),
        crot.ravel(),
        srot.ravel(),
        xlon.ravel(),
        xlat.ravel(),
        ylon.ravel(),
        ylat.ravel(),
        area.ravel(),
    )
    if nret < 0:
        raise WgribError("Unrecognised projection")
    ret = dict(crot=crot, srot=srot, area=area)
    if opt >= 0:
        ret["lon"] = lon
        ret["lat"] = lat
    if opt <= 0:
        ret["xpts"] = xpts - 1.0
        ret["ypts"] = ypts - 1.0
    return ret


def earth2grid_points(grid, point):
    """Computes grid coordinates of selected Earth coordinates.

    Parameters
    ----------
    grid: Grid
        Grid geometry instance.
    point : Point
        Point geometry instance.

    Returns
    -------
    dict
        Calculated coordinates: a dictionary with keys
        {'crot', 'srot', 'area', 'xpts', 'ypts'}
        where:

        - crot, srot : Cosine and sines of clockwise vector rotation.
        - area : Area weights in `m^2`. Proportional to the square of the map factor \
            in the case of conformal projections.
        - xpts, ypts : Grid point coordinates`.
    """
    lon = point.coords["longitude"].data.astype(DTYPE)
    lat = point.coords["latitude"].data.astype(DTYPE)
    xpts = np.empty(point.shape, dtype=DTYPE)
    ypts = np.empty(point.shape, dtype=DTYPE)
    gdtmpl = np.asarray(grid.gdtmpl, dtype=np.int32)
    with IP_LOCK:
        return gdswzd(grid.gdtnum, gdtmpl, -1, xpts, ypts, lon, lat)


def grid2earth_grid(grid):
    """computes Earth coordinates of all the grid points.

    Parameters
    ----------
    grid: Grid
        Grid definition instance.

    Returns
    -------
    dict
        Calculated coordinates: a dictionary with keys
        {'crot', 'srot', 'area', 'lat', 'lon', 'xpts', 'ypts'}
        where:

        - crot, srot : Cosine and sines of clockwise vector rotation.
        - area : Area weights in `m^2`. Proportional to the square of the map factor \
            in the case of conformal projections.
        - lat, lon : Latitudes and longitudes.
        - xpts, ypts : Grid point coordinates.
    """
    xpts = np.empty(grid.shape, dtype=DTYPE)
    ypts = np.empty(grid.shape, dtype=DTYPE)
    lon = np.empty(grid.shape, dtype=DTYPE)
    lat = np.empty(grid.shape, dtype=DTYPE)
    gdtmpl = np.asarray(grid.gdtmpl, dtype=np.int32)
    with IP_LOCK:
        return gdswzd(grid.gdtnum, gdtmpl, 0, xpts, ypts, lon, lat)


def grid2earth_points(grid, xpts, ypts):
    """Computes Earth coordinates of selected grid points.

    Parameters
    ----------
    grid : Grid
        Grid geometry instance.

    xpts : array_like
        Grid X point coordinates.
    ypts : array_like
        Grid Y point coordinates.

    Returns
    -------
    dict
        Calculated coordinates: a dictionary with keys
        {'crot', 'srot', 'area', 'lat', 'lon'}
        where:

        - crot, srot : Cosine and sines of clockwise vector rotation.
        - area : Area weights in `m^2`. Proportional to the square of the map factor \
            in the case of conformal projections.
        - lat, lon : Latitudes and longitudes.
    """
    xpts = np.ascontiguousarray(xpts, dtype=DTYPE) + 1.0  # fortran counts from 1
    shape = xpts.shape
    ypts = np.ascontiguousarray(ypts, dtype=DTYPE) + 1.0
    if shape != ypts.shape:
        raise ValueError(
            "shapes of xpts {!r} and ypts {!r} must be equal".format(shape, ypts.shape)
        )
    lon = np.empty(shape, dtype=DTYPE)
    lat = np.empty(shape, dtype=DTYPE)
    gdtmpl = np.asarray(grid.gdtmpl, dtype=np.int32)
    with IP_LOCK:
        return gdswzd(grid.gdtnum, gdtmpl, 1, xpts, ypts, lon, lat)


def _get_ipopt(ip: int, ipopt: Any) -> ArrayLike:
    """Sets ipopt array."""
    if ipopt is None:
        ipopt = {}
    ipopt_array = np.zeros((IPOPT_SIZE,), dtype=np.int32)
    ipopt_array[:2] = -1
    if ip in (1, 4):  # bicubic or spectral, wgrib2 defaults
        ipopt_array[0] = 0
    return ipopt_array


def ipolates(
    grid: ArrayLike,
    iptype: str,
    gdtnum_in: int,
    gdtmpl_in: Sequence[int],
    gdtnum_out: int,
    gdtmpl_out: Union[Sequence[int], ArrayLike, None] = None,
    rlon: Union[Sequence[float], ArrayLike, None] = None,
    rlat: Union[Sequence[float], ArrayLike, None] = None,
    ipopt: Optional[Any] = None,
):
    """Interface to `iplib` subroutine `ipolates`."""
    ip = IP_Types.get(iptype)
    if ip is None:
        raise ValueError("Invalid interpolation type")
    ipopt_array = _get_ipopt(ip, ipopt)
    gdtmpl_in = np.asarray(gdtmpl_in, dtype=np.int32)
    nx_in, ny_in = gdtmpl_in[7:9]
    if grid.shape[-2:] != (ny_in, nx_in):
        raise WgribError(
            "grid description template does not match grid: "
            "{!r} and {!r}".format((ny_in, nx_in), tuple(grid.shape[-2:]))
        )
    m_in = nx_in * ny_in
    km = int(grid.size // m_in)
    if gdtnum_out >= 0:
        if gdtmpl_out is None:
            raise ValueError("gdtmpl_out must be specified")
        gdtmpl_out = np.asarray(gdtmpl_out, dtype=np.int32)
        nx_out, ny_out = gdtmpl_out[7:9]
        m_out = nx_out * ny_out
        rlat = np.zeros((m_out,), dtype=DTYPE)
        rlon = np.zeros((m_out,), dtype=DTYPE)
        shape_out = tuple(list(grid.shape[:-2]) + [ny_out, nx_out])
    else:
        if rlat is None or rlon is None:
            raise WgribError("Latitude and longitude must be specified")
        rlat = np.ascontiguousarray(rlat, dtype=DTYPE).ravel()
        rlon = np.ascontiguousarray(rlon, dtype=DTYPE).ravel()
        if rlon.size != rlat.size:
            raise WgribError("Latitude/longitude sizes differ")
        if iptype == "budget":
            gdtmpl_out = np.asarray(gdtmpl_out, dtype=np.int32)
        else:
            gdtmpl_out = np.array([0], np.int32)
        m_out = rlon.size
        shape_out = tuple(list(grid.shape[:-2]) + [m_out])
    g_in = np.ascontiguousarray(grid, dtype=DTYPE).ravel()
    l_in = np.ones((g_in.size,), dtype=np.uint8)
    l_in[np.isnan(g_in)] = 0
    if np.all(l_in):
        ib_in = np.zeros((km,), dtype=np.int32)
    else:
        ib_in = np.ones((km,), dtype=np.int32)
    ib_out = np.empty((km,), dtype=np.int32)
    g_out = np.empty((km * m_out,), dtype=DTYPE)
    l_out = np.empty((g_out.size,), dtype=np.uint8)
    iret, nout = _wgrib2.ipolates(
        ip,
        ipopt_array,
        gdtnum_in,
        gdtmpl_in,
        gdtnum_out,
        gdtmpl_out,
        m_in,
        m_out,
        km,
        ib_in,
        l_in,
        g_in,
        rlat,
        rlon,
        ib_out,
        l_out,
        g_out,
    )
    if iret != 0:
        msg = {
            1: "Unrecognised interpolation method",
            2: "Unrecognised input grid or no grid overlap",
            3: "Unrecognised output grid",
        }.get(iret, "Interpolation failed, reason: {:d}".format(iret))
        raise WgribError(msg)
    if not np.all(ib_out == 0):
        g_out[l_out & 1 == 0] = np.nan
    if gdtnum_out < 0:
        return dict(data=g_out.reshape(shape_out))
    return dict(
        data=g_out.reshape(shape_out),
        lat=rlat.reshape(ny_out, nx_out),
        lon=rlon.reshape(ny_out, nx_out),
        nout=nout,
    )


def ips_grid(data, iptype, grid_in, grid_out, ipopt=None):
    """Interface to NCEP subroutine `ipolates`.

    This function interpolates scalar fields from any grid to a grid.
    Only horizontal interpolation is performed.

    Parameters
    ----------
    data : array_like
        Input grid.
    iptype : {'bilinear', 'bicubic', 'neighbour', 'budget', 'spectral'}
        Interpolation method.
    grid_in : Grid
        Input grid geometry instance. One of
        {GridLatLon, GridRotLatLon, GridMercator, GridPolarStereo, \
         GridLambertConformal, GridGaussian}
    grid_out : Grid
        Output grid geometry instance.
    ipopt : array_like
        Interpolation options.

    Returns
    -------
    dict
        A dictionary with keys {'data', 'lat', 'lon', 'nout'}. Values are
        interpolated grid, latitudes/longitudes and number of output grid
        points.
    """
    with IP_LOCK:
        return ipolates(
            data,
            iptype,
            grid_in.gdtnum,
            grid_in.gdtmpl,
            grid_out.gdtnum,
            grid_out.gdtmpl,
            ipopt,
        )


def ips_points(data, iptype, grid, point, ipopt=None):
    """Interface to NCEP subroutine `ipolates`.

    This function interpolates scalar fields from any grid to a set of points
    given by their latitudes and longitudes.
    Only horizontal interpolation is performed.

    Parameters
    ----------
    data : array_like
        Input grid.
    iptype : {'bilinear', 'bicubic', 'neighbour', 'budget'}
        Interpolation method.
    grid : Grid
        Input grid geometry instance. One of
        {GridLatLon, GridRotLatLon, GridMercator, GridPolarStereo, \
         GridDefLambertConformal, GridDefGaussian}
    point : Point
        Output Point geometry instance.
    ipopt : array_like
        Interpolation options.

    Returns
    -------
    dict
        A dictionary with single key {"data"} (for consistency with ips_grid).
        Values are interpolated grid at location specified by 'point' argument.
    """
    lon = point.coords["longitude"].data.astype(DTYPE)
    lat = point.coords["latitude"].data.astype(DTYPE)
    with IP_LOCK:
        if iptype == "budget":
            # FIXME: define smaller grid containing all points
            return ipolates(
                data,
                iptype,
                grid.gdtnum,
                grid.gdtmpl,
                grid.gdtnum - 255,
                grid.gdtmpl,
                rlon=lon,
                rlat=lat,
                ipopt=ipopt,
            )
        else:
            return ipolates(
                data,
                iptype,
                grid.gdtnum,
                grid.gdtmpl,
                -1,
                rlon=lon,
                rlat=lat,
                ipopt=ipopt,
            )


def ipolatev(
    udata: ArrayLike,
    vdata: ArrayLike,
    iptype: str,
    gdtnum_in: int,
    gdtmpl_in: Sequence[int],
    gdtnum_out: int,
    gdtmpl_out: Union[Sequence[int], ArrayLike, None] = None,
    rlon: Union[Sequence[float], ArrayLike, None] = None,
    rlat: Union[Sequence[float], ArrayLike, None] = None,
    ipopt: Optional[Sequence[int]] = None,
):
    """Interface to NCEP subroutine `ipolatev`."""
    ip = IP_Types.get(iptype)
    if ip is None:
        raise WgribError("Invalid interpolation type")
    ipopt_array = _get_ipopt(ip, ipopt)
    gdtmpl_in = np.asarray(gdtmpl_in, dtype=np.int32)
    nx_in, ny_in = gdtmpl_in[7:9]
    if udata.shape != vdata.shape:
        raise ValueError(
            "U and V grids differ: {!r} and {!r}".format(udata.shape, vdata.shape)
        )
    if udata.shape[-2:] != (ny_in, nx_in):
        raise ValueError("grid description template does not match grid")
    m_in = nx_in * ny_in
    km = int(udata.size // m_in)
    if gdtnum_out >= 0:
        if gdtmpl_out is None:
            raise ValueError("gdtmpl_out must be specified")
        gdtmpl_out = np.asarray(gdtmpl_out, dtype=np.int32)
        nx_out, ny_out = gdtmpl_out[7:9]
        m_out = nx_out * ny_out
        rlat = np.empty((ny_out, nx_out), dtype=DTYPE).ravel()
        rlon = np.empty((ny_out, nx_out), dtype=DTYPE).ravel()
        shape_out = tuple(list(udata.shape[:-2]) + [ny_out, nx_out])
    else:
        if rlat is None or rlon is None:
            raise ValueError("latitudes and longitudes bust be specified")
        rlat = np.asarray(rlat, dtype=DTYPE).ravel()
        rlon = np.asarray(rlon, dtype=DTYPE).ravel()
        if rlon.size != rlat.size:
            raise ValueError(
                "Latitude/longitude sizes differ: {:d} and {:d}".format(
                    rlon.size, rlat.size
                )
            )
        gdtmpl_out = np.array([0], np.int32)
        m_out = rlon.size
        shape_out = tuple(list(udata.shape[:-2]) + [m_out])
    ug_in = np.ascontiguousarray(udata, dtype=DTYPE).ravel()
    vg_in = np.ascontiguousarray(vdata, dtype=DTYPE).ravel()
    l_in = np.ones((ug_in.size,), dtype=np.uint8)
    l_in[np.isnan(ug_in) | np.isnan(vg_in)] = 0
    if np.all(l_in):
        ib_in = np.zeros((km,), dtype=np.int32)
    else:
        ib_in = np.ones((km,), dtype=np.int32)
    ug_out = np.empty((km * m_out,), dtype=DTYPE)
    vg_out = np.empty((km * m_out,), dtype=DTYPE)
    crot = np.empty((m_out,), dtype=DTYPE)
    srot = np.empty((m_out,), dtype=DTYPE)
    ib_out = np.empty((km,), dtype=np.int32)
    l_out = np.empty((km * m_out,), dtype=np.uint8)
    iret, nout = _wgrib2.ipolatev(
        ip,
        ipopt_array,
        gdtnum_in,
        gdtmpl_in,
        gdtnum_out,
        gdtmpl_out,
        m_in,
        m_out,
        km,
        ib_in,
        l_in,
        ug_in,
        vg_in,
        rlat,
        rlon,
        crot,
        srot,
        ib_out,
        l_out,
        ug_out,
        vg_out,
    )
    if iret != 0:
        msg = {
            1: "Unrecognised interpolation method.",
            2: "Unrecognised input grid or no grid overlap.",
            3: "Unrecognised output grid.",
        }.get(iret, "Interpolation failed, error: {:d}.".format(iret))
        raise WgribError(msg)
    if not np.all(ib_out == 0):
        m = l_out & 1 == 0
        ug_out[m] = np.nan
        vg_out[m] = np.nan
    if gdtnum_out < 0:
        return dict(
            udata=ug_out.reshape(shape_out),
            vdata=vg_out.reshape(shape_out),
            crot=crot,
            srot=srot,
        )
    return dict(
        udata=ug_out.reshape(shape_out),
        vdata=vg_out.reshape(shape_out),
        lat=rlat.reshape(ny_out, nx_out),
        lon=rlon.reshape(ny_out, nx_out),
        crot=crot.reshape(ny_out, nx_out),
        srot=srot.reshape(ny_out, nx_out),
        nout=nout,
    )


def ipv_grid(udata, vdata, iptype, grid_in, grid_out, ipopt=None):
    """Interface to NCEP subroutine `ipolatev`.

    This function interpolates vector fields from any grid to a grid.
    Only horizontal interpolation is performed.

    Parameters
    ----------
    udata : array_like
        U-component of input grid.
    vdata : array_like
        V-component of input grid.
    iptype : {'bilinear', 'bicubic', 'neighbour', 'budget', 'spectral'}
        Interpolation method.
    grid_in : Grid
        Input grid grid geometry instance. One of
        {GridLatLon, GridRotLatLon, GridMercator, GridPolarStereo, \
         GridLambertConformal, GridGaussian}
    grid_out : Grid
        Output grid grid geometry instance.
    ipopt : array_like
        Interpolation options. Currently not implemented.

    Returns
    -------
    dict
        A dictionary with keys {'udata', 'vdata', 'lat', 'lon', 'nout'}.
        Values are interpolated grids, latitudes/longitudes and number
        of output grid points.
    """
    with IP_LOCK:
        return ipolatev(
            udata,
            vdata,
            iptype,
            grid_in.gdtnum,
            grid_in.gdtmpl,
            grid_out.gdtnum,
            grid_out.gdtmpl,
            ipopt,
        )


def ipv_points(udata, vdata, iptype, grid, point, windNS=False, ipopt=None):
    """Interface to NCEP subroutine `ipolatev`.

    This function interpolates vector fields from any grid to a set of points
    given by their latitudes and longitudes.
    Only horizontal interpolation is performed.

    Parameters
    ----------
    udata : array_like
        U-component of input grid.
    vdata : array_like
        V-component of input grid.
    iptype : {'bilinear', 'bicubic', 'neighbour', 'budget'}
        Interpolation method.
    grid : Grid
        Input grid geometry instance. One of
        {GridLatLon, GridRotLatLon, GridMercator, GridPolarStereo, \
         GridLambertConformal, GridGaussian}
    point : Point,
        Destination geometry instance.
    windNS : bool
        Force winds to be in Earth coordinates. Default is False.
    ipopt : array_like
        Interpolation options.

    Returns
    -------
    dict
        A dictionary with keys {'udata', 'vdata'}.
        Values are interpolated grids at locations given by 'point' argument.
    """
    lon = point.coords["longitude"].data.astype(DTYPE)
    lat = point.coords["latitude"].data.astype(DTYPE)
    with IP_LOCK:
        if iptype == "budget":
            # FIXME: define smaller grid containing all points
            ret = ipolatev(
                udata,
                vdata,
                iptype,
                grid.gdtnum,
                grid.gdtmpl,
                grid.gdtnum - 255,
                grid.gdtmpl,
                rlon=lon,
                rlat=lat,
                ipopt=ipopt,
            )
        else:
            ret = ipolatev(
                udata,
                vdata,
                iptype,
                grid.gdtnum,
                grid.gdtmpl,
                -1,
                rlon=lon,
                rlat=lat,
                ipopt=ipopt,
            )
    # FIXME: should be grid?
    if windNS and grid.params["GRIB_winds"] == "grid":
        return {
            "udata": ret["crot"] * ret["udata"] - ret["srot"] * ret["vdata"],
            "vdata": ret["srot"] * ret["udata"] + ret["crot"] * ret["vdata"],
        }
    return {"udata": ret["udata"], "vdata": ret["vdata"]}

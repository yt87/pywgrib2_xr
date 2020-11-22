from typing import Any, Tuple, Union

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any
import dask.array as da
import xarray as xr
from xarray.core.pycompat import dask_array_type

from .ip import (
    grid2earth_grid,
    ips_points,
    ipv_points,
    ips_grid,
    ipv_grid,
)
from .grids import (
    #    Grid,
    #    Point,
    GridLatLon,
    GridRotLatLon,
    GridMercator,
    GridPolarStereo,
    GridLambertConformal,
    GridGaussian,
    GridSpaceView,
    grid_fromgds,
)

# u -> v mappings for vector variables
WIND = {
    "UGRD": "VGRD",
    "VUCSH": "VVCSH",
    "UFLX": "VFLX",
    "UGUST": "VGUST",
    "USTM": "VSTM",
    "VDFUA": "VDFVA",
    "MAXUW": "MAXVW",
    "UOGRD": "VOGRD",
    "UICE": "VICE",
    "U-GWD": "V-GWD",
    "USSD": "VSSD",
}

GEO_COORDS = set(
    [
        "x",
        "y",
        "latitude",
        "longitude",
        "point",
        GridLatLon.cfname,
        GridRotLatLon.cfname,
        GridMercator.cfname,
        GridPolarStereo.cfname,
        GridLambertConformal.cfname,
        GridGaussian.cfname,
        GridSpaceView.cfname,
    ]
)


def get_v_component(uname: str, name: str) -> Union[str, None]:
    vname = WIND.get(uname)
    if not vname:
        return None if uname in WIND.values() else name
    return name.replace(uname, vname)


def ip2pts_scalar(var: xr.DataArray, npoints: int, **kwargs: Any) -> ArrayLike:
    def _ip(u):
        u2 = ips_points(u, **kwargs)
        return u2["data"]

    if isinstance(var.data, dask_array_type):
        ip = da.gufunc(
            _ip,
            signature="(m,n)->(p)",
            axes=[(-2, -1), (-1)],
            output_dtypes=(var.dtype,),
            output_sizes={"p": npoints},
            vectorize=True,
        )
    else:
        ip = _ip

    return ip(var.data)


def ip2pts_vector(
    u_var: xr.DataArray, v_var: xr.DataArray, npoints: int, **kwargs: Any
) -> Tuple[ArrayLike, ArrayLike]:
    def _ip(u, v):
        d = ipv_points(u, v, windNS=True, **kwargs)
        return d["udata"], d["vdata"]

    if isinstance(u_var.data, dask_array_type):
        ip = da.gufunc(
            _ip,
            signature="(m,n),(m,n)->(p),(p)",
            axes=[(-2, -1), (-2, -1), (-1,), (-1,)],
            output_dtypes=(u_var.dtype, v_var.dtype),
            output_sizes={"p": npoints},
            vectorize=True,
        )
    else:
        ip = _ip

    return ip(u_var.data, v_var.data)


def ip2grid_scalar(var: xr.DataArray, **kwargs: Any) -> ArrayLike:
    def _ip(u):
        u2 = ips_grid(u, **kwargs)
        return u2["data"]

    if isinstance(var.data, dask_array_type):
        i, j = kwargs["grid_out"].gdtmpl[7:9]
        ip = da.gufunc(
            _ip,
            signature="(m,n)->(j,i)",
            axes=[(-2, -1), (-2, -1)],
            output_dtypes=(var.dtype,),
            output_sizes={"i": i, "j": j},
            vectorize=True,
        )
    else:
        ip = _ip

    return ip(var.data)


def ip2grid_vector(
    u_var: xr.DataArray, v_var: xr.DataArray, **kwargs: Any
) -> Tuple[ArrayLike, ArrayLike]:
    def _ip(u, v):
        d = ipv_grid(u, v, **kwargs)
        return d["udata"], d["vdata"]

    if isinstance(u_var.data, dask_array_type):
        i, j = kwargs["grid_out"].gdtmpl[7:9]
        ip = da.gufunc(
            _ip,
            signature="(m,n),(m,n)->(j,i),(j,i)",
            axes=[(-2, -1), (-2, -1), (-2, -1), (-2, -1)],
            output_dtypes=(u_var.dtype, v_var.dtype),
            output_sizes={"i": i, "j": j},
            vectorize=True,
        )
    else:
        ip = _ip

    return ip(u_var.data, v_var.data)


@xr.register_dataset_accessor("wgrib2")
class Wgrib2DatasetAccessor:
    """Provides custom attributes and methods on xarray Dataset.

    Do not instantiate this class directly, use accessor name '.wgrib2' to call
    its method, for example:

        >>> ds.wgrib2.grid()

    """

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    # @property
    def get_grid(self):
        """Returns GRIB2 grid definition as dictionary."""
        proj = self._obj.attrs["Projection"]
        attrs = self._obj.coords[proj].attrs
        return grid_fromgds(attrs["GRIB_gdtnum"], attrs["GRIB_gdtmpl"])

    def location(self, points, iptype="neighbour"):
        """Remaps all variables to point locations.

        Parameters
        ----------
        points : Point
            Point geometry instance.
        iptype : dict or str: {'bilinear', 'bicubic', 'neighbour'}
            Interpolation method. Default is 'neighbour'.
            Dictionary allows interpolation type specific to variable.

            Example: ``iptype = {'CEIL': 'neighbour', 'default': 'bilinear'}``.

        Returns
        -------
        xarray.Dataset
            New dataset.
        """
        if isinstance(iptype, dict) and "default" not in iptype:
            iptype["default"] = "neighbour"
        cfname = points.cfname
        coords = {cfname: ((), 0, points.attrs)}
        coords.update(points.coords)
        # Copy remaining coords
        for name in set(self._obj.coords.keys()) - GEO_COORDS:
            var = self._obj.coords[name]
            coords[name] = (var.dims, var.data, var.attrs)

        grid = self.get_grid()
        data_vars = {}
        for name, var in self._obj.data_vars.items():
            dims = var.dims[:-2] + points.dims
            short_name = var.attrs["short_name"]
            if isinstance(iptype, dict):
                ipt = iptype.get(name, iptype["default"])
            else:
                ipt = iptype
            ip_kwargs = dict(iptype=ipt, grid=grid, point=points)
            v_name = get_v_component(short_name, name)
            if v_name == name:
                # scalar
                data = ip2pts_scalar(var, points.shape[0], **ip_kwargs)
                attrs = {**var.attrs, **{"grid_mapping": cfname}}
                data_vars[name] = (dims, data, attrs)
            elif v_name:
                # u-component
                # u_name == name, u_var == var
                v_var = self._obj[v_name]
                u_data, v_data = ip2pts_vector(var, v_var, points.shape[0], **ip_kwargs)
                attrs = {**var.attrs, **{"grid_mapping": cfname}}
                data_vars[name] = (dims, u_data, attrs)
                attrs = {**var.attrs, **{"grid_mapping": cfname}}
                data_vars[v_name] = (dims, v_data, attrs)
            # else:
            # v-component, skip

        attrs = self._obj.attrs.copy()
        attrs["Projection"] = cfname
        return xr.Dataset(data_vars, coords, attrs)

    def grid(self, grid, iptype="neighbour"):
        """Remaps all variables to points specified by `longitude` and `latitude`.

        Parameters
        ----------
        grid : Grid
            Target grid geometry. Projection can be one of
            {LatLon, RotLatLon, Mercator, PolarStereo, LambertConformal, Gaussian}
            To create 'grid' use factory method `gd_fromstring` or `gd_fromdict`.
        iptype : dict or str: {'bilinear', 'bicubic', 'neighbour', 'budget', 'spectral'}
            Interpolation method. Default is 'neighbour'.
            Dictionary allows interpolation type specific to variable.

            Example: ``iptype = {'APCP': 'budget', 'default': 'bilinear'}``.

        Returns
        -------
        xarray.Dataset
            New dataset.
        """
        if isinstance(iptype, dict) and "default" not in iptype:
            iptype["default"] = "neighbour"
        src_grid = self.get_grid()
        if grid == src_grid:
            return self._obj.copy()
        cfname = grid.cfname
        # Set geographic coordinates
        coords = {cfname: ((), 0, grid.attrs)}
        coords.update(grid.coords)
        # Copy remaining coords
        for name in set(self._obj.coords.keys()) - GEO_COORDS:
            var = self._obj.coords[name]
            coords[name] = (var.dims, var.data, var.attrs)

        data_vars = {}
        for name, var in self._obj.data_vars.items():
            dims = var.dims[:-2] + grid.dims
            short_name = var.attrs["short_name"]
            if isinstance(iptype, dict):
                ipt = iptype.get(name, iptype["default"])
            else:
                ipt = iptype
            ip_kwargs = dict(iptype=ipt, grid_in=src_grid, grid_out=grid)
            v_name = get_v_component(short_name, name)
            if v_name == name:
                data = ip2grid_scalar(var, **ip_kwargs)
                attrs = {"grid_mapping": cfname, **var.attrs}
                data_vars[name] = (dims, data, attrs)
            elif v_name:
                # u_name == name, u_var == var
                v_var = self._obj[v_name]
                u_data, v_data = ip2grid_vector(var, v_var, **ip_kwargs)
                attrs = {**var.attrs, **{"grid_mapping": cfname}}
                data_vars[name] = (dims, u_data, attrs)
                attrs = {**var.attrs, **{"grid_mapping": cfname}}
                data_vars[v_name] = (dims, v_data, attrs)

        attrs = self._obj.attrs.copy()
        attrs["Projection"] = cfname

        return xr.Dataset(data_vars, coords, attrs)

    def winds(self, winds, inplace=False):
        """Changes vector coordinates to grid/Earth direction.

        Parameters
        ----------
        winds : str
            Vector orientation. One of {'grid', 'earth'}.

        Returns
        -------
        xarray.Dataset
            New dataset with vectors in new coordinates.
        """
        ds = self._obj if inplace else self._obj.copy()
        grid = self.get_grid()
        if grid.params["GRIB_winds"] == winds:
            # Nothing to do
            return ds

        ret = grid2earth_grid(grid)
        crot = ret["crot"]
        srot = ret["srot"]
        for name, var in self._obj.data_vars.items():
            shortname = var.attrs.get("short_name")
            if not shortname:
                continue
            v_name = get_v_component(shortname, name)
            if not v_name or v_name == name:
                continue
            v_var = self._obj[v_name]
            urot = crot * var.values + srot * v_var.values
            vrot = -srot * var.values + crot * v_var.values
            ds[name] = (var.dims, urot.astype(var.dtype, copy=False), var.attrs)
            ds[v_name] = (v_var.dims, vrot.astype(v_var.dtype, copy=False), v_var.attrs)
        # Update gdtmpl
        grid.set_winds(winds)
        proj = self._obj.attrs["Projection"]
        ds.coords[proj].attrs = grid.params

        return ds

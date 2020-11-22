# from __future__ import annotations  # Python-3.7+

from abc import ABC, abstractmethod
import enum
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np  # type: ignore

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any

from . import _Variable
from .wgrib2 import latlon, latlon2xy


class GDTNum(enum.IntEnum):
    """Grid Definition Template Number."""

    UNDEFINED = -1
    "Not set"
    LATLON = 0
    "Latitude/Longitude"
    ROT_LATLON = 1
    "Rotated latitude/longitude"
    MERCATOR = 10
    "Mercator"
    POLAR_STEREO = 20
    "Polar stereographic"
    LAMBERT_CONFORMAL = 30
    "Lambert conformal"
    GAUSSIAN = 40
    "Global Gaussian"
    SPACE_VIEW = 90
    "Space View"


def _norm_lon(a: float) -> float:
    while a > 360:
        a -= 360
    while a < 0:
        a += 360
    return a


class Point:
    """Unstructured list of points."""

    cfname = "points"

    def __init__(
        self,
        longitude: Sequence[float],
        latitude: Sequence[float],
        coord: Optional[Tuple[str, Sequence[Any], Dict[str, Any]]] = None,
    ):
        npts = len(longitude)
        assert len(latitude) == npts
        if coord is None:
            coord = ("point", np.array(range(npts)), {"long_name": "point number"})
        else:
            coord = (coord[0], np.asarray(coord[1]), coord[2])
        assert len(coord[1]) == npts
        longitude = np.ascontiguousarray(longitude, dtype=np.float64)
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        latitude = np.ascontiguousarray(latitude, dtype=np.float64)
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._dims = (coord[0],)
        self._coords = {
            "longitude": _Variable(self._dims, longitude, lon_attrs),
            "latitude": _Variable(self._dims, latitude, lat_attrs),
            coord[0]: _Variable(self._dims, coord[1], coord[2]),
        }

    def __repr__(self) -> str:
        return repr({**self.crs, **self.coords})

    @property
    def attrs(self) -> Dict[str, Any]:
        return self.crs

    @property
    def crs(self) -> Dict[str, Any]:
        return {"mapping_name": self.cfname}

    @property
    def coords(self) -> Dict[str, _Variable]:
        return self._coords

    @property
    def dims(self) -> Tuple[str]:
        return self._dims

    @property
    def shape(self) -> Tuple[int]:
        return self._coords["longitude"].data.shape


class Grid(ABC):
    """2-dimensional rectangular grid.

    This is a base class, concrete subclasses are:

    * GridLatLon (0): Latitude/Longitude.
    * GridRotLatLon (1): Rotated Latitude/Longitude.
    * GridMercator (10): Mercator.
    * GridPolarStereo (20): Polar Stereographic Projection (can be North or South).
    * GridLambertConformal (30): Lambert Conformal, can be Secant, Tangent, Conical, or Bipolar
    * GridGaussian (40): Gaussian Latitude/Longitude.
    * GridSpaceView (90): Space View.

    These classes should not be instantiated directly, use factory methods
    :py:func:`grid_fromgdt`, :py:func:`grid_fromstring` and :py:func:`grid_fromdict`.
    """

    cfname = ""
    "Class name"
    gdtnum = GDTNum.UNDEFINED
    "Grid definition template number"
    _sec3_head_fmt = ">IBBIBBHBBIBIBI"
    _sec3_param_fmt = ""  # specific to projection
    _sec3_len = 0
    _respos = 0
    _scanpos = 0

    def __init__(self, gdtmpl: List[int]) -> None:
        npts = gdtmpl[7] * gdtmpl[8]
        sec3 = self._mksec3(gdtmpl)
        longitude, latitude = latlon(sec3, npts)
        self.gdtmpl = gdtmpl.copy()
        wesn_gdtmpl = self.to_wesn(longitude, latitude)
        self._params: Dict[str, Any] = {
            "GRIB_gdtnum": self.gdtnum,
            "GRIB_gdtmpl": wesn_gdtmpl,
        }
        self.decode_params()
        self.decode_globe()
        self.set_coords(longitude, latitude)

    def _mksec3(self, gdtmpl: List[int]) -> bytes:
        fmt = self._sec3_head_fmt + self._sec3_param_fmt
        seclen = self._sec3_len
        npts = gdtmpl[7] * gdtmpl[8]
        gds = np.concatenate([[3, 0, npts, 0, 0, self.gdtnum], gdtmpl])
        ugds = np.empty(gds.shape, dtype=np.uint32)
        for i, v in enumerate(gds):
            assert abs(v) <= 0x7FFFFFFF
            # -1 might be missing value
            ugds[i] = v if v > -1 else 0x80000000 - v
        return struct.pack(fmt, seclen, *ugds)

    def __repr__(self) -> str:
        return repr({**self.crs, **self.globe, **self.params, **self.coords})

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return (
                self.__class__.gdtnum == other.__class__.gdtnum
                and self.gdtmpl == other.gdtmpl
            )
        return False

    def decode_globe(self):
        code, sradius, vradius, smajor, vmajor, sminor, vminor = self.gdtmpl[:7]
        if code == 0:
            self._globe = {"shape": "sphere", "earth_radius": 6367470.0}
        elif code == 1:
            radius = vradius / 10 ** sradius
            self._globe = {"shape": "sphere", "earth_radius": radius}
        elif code == 2:
            self._globe = {
                "shape": "ellipsoid",
                "semi_major_axis": 6378160.0,
                "semi_minor_axis": 6356775.0,
            }
        elif code in (3, 7):
            i = 3 if code == 3 else 0  # return value in [m]
            major = vmajor / 10 ** (smajor - i)
            minor = vminor / 10 ** (sminor - i)
            self._globe = {
                "shape": "ellipsoid",
                "semi_major_axis": major,
                "semi_minor_axis": minor,
            }
        elif code == 4:
            self._globe = {
                "shape": "GRS80",
                "semi_major_axis": 6378137.0,
                "semi_minor_axis": 6356752.140,
            }
        elif code == 5:
            self._globe = {
                "shape": "WGS84",
                "semi_major_axis": 6378137.0,
                "semi_minor_axis": 6356752.245,
            }
        elif code == 6:
            self._globe = {"shape": "sphere", "earth_radius": 6371229.0}
        elif code == 8:
            self._globe = {"shape": "sphere", "earth_radius": 6371200.0}
        elif code == 9:
            self._globe = {
                "shape": "Airy",
                "semi_major_axis": 6377563.396,
                "semi_minor_axis": 6356256.909,
            }
        self._globe["code"] = code

    @staticmethod
    def encode_globe(code: int, **kwargs) -> List[int]:
        scale = 0xFF
        vradius = vmajor = vminor = -1  # 0xFFFFFFFF
        if code == 1:
            scale = 1
            vradius = int(kwargs["earth_radius"] * 10 ** scale)
        elif code in (3, 7):
            scale = 4 if code == 3 else 1
            vmajor = int(kwargs["semi_major_axis"] * 10 ** scale)
            vminor = int(kwargs["semi_minor_axis"] * 10 ** scale)
        return [code, scale, vradius, scale, vmajor, scale, vminor]

    @abstractmethod
    def decode_params(self) -> None:
        pass

    @staticmethod
    @abstractmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        pass

    @staticmethod
    @abstractmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        pass

    @abstractmethod
    def set_coords(self, longitude: ArrayLike, latitude: ArrayLike) -> None:
        self._coords: Dict[str, Any] = {}

    @property
    def attrs(self) -> Dict[str, Any]:
        return {**self.crs, **self.globe, **self.params}

    @property
    def coords(self) -> Dict[str, _Variable]:
        return self._coords

    @property
    @abstractmethod
    def crs(self) -> Dict[str, Any]:
        """Parameters for cartopy coordinate reference system."""
        pass

    @property
    @abstractmethod
    def dims(self) -> Tuple[str, str]:
        """Grid dimension names."""
        pass

    @property
    def globe(self) -> Dict[str, Any]:
        """Parameters for cartopy globe"""
        return self._globe

    @property
    def params(self) -> Dict[str, Any]:
        """GRIB parameters as dictionary"""
        return self._params

    @property
    def shape(self) -> Tuple[int, int]:
        """Grid shape."""
        nx, ny = self.gdtmpl[7:9]
        return ny, nx

    def set_winds(self, winds: str) -> None:
        """Sets vector orientation."""
        if winds in ("earth", "grid"):
            if winds == self._params["GRIB_winds"]:
                return
            if winds == "grid":
                self._params["GRIB_gdtmpl"][self._respos] |= 0x08
            else:
                self._params["GRIB_gdtmpl"][self._respos] &= 0xF7
            self._params["GRIB_winds"] = winds
        else:
            raise ValueError("wind orientation must be 'grid' or 'earth'")

    @classmethod
    def fromdict(
        cls,
        winds: Optional[str] = "earth",
        globe: Optional[Dict[str, Any]] = None,
        **params
    ) -> "Grid":
        """Creates Grid Definition class from keywords."""
        if globe is None:
            globe = {"code": 6}  # NCEP model default
        gdtmpl = cls.encode_globe(**globe)

        # make prefix GRIB_optional
        # Replace with method removeprefix in Python-3.9
        def _removeprefix(s, prefix):
            return s[len(prefix) :] if s.startswith(prefix) else s

        params = {_removeprefix(k, "GRIB_"): v for k, v in params.items()}
        gdtmpl.extend(cls.encode_params(winds=winds, **params))
        return cls(gdtmpl)

    @classmethod
    def fromstring(
        cls,
        strings: List[str],
        winds: Optional[str] = None,
        globe: Optional[Dict[str, Any]] = None,
    ) -> "Grid":
        """Creates Grid Definition class from wgrib2 style strings."""
        params = cls.strings2params(strings)
        return cls.fromdict(globe=globe, winds=winds, **params)


class GridLatLon(Grid):
    """Grid definition for latitude-longitude (also known as Plate Carree) projection."""

    cfname = "latitude_longitude"
    gdtnum = GDTNum.LATLON
    _sec3_param_fmt = "IIIIIIBIIIIB"
    _sec3_len = 72
    _respos = 19
    _scanpos = 18

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        Ni, Nj, ba, sba, La1, Lo1, res, La2, Lo2, Di, Dj, scan = gdtmpl[7:]
        scale = 1e-6 if ba == 0 else ba / sba
        self._params.update(
            {
                "GRIB_Npts": Ni * Nj,
                "GRIB_Ni": Ni,
                "GRIB_Nj": Nj,
                "GRIB_La1": La1 * scale,
                "GRIB_Lo1": Lo1 * scale,
                "GRIB_La2": La2 * scale,
                "GRIB_Lo2": Lo2 * scale,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Di": Di * scale,
                "GRIB_Dj": Dj * scale,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        ba = params.get("basic_angle", 0)
        sba = params.get("subdiv_basic_angle", -1)  # 0xFFFFFFFF)
        scale = 1e-6 if params.get("basic_angle", 0) == 0 else ba / sba
        La1 = int(params["La1"] / scale)
        Lo1 = int(params["Lo1"] / scale)
        # Override coordinates of the last point, if present, for consistency
        # FIXME: make it conditional, key on La2 or Dj, only one need to be present.
        params["La2"] = params["La1"] + (params["Nj"] - 1) * params["Dj"]
        params["Lo2"] = (params["Lo1"] + (params["Ni"] - 1) * params["Di"]) % 360
        La2 = int(params["La2"] / scale)
        Lo2 = int(params["Lo2"] / scale)
        Di = int(params["Di"] / scale)
        Dj = int(params["Dj"] / scale)
        Ni = params["Ni"]
        Nj = params["Nj"]
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        return [Ni, Nj, ba, sba, La1, Lo1, res, La2, Lo2, Di, Dj, scan]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        params = {}
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Ni"] = int(tok[1])
        params["Di"] = float(tok[2])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Nj"] = int(tok[1])
        params["Dj"] = float(tok[2])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        lon = longitude.reshape(self.shape)[0, :]
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
            "axis": "X",
        }
        lat = latitude.reshape(self.shape)[:, 0]
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
            "axis": "Y",
        }
        self._coords = {
            "longitude": _Variable(("longitude",), lon, lon_attrs),
            "latitude": _Variable(("latitude",), lat, lat_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            ba, sba = gdtmpl[9:11]
            scale = 1e-6 if ba == 0 else ba / sba
            gdtmpl[11] = int(latitude[0] / scale)
            gdtmpl[12] = int(longitude[0] / scale)
            gdtmpl[14] = int(latitude[-1] / scale)
            gdtmpl[15] = int(longitude[-1] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {"grid_mapping_name": self.cfname}

    @property
    def dims(self) -> Tuple[str, str]:
        return ("latitude", "longitude")


class GridRotLatLon(Grid):
    """Grid definition for rotated latitude-longitude projection."""

    cfname = "rotated_latitude_longitude"
    gdtnum = GDTNum.ROT_LATLON
    _sec3_param_fmt = "IIIIIIBIIIIBIII"
    _sec3_len = 84
    _respos = 13
    _scanpos = 18

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        (
            Ni,
            Nj,
            ba,
            sba,
            La1,
            Lo1,
            res,
            La2,
            Lo2,
            Di,
            Dj,
            scan,
            LaSP,
            LoSP,
            Rot,
        ) = gdtmpl[7:]
        scale = 1e-6 if ba == 0 else ba / sba
        self._params.update(
            {
                "GRIB_Npts": Ni * Nj,
                "GRIB_Ni": Ni,
                "GRIB_Nj": Nj,
                "GRIB_La1": La1 * scale,
                "GRIB_Lo1": Lo1 * scale,
                "GRIB_La2": La2 * scale,
                "GRIB_Lo2": Lo2 * scale,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Di": Di * scale,
                "GRIB_Dj": Dj * scale,
                "GRIB_LaSP": LaSP * scale,
                "GRIB_LoSP": LoSP * scale,
                "GRIB_Rot": Rot * scale,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        ba = params.get("basic_angle", 0)
        sba = params.get("subdiv_basic_angle", -1)  # 0xFFFFFFFF
        scale = 1e-6 if params.get("basic_angle", 0) == 0 else ba / sba
        La1 = int(params["La1"] / scale)
        Lo1 = int(params["Lo1"] / scale)
        # Override coordinates of the last point, if present, for consistency
        params["La2"] = params["La1"] + (params["Nj"] - 1) * params["Dj"]
        params["Lo2"] = (params["Lo1"] + (params["Ni"] - 1) * params["Di"]) % 360
        La2 = int(params["La2"] / scale)
        Lo2 = int(params["Lo2"] / scale)
        Di = int(params["Di"] / scale)
        Dj = int(params["Dj"] / scale)
        Ni = params["Ni"]
        Nj = params["Nj"]
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        LaSP = int(params["LaSP"] / scale)
        LoSP = int(params["LoSP"] / scale)
        Rot = int(params["Rot"] / scale)
        return [
            Ni,
            Nj,
            ba,
            sba,
            La1,
            Lo1,
            res,
            La2,
            Lo2,
            Di,
            Dj,
            scan,
            LaSP,
            LoSP,
            Rot,
        ]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        # rot-ll:sp_lon:sp_lat:sp_rot lon0:nlon:dlon lat0:nlat:dlat
        params = {}
        tok = strings[0].split(":")
        params["LoSP"] = float(tok[1])
        params["LaSP"] = float(tok[2])
        params["Rot"] = float(tok[3])
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Ni"] = int(tok[1])
        params["Di"] = float(tok[2])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Nj"] = int(tok[1])
        params["Dj"] = float(tok[2])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        x = np.linspace(
            self._params["GRIB_Lo1"],
            self._params["GRIB_Lo2"],
            self._params["GRIB_Ni"],
        )
        x_attrs = {
            "units": "degree",
            "standard_name": "projection_x_coordinate",
            "axis": "X",
        }
        y = np.linspace(
            self._params["GRIB_La1"],
            self._params["GRIB_La2"],
            self._params["GRIB_Nj"],
        )
        y_attrs = {
            "units": "degree",
            "standard_name": "projection_y_coordinate",
            "axis": "X",
        }
        lon = longitude.reshape(self.shape)
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        lat = latitude.reshape(self.shape)
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._coords = {
            "x": _Variable(("x",), x, x_attrs),
            "y": _Variable(("y",), y, y_attrs),
            "longitude": _Variable(self.dims, lon, lon_attrs),
            "latitude": _Variable(self.dims, lat, lat_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            ba, sba = gdtmpl[9:11]
            scale = 1e-6 if ba == 0 else ba / sba
            gdtmpl[11] = int(latitude[0] / scale)
            gdtmpl[12] = int(longitude[0] / scale)
            gdtmpl[14] = int(latitude[-1] / scale)
            gdtmpl[15] = int(longitude[-1] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {
            "grid_mapping_name": self.cfname,
            "pole_longitude": self.params["GRIB_LoSP"],
            "pole_latitude": self.params["GRIB_LaSP"],
            "central_rotated_longitude": self.params["GRIB_Rot"],
        }

    @property
    def dims(self) -> Tuple[str, str]:
        return ("y", "x")


class GridMercator(Grid):
    """Grid definition for Mercator projection."""

    cfname = "mercator"
    gdtnum = GDTNum.MERCATOR
    _sec3_param_fmt = "IIIIBIIIBIII"
    _sec3_len = 72
    _respos = 11
    _scanpos = 15

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        Ni, Nj, La1, Lo1, res, LaD, La2, Lo2, scan, orient, Di, Dj = gdtmpl[7:]
        assert orient == 0
        self._params.update(
            {
                "GRIB_Npts": Ni * Nj,
                "GRIB_Ni": Ni,
                "GRIB_Nj": Nj,
                "GRIB_La1": La1 * 1e-6,
                "GRIB_Lo1": Lo1 * 1e-6,
                "GRIB_La2": La2 * 1e-6,
                "GRIB_Lo2": Lo2 * 1e-6,
                "GRIB_LaD": LaD * 1e-6,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Di": Di * 1e-3,
                "GRIB_Dj": Dj * 1e-3,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        La1 = int(params["La1"] * 1e6)
        Lo1 = int(params["Lo1"] * 1e6)
        La2 = int(params["La2"] * 1e6)
        Lo2 = int(params["Lo2"] * 1e6)
        LaD = int(params["LaD"] * 1e6)
        Di = int(params["Di"] * 1e3)
        Dj = int(params["Dj"] * 1e3)
        Ni = params["Ni"]
        Nj = params["Nj"]
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        return [Ni, Nj, La1, Lo1, res, LaD, La2, Lo2, scan, 0, Di, Dj]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        params = {}
        tok = strings[0].split(":")
        params["LaD"] = float(tok[1])
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Ni"] = int(tok[1])
        params["Di"] = int(tok[2])
        params["Lo2"] = float(tok[3])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Nj"] = int(tok[1])
        params["Dj"] = int(tok[2])
        params["La2"] = float(tok[3])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        # FIXME: add x/y coordinates
        lon = longitude.reshape(self.shape)[0, :]
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        lat = latitude.reshape(self.shape)[:, 0]
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._coords = {
            "longitude": _Variable(("longitude",), lon, lon_attrs),
            "latitude": _Variable(("latitude",), lat, lat_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            scale = 1e-6
            gdtmpl[9] = int(latitude[0] / scale)
            gdtmpl[10] = int(longitude[0] / scale)
            gdtmpl[13] = int(latitude[-1] / scale)
            gdtmpl[14] = int(longitude[-1] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {
            "grid_mapping_name": self.cfname,
            "standard_parallel": self.params["GRIB_LaD"],
        }

    @property
    def dims(self) -> Tuple[str, str]:
        return ("latitude", "longitude")


class GridPolarStereo(Grid):
    """Grid definition for Polar Stereographic (North and South) projection."""

    cfname = "polar_stereographic"
    gdtnum = GDTNum.POLAR_STEREO
    _sec3_param_fmt = "IIIIBIIIIBB"
    _sec3_len = 65
    _respos = 11
    _scanpos = 17

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        Nx, Ny, La1, Lo1, res, LaD, LoV, Dx, Dy, proj_centre, scan = gdtmpl[7:]
        self._params.update(
            {
                "GRIB_Npts": Nx * Ny,
                "GRIB_Nx": Nx,
                "GRIB_Ny": Ny,
                "GRIB_La1": La1 * 1e-6,
                "GRIB_Lo1": Lo1 * 1e-6,
                "GRIB_LaD": LaD * 1e-6,
                "GRIB_LoV": LoV * 1e-6,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Dx": Dx * 1e-3,
                "GRIB_Dy": Dy * 1e-3,
                "GRIB_LaO": -90.0 if proj_centre & 0x80 else 90.0,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        La1 = int(params["La1"] * 1e6)
        Lo1 = int(params["Lo1"] * 1e6)
        LaD = int(params["LaD"] * 1e6)
        LoV = int(params["LoV"] * 1e6)
        Dx = int(params["Dx"] * 1e3)
        Dy = int(params["Dy"] * 1e3)
        Nx = params["Nx"]
        Ny = params["Ny"]
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        proj_centre = 0x80 if params["LaD"] < 0 else 0x00
        return [Nx, Ny, La1, Lo1, res, LaD, LoV, Dx, Dy, proj_centre, scan]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        params = {}
        tok = strings[0].split(":")
        params["LaO"] = 90.0 if tok[0] == "nps" else -90.0
        params["LoV"] = float(tok[1])
        params["LaD"] = float(tok[2])
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Nx"] = int(tok[1])
        params["Dx"] = float(tok[2])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Ny"] = int(tok[1])
        params["Dy"] = float(tok[2])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        lat_o = self._params["GRIB_LaO"]
        lon_o = self._params["GRIB_LoV"]
        gdtmpl = self._params["GRIB_gdtmpl"]
        xo, yo = latlon2xy(self._mksec3(gdtmpl), longitude, latitude, lon_o, lat_o)
        dx = self.params["GRIB_Dx"]
        dy = self.params["GRIB_Dy"]
        x = (np.arange(self.params["GRIB_Nx"]) - xo) * dx
        x_attrs = {
            "units": "m",
            "standard_name": "projection_x_coordinate",
            "axis": "X",
        }
        y = (np.arange(self.params["GRIB_Ny"]) - yo) * dy
        y_attrs = {
            "units": "m",
            "standard_name": "projection_y_coordinate",
            "axis": "Y",
        }
        lon = longitude.reshape(self.shape)
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        lat = latitude.reshape(self.shape)
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._coords = {
            "longitude": _Variable(self.dims, lon, lon_attrs),
            "latitude": _Variable(self.dims, lat, lat_attrs),
            "x": _Variable(("x",), x, x_attrs),
            "y": _Variable(("y",), y, y_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            scale = 1e-6
            gdtmpl[9] = int(latitude[0] / scale)
            gdtmpl[10] = int(longitude[0] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {
            "grid_mapping_name": self.cfname,
            "straight_vertical_longitude_from_pole": self.params["GRIB_LoV"],
            "standard_parallel": self.params["GRIB_LaD"],
            "latitude_of_projection_origin": self.params["GRIB_LaO"],
        }

    @property
    def dims(self) -> Tuple[str, str]:
        return ("y", "x")


class GridLambertConformal(Grid):
    """Grid definition for Lambert conformal projection."""

    cfname = "lambert_conformal_conic"
    gdtnum = GDTNum.LAMBERT_CONFORMAL
    _sec3_param_fmt = "IIIIBIIIIBBIIII"
    _sec3_len = 81
    _respos = 11
    _scanpos = 17

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        (
            Nx,
            Ny,
            La1,
            Lo1,
            res,
            LaD,
            LoV,
            Dx,
            Dy,
            proj_centre,
            scan,
            Latin1,
            Latin2,
            LaSP,
            LoSP,
        ) = gdtmpl[7:]
        self._params.update(
            {
                "GRIB_Npts": Nx * Ny,
                "GRIB_Nx": Nx,
                "GRIB_Ny": Ny,
                "GRIB_La1": La1 * 1e-6,
                "GRIB_Lo1": Lo1 * 1e-6,
                "GRIB_LaD": LaD * 1e-6,
                "GRIB_LoV": LoV * 1e-6,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Dx": Dx * 1e-3,
                "GRIB_Dy": Dy * 1e-3,
                "GRIB_Latin1": Latin1 * 1e-6,
                "GRIB_Latin2": Latin2 * 1e-6,
                "GRIB_LaSP": LaSP * 1e-6,
                "GRIB_LoSP": LoSP * 1e-6,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        La1 = int(params["La1"] * 1e6)
        Lo1 = int(params["Lo1"] * 1e6)
        LaD = int(params["LaD"] * 1e6)
        LoV = int(params["LoV"] * 1e6)
        Latin1 = int(params["Latin1"] * 1e6)
        Latin2 = int(params["Latin2"] * 1e6)
        proj_centre = 0x80 if params["Latin2"] < 0.0 else 0x00
        la_sp = -90.0 if proj_centre == 0 else 90.0
        LaSP = int(params.get("LaSP", la_sp) * 1e6)
        LoSP = int(params.get("LoSP", 0) * 1e6)
        Dx = int(params["Dx"] * 1e3)
        Dy = int(params["Dy"] * 1e3)
        Nx = params["Nx"]
        Ny = params["Ny"]
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        return [
            Nx,
            Ny,
            La1,
            Lo1,
            res,
            LaD,
            LoV,
            Dx,
            Dy,
            proj_centre,
            scan,
            Latin1,
            Latin2,
            LaSP,
            LoSP,
        ]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        params = {}
        tok = strings[0].split(":")
        params["LoV"] = float(tok[1])
        params["Latin1"] = float(tok[2])
        n = len(tok)
        params["Latin2"] = params["Latin1"] if n < 4 else float(tok[3])
        params["LaD"] = params["Latin2"] if n < 5 else float(tok[4])
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Nx"] = int(tok[1])
        params["Dx"] = int(tok[2])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Ny"] = int(tok[1])
        params["Dy"] = int(tok[2])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        lat_o = (self._params["GRIB_Latin1"] + self._params["GRIB_Latin2"]) / 2
        lon_o = self._params["GRIB_LoV"]
        gdtmpl = self._params["GRIB_gdtmpl"]
        xo, yo = latlon2xy(self._mksec3(gdtmpl), longitude, latitude, lon_o, lat_o)
        dx = self._params["GRIB_Dx"]
        dy = self._params["GRIB_Dy"]
        x = (np.arange(self._params["GRIB_Nx"]) - xo) * dx
        x_attrs = {
            "units": "m",
            "standard_name": "projection_x_coordinate",
            "axis": "X",
        }
        y = (np.arange(self._params["GRIB_Ny"]) - yo) * dy
        y_attrs = {
            "units": "m",
            "standard_name": "projection_y_coordinate",
            "axis": "Y",
        }
        lon = longitude.reshape(self.shape)
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        lat = latitude.reshape(self.shape)
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._coords = {
            "longitude": _Variable(self.dims, lon, lon_attrs),
            "latitude": _Variable(self.dims, lat, lat_attrs),
            "x": _Variable(("x",), x, x_attrs),
            "y": _Variable(("y",), y, y_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            scale = 1e-6
            gdtmpl[9] = int(latitude[0] / scale)
            gdtmpl[10] = int(longitude[0] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        lat_origin = (self._params["GRIB_Latin1"] + self._params["GRIB_Latin2"]) / 2
        return {
            "grid_mapping_name": self.cfname,
            "longitude_of_central_meridian": self._params["GRIB_LoV"],
            "standard_parallels": (
                self._params["GRIB_LoV"],
                self._params["GRIB_LoV"],
            ),
            "latitude_of_projection_origin": lat_origin,
        }

    @property
    def dims(self) -> Tuple[str, str]:
        return ("y", "x")


class GridGaussian(Grid):
    """Grid definition for Global Gaussian projection."""

    cfname = "gaussian"
    gdtnum = GDTNum.GAUSSIAN
    _sec3_param_fmt = "IIIIIIBIIIIB"
    _sec3_len = 72
    _respos = 13
    _scanpos = 18

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        Ni, Nj, ba, sba, La1, Lo1, res, La2, Lo2, Di, N, scan = gdtmpl[7:]
        scale = 1e-6 if ba == 0 else ba / sba
        self._params.update(
            {
                "GRIB_Npts": Ni * Nj,
                "GRIB_Ni": Ni,
                "GRIB_Nj": Nj,
                "GRIB_La1": La1 * scale,
                "GRIB_Lo1": Lo1 * scale,
                "GRIB_La2": La2 * scale,
                "GRIB_Lo2": Lo2 * scale,
                "GRIB_winds": "earth" if res & 0x08 == 0 else "grid",
                "GRIB_Di": Di * scale,
                "GRIB_N": N,
            }
        )

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> List[int]:
        ba = params.get("basic_angle", 0)
        sba = params.get("subdiv_basic_angle", -1)  # 0xFFFFFFFF)
        scale = 1e-6 if params.get("basic_angle", 0) == 0 else ba / sba
        Ni = params["Ni"]
        Nj = params["Nj"]
        La1 = int(params["La1"] / scale)
        Lo1 = int(params["Lo1"] / scale)
        La2 = int(params.get("La2", -params["La1"]) / scale)
        lo2 = params["Lo1"] + (Ni - 1) * params["Di"]
        Lo2 = int(params.get("Lo2", lo2) / scale)
        Di = int(params["Di"] / scale)
        N = params.get("N") or Nj // 2
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        return [Ni, Nj, ba, sba, La1, Lo1, res, La2, Lo2, Di, N, scan]

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        params = {}
        tok = strings[1].split(":")
        params["Lo1"] = float(tok[0])
        params["Ni"] = int(tok[1])
        params["Di"] = float(tok[2])
        tok = strings[2].split(":")
        params["La1"] = float(tok[0])
        params["Nj"] = int(tok[1])
        return params

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        lon = longitude.reshape(self.shape)[0, :]
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
            "axis": "X",
        }
        lat = latitude.reshape(self.shape)[:, 0]
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
            "axis": "Y",
        }
        self._coords = {
            "longitude": _Variable(("longitude",), lon, lon_attrs),
            "latitude": _Variable(("latitude",), lat, lat_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
            ba, sba = gdtmpl[9:11]
            scale = 1e-6 if ba == 0 else ba / sba
            gdtmpl[11] = int(latitude[0] / scale)
            gdtmpl[12] = int(longitude[0] / scale)
            gdtmpl[14] = int(latitude[-1] / scale)
            gdtmpl[15] = int(longitude[-1] / scale)
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {"grid_mapping_name": self.cfname}

    @property
    def dims(self) -> Tuple[str, str]:
        return ("latitude", "longitude")


class GridSpaceView(Grid):
    """Grid definition for Space View projection."""

    cfname = "space_view"
    gdtnum = GDTNum.SPACE_VIEW
    _sec3_param_fmt = "IIIIBIIIIBIIII"
    _respos = 11
    _scanpos = 16

    @staticmethod
    def encode_params(winds: Optional[str], **params) -> Sequence[int]:
        Nx = params["Nx"]
        Ny = params["Ny"]
        Dx = params["Dx"]
        Dy = params["Dy"]
        Xp = int(params["Xp"] * 1e3)
        Yp = int(params["Yp"] * 1e3)
        Nr = int(params["Nr"] * 1e3)
        Lap = int(params["Lap"] * 1e6)
        Lop = int(params["Lop"] * 1e6)
        OriAngle = int(params["OriAngle"] * 1e6)
        Xo = int(params["Xo"])
        Yo = int(params["Yo"])
        res = 0x38 if winds == "grid" else 0x30
        scan = 0x40
        return [Nx, Ny, Lap, Lop, res, Dx, Dy, Xp, Yp, scan, OriAngle, Nr, Xo, Yo]

    def decode_params(self) -> None:
        gdtmpl = self._params["GRIB_gdtmpl"]
        (
            Nx,
            Ny,
            Lap,
            Lop,
            res,
            Dx,
            Dy,
            Xp,
            Yp,
            scan,
            OriAngle,
            Nr,
            Xo,
            Yo,
        ) = gdtmpl[7:]
        self._params.update(
            {
                "GRIB_Npts": Nx * Ny,
                "GRIB_Nx": Nx,
                "GRIB_Ny": Ny,
                "GRIB_Lap": Lap * 1e-6,
                "GRIB_Lop": Lop * 1e-6,
                "GRIB_Dx": Dx,
                "GRIB_Dy": Dy,
                "GRIB_Xp": Xp * 1e-3,
                "GRIB_Yp": Yp * 1e-3,
                "GRIB_OriAngle": OriAngle * 1e-6,
                "GRIB_Nr": Nr * 1e-6,
                "GRIB_Xo": Xo,
                "GRIB_Yo": Yo,
            }
        )

    @staticmethod
    def strings2params(strings: List[str]) -> Dict[str, Any]:
        raise NotImplementedError()

    def set_coords(self, longitude: Any, latitude: Any) -> None:
        if self._globe["shape"] == "sphere":
            rx = ry = self._globe["earth_radius"]
        else:
            rx = self._globe["semi_major_axis"]
            ry = self._globe["semi_minor_axis"]
        h = self._params["GRIB_Nr"]
        a_x = np.arctan(rx / (rx + h))
        a_y = np.arctan(ry / (ry + h))
        dx = self._params["GRIB_Dx"]
        dy = self._params["GRIB_Dy"]
        xp = self._params["GRIB_Xp"]
        yp = self._params["GRIB_Yp"]
        x = 2 * a_x * h / dx * (np.arange(self._params["GRIB_Nx"] - xp))
        x_attrs = {"units": "m", "standard_name": "projection_x_coordinate"}
        y = 2 * a_y * h / dy * (np.arange(self._params["GRIB_Ny"] - yp))
        y_attrs = {"units": "m", "standard_name": "projection_y_coordinate"}
        lon = longitude.reshape(self.shape)
        lon_attrs = {
            "long_name": "longitude coordinate",
            "units": "degree_east",
            "standard_name": "longitude",
        }
        lat = latitude.reshape(self.shape)
        lat_attrs = {
            "long_name": "latitude coordinate",
            "units": "degree_north",
            "standard_name": "latitude",
        }
        self._coords = {
            "x": _Variable(("x",), x, x_attrs),
            "y": _Variable(("y",), y, y_attrs),
            "longitude": _Variable(self.dims, lon, lon_attrs),
            "latitude": _Variable(self.dims, lat, lat_attrs),
        }

    def to_wesn(self, longitude: Any, latitude: Any) -> List[int]:
        gdtmpl = self.gdtmpl[:]
        if gdtmpl[self._scanpos] != 0x40:
            gdtmpl[self._scanpos] = 0x40
        return gdtmpl

    @property
    def crs(self) -> Dict[str, Any]:
        return {"grid_mapping_name": self.cfname}

    @property
    def dims(self) -> Tuple[str, str]:
        return ("y", "x")


def grid_fromgds(gdtnum, gdtmpl):
    """Factory method to create projection from grid definition section.

    Parameters
    ----------
    gdtnum: int
        Grid definition template number: table 3.1
    gdtmpl: array_like
        Grid definition template obtained from wgrib2 -pyinv.

    Returns
    -------
    Grid
        Projection specific class instance.
    """
    cls = {
        GDTNum.LATLON: GridLatLon,
        GDTNum.ROT_LATLON: GridRotLatLon,
        GDTNum.MERCATOR: GridMercator,
        GDTNum.POLAR_STEREO: GridPolarStereo,
        GDTNum.LAMBERT_CONFORMAL: GridLambertConformal,
        GDTNum.GAUSSIAN: GridGaussian,
        GDTNum.SPACE_VIEW: GridSpaceView,
    }.get(gdtnum)
    if not cls:
        raise ValueError("Invalid or unsupported projection: {:d}".format(gdtnum))
    return cls(gdtmpl)


def grid_fromdict(projname, globe=None, **kwargs):
    """Factory method to create projection from dictionary.

    Parameters
    ----------
    projname: str
        Projection name, one of {'latitude_longitude', 'rotated_latitude_longitude',
        'mercator', 'polar_stereographic', 'lambert_conformal', 'gaussian',
        'space_view'}.
    globe: dict
        Mapping: code -> int, 'shape' -> str, 'earth_radius' -> float,
        'semi_major_axis' -> float, 'semi_minor_axis' -> float
    **kwargs:
        Projection-specific parameters.

        - latitude_longitude:

            - La1 : latitude of first grid point
            - Lo1 : longitude of first grid point
            - Ni : number of points along a parallel
            - Nj : number of points along a meridan
            - Di : i direction increment (deg)
            - Dj : j direction increment (deg)

        - rotated latitude_longitude:

            - La1 : latitude of first grid point
            - Lo1 : longitude of first grid point
            - Ni : number of points along a parallel
            - Nj : number of points along a meridan
            - Di : i direction increment (deg)
            - Dj : j direction increment (deg)
            - LaSP : latitude of the southern pole of projection
            - LoSP : longitude of the southern pole of projection
            - Rot : angle of rotation of projection

         - mercator:

            - La1 : latitude of first grid point
            - Lo1 : longitude of first grid point
            - La2 : latitude of last grid point
            - Lo2 : longitude of last grid point
            - LaD : latitude  where Di and Dj are specified
            - Ni : number of points along a parallel
            - Nj : number of points along a meridian
            - Di : longitudinal direction grid length
            - Dj : latitudinal direction grid length

       wgrib2/Sec1.c  - polar_stereographic:

            - La1 : latitude of first grid point
            - Lo1 : longitude of first grid point
            - LaD : latitude  where Dx and Dy are specified [deg]. \
                    LaD must be 60 (nps) or -60 (sps) (library limitation).
            - LoV : longitude where y axis is parallel to meridian.
            - LaO : latitude of projection origin, either 90 (nps) or -90 (sps)
            - Nx : number of points along the x-axis
            - Ny : number of points along the y-axis
            - Dx : x-direction grid length [m]
            - Dy : y-direction  grid length [m]

        - lambert_conformal_conic:

            - La1 : latitude of first grid point
            - Lo1 : longitude of first grid point
            - LaD : latitude  where Dx and Dy are specified [deg]
            - LoV : longitude where y axis is parallel to meridian
            - Latin1 : first latitude from pole which cuts the secant cone
            - Latin2 : second latitude from pole which cuts the secant cone
            - Nx : number of points along the x-axis
            - Ny : number of points along the y-axis
            - Dx : x-direction grid length [m]
            - Dy : y-direction  grid length [m]

        - gaussian :
            - lat0, lon0 : degrees of lat/lon for 1st grid point \
                ``lon1 = -lon0``, ``lat1 = lat0 + (nx-1)*dlon``
            - nx : number of grid points in X direction.
            - ny : number of grid points in Y direction. `ny` must be even.
            - dlon : degrees of longitude between adjacent grid points.

        - space_view :

            - Lap : latitude of sub-satellite point
            - Lop : longitude of sub-satellite point
            - Nx : number of points along the x-axis
            - Ny : number of points along the y-axis
            - Dx : apparent diameter of Earth in grid lengths, in x-direction
            - Dy : apparent diameter of Earth in grid lengths, in y-direction
            - Xp : x-coordinate of sub-satellite point
            - Yp : y-coordinate of sub-satellite point
            - Nr : altitude of the camera from the Earth's centre, measured in units of the Earth's (equatorial) radius
            - Xo : x-coordinate of origin of sector image
            - Yo : y-coordinate of origin of sector image

        - unstructured :

            - Npts : number of points.

        The following parameter is common for all projections :

            - winds : {'grid', 'earth'}, optional. Vector orientation. Default is 'earth'.

    Returns
    -------
    Grid
        Projection specific class instance.
    """
    cls = {
        "latitude_longitude": GridLatLon,
        "rotated_latitude_longitude": GridRotLatLon,
        "mercator": GridMercator,
        "polar_stereographic": GridPolarStereo,
        "lambert_conformal": GridLambertConformal,
        "gaussian": GridGaussian,
        "space_view": GridSpaceView,
    }.get(projname)
    if not cls:
        raise ValueError("Invalid or unsupported projection: {:s}".format(projname))
    return cls.fromdict(**kwargs)


NCEP_GRIDS = {
    2: "latlon 0:144:2.5 90:73:-2.5",
    3: "latlon 0:360:1 90:181:-1",
    4: "latlon 0:720:0.5 90:361:-0.5",
    45: "latlon 0:288:1.25 90:145:-1.25",
    98: "gaussian 0:192:1.875 88.5419501372975:94",
    126: "gaussian 0:384:0.9375 89.2767128781058:190",
    127: "gaussian 0:768:0.46875 89.6416480725934:384",
    128: "gaussian 0:1152:0.3125 89.7609950778017:576",
    129: "gaussian 0:1760:0.20454545454545 89.8435135178685:880",
    170: "gaussian 0:512:0.703125 89.4628215685774:256",
    173: "latlon 0.041666667:4320:0.083333333 89.95833333:2160:-0.083333333",
    184: "lambert:265:25 238.446:2145:2540 20.192:1377:2540",
    194: "mercator:20 284.5:544:2500:297.491 15:310:2500:22.005",
    221: "lambert:253:50 214.5:349:32463.41 1:277:32463.41",
    230: "latlon 0:720:0.5 90:361:-0.5",
    242: "nps:225:60 187:553:11250 30:425:11250",
    249: "nps:210.0:60.0 188.4:367:9867.89 45.4:343:9867.89",
}


def grid_fromstring(string, winds="grid", globe=None):
    """Factory method to create projection from `wgrib2` style string.

    Parameters
    ----------
    string: str
        Grid description in
        `wgrib2 style <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/new_grid.html>`_:

        - latitude longitude : 'latlon lon0:nlon:dlon lat0:nlat:dlat', where

            - lon0, lat0 : degrees of lat/lon for 1st grid point.
            - nlon : number of longitudes.
            - nlat : number of latitudes.
            - dlon : grid cell size in degrees of longitude.
            - dlat : grid cell size in degrees of latitude.

        - rotated latitude longitude : 'rot-ll:sp_lon:sp_lat:sp_rot lon0:nlon:dlon lat0:nlat:dlat', where

            - sp_lon : longitude of the South pole (for rotation)
            - sp_lat : latitude of the South pole (for rotation)
            - sp_rot : angle of rotation
            - lon0, lat0 : degrees of lat/lon for 1st grid point.
            - nlon : number of longitudes.
            - nlat : number of latitudes.
            - dlon : grid cell size in degrees of longitude.
            - dlat : grid cell size in degrees of latitude.

        - Mercator : 'mercator:lad lon0:nx:dx:lonn lat0:ny:dy:latn', where

            - lad : latitude (degrees) where dx and dy are specified.
            - lat0, lon0 : degrees of lat/lon for 1st grid point.
            - latn, lonn : degrees of lat/lon for last grid point.
            - nx : number of grid points in X direction.
            - ny : number of grid points in Y direction.
            - dx : grid cell distance in meters in x direction at lad.
            - dy : grid cell distance in meters in y direction at lad.

        - north polar stereographic: 'nps:lov:lad lon0:nx:dx lat0:ny:dy'
        - south polar stereographic: 'sps:lov:lad lon0:nx:dx lat0:ny:dy'

            - lov : longitude (degrees) where y axis is parallel to meridian.
            - lad : latitude (degrees) where dx and dy are specified. \
                    lad must be 60 (nps) or -60 (sps) (library limitation).
            - lat0, lon0 : degrees of lat/lon for 1st grid point.
            - nx : number of grid points in X direction.
            - ny : number of grid points in Y direction.
            - dx : grid cell distance meters in x direction at lad.
            - dy : grid cell distance meters in y direction at lad.

        - Lambert conformal : 'lambert:lov:latin1:latin2:lad lon0:nx:dx lat0:ny:dy'

            - lov : longitude (degrees) where y axis is parallel to meridian
            - latin1 : first latitude from pole which cuts the secant cone
            - latin2 : second latitude from pole which cuts the secant cone
            - lad : latitude (degrees) where dx and dy are specified
            - lat0, lon0 : degrees of lat/lon for first grid point
            - nx : number of grid points in X direction
            - ny : number of grid points in Y direction
            - dx : grid cell size in meters in x direction
            - dy : grid cell size in meters in y direction

        - global Gaussian: 'gaussian lon0:nx:dlon lat0:ny'

            lat0, lon0 : degrees of lat/lon for 1st grid point \
                ``(lon1 = -lon0``, ``lat1 = lat0 + (nx-1)*dlon)``

            nx : number of grid points in X direction.

            ny : number of grid points in Y direction. `ny` must be even.

            dlon : degrees of longitude between adjacent grid points.

    winds : {'grid', 'earth'}
        Vector orientation. Default is 'grid'.
    globe: dict, optional
        Mapping: code -> int, 'shape' -> str, 'earth_radius' -> float,
        'semi_major_axis' -> float, 'semi_minor_axis' -> float
        Default is current NCEP choice: Earth assumed spherical with
        radius = 6,371,229.0 m.

    Returns
    -------
    Grid
        Projection specific class instance.
    """
    tokens = string.split()
    if len(tokens) != 3:
        raise ValueError("Invalid grid description: {:s}".format(string))
    if tokens[0] == "ncep" and tokens[1] == "grid":
        # Predefined grids known to wgrib2
        gridnum = int(tokens[2])
        try:
            string = NCEP_GRIDS[gridnum]
        except KeyError:
            raise ValueError("Unsupported NCEP grid: {:d}".format(gridnum))
        tokens = string.split()

    projname = tokens[0].split(":")[0]
    f = {
        "latlon": GridLatLon.fromstring,
        "rot-ll": GridRotLatLon.fromstring,
        "mercator": GridMercator.fromstring,
        "nps": GridPolarStereo.fromstring,
        "sps": GridPolarStereo.fromstring,
        "lambert": GridLambertConformal.fromstring,
        "gaussian": GridGaussian.fromstring,
    }.get(projname)
    if not f:
        raise ValueError("Invalid or unsupported projection: {:s}".format(projname))
    return f(tokens, winds=winds, globe=globe)

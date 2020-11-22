from datetime import datetime, timedelta
from functools import partial
from typing import (
    Any,
    Callable,
    Dict,
    List,
    NamedTuple,
    Optional,
    Sequence,
    Set,
    Tuple,
)

# For older Pythons
try:
    from typing import TypedDict
except ImportError:
    from mypy_extensions import TypedDict

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any

import numpy as np
from dask.base import tokenize

from . import __version__, _Variable
from .inventory import (
    MetaData,
    item_match,
    load_or_make_inventory,
)
from .grids import grid_fromgds

# FIME: remove?
# wgrib2 returns C float arrays
# DTYPE = np.dtype("float32")
# From wgrib2 CodeTable_4.10.dat
# Spaces are intentional
TIME_MODS = [
    " ave ",
    " acc ",
    " max ",
    " min ",
    " last-first ",
    " RMS ",
    " StdDev ",
    " covar ",
    " first-last ",
    " ratio ",
    " standardized anomaly ",
    " summation ",
]


class VertLevel(NamedTuple):
    type: str
    reverse: bool  # sort order
    units: str


# Possible 3-D variables
VERT_LEVELS: Dict[int, VertLevel] = {
    100: VertLevel("isobaric", True, "Pa"),
    102: VertLevel("height_asl", False, "m"),
    103: VertLevel("height_agl", False, "m"),
    104: VertLevel("sigma", True, ""),
    105: VertLevel("hybrid", False, ""),
}


# Used to set dataset attributes
class CommonInfo(NamedTuple):
    reftime: datetime
    centre: str
    subcentre: str
    gdtnum: int
    gdtmpl: List[int]

    def check_item(self, item: MetaData) -> None:
        if item.reftime != self.reftime:
            raise ValueError(
                "Reference times differ: {!r} != {!r}".format(
                    self.reftime, item.reftime
                )
            )
        if item.gdtnum != self.gdtnum or item.gdtmpl != self.gdtmpl:
            raise ValueError(
                "Grids differ: {:d}: {!r} != {:d}: {!r}".format(
                    self.gdtnum, self.gdtmpl, item.gdtnum, item.gdtmpl
                )
            )


class VarSpecs(NamedTuple):
    time_coord: str  # forecast time coordinate
    level_coord: Optional[str]  # level (type from VertLevel) coordinate
    dims: Sequence[str]  # dimension names
    shape: Tuple[int, ...]  # array shape
    attrs: Dict[str, Any]  # attributes


# Containers used to construct VarSpecs
class VarInfo(TypedDict):
    long_name: str
    units: str
    fcst_time: Set[timedelta]
    level: VertLevel
    level_value: Set[float]


class TimeCoord(NamedTuple):
    name: str
    values: ArrayLike


class LevelCoord(NamedTuple):
    level: VertLevel
    name: str
    values: ArrayLike


def item_to_varname(item: MetaData, vert_levels: Dict[int, VertLevel]) -> str:
    def _level() -> str:
        # return lvl["type"] if (lvl := vert_levels.get(item.level_code)) else ""
        # For Python < 3.8 and flake8
        lvl = vert_levels.get(item.bot_level_code)
        return lvl.type if lvl else item.level_str

    def _time() -> str:
        td = item.end_ft - item.start_ft
        if td <= timedelta(0):
            return ""
        # skip values like "102 hour fcst", consider only periods
        for tm in TIME_MODS:
            if tm in item.time_str:
                days, hours, minutes = (
                    td.days,
                    td.seconds // 3600,
                    (td.seconds // 60) % 60,
                )
                if minutes:
                    minutes += 60 * hours
                    return "{:d}_min_{:s}".format(minutes, tm.strip())
                elif hours:
                    hours += 24 * days
                    return "{:d}_hour_{:s}".format(hours, tm.strip())
                elif days:
                    return "{:d}_day_{:s}".format(days, tm.strip())
        return ""

    parts = (item.varname, _level(), _time())
    return ".".join([x for x in parts if x]).replace(" ", "_")


class Template:
    """Defines dataset structure.

    This is an opaque class instantiated by :py:func:`make_template`.
    It's purpose is to define Dataset structure and avoid complex merges.
    """

    def __init__(
        self,
        commoninfo: CommonInfo,
        var_info_map: Dict[str, VarInfo],
        vert_level_map: Dict[int, VertLevel],
        predicates: Optional[Sequence[Callable[[MetaData], bool]]] = None,
    ):
        if predicates is None:
            predicates = []
        else:
            predicates = list(predicates)
        self.commoninfo = commoninfo
        self.grid = grid_fromgds(commoninfo.gdtnum, commoninfo.gdtmpl)
        self.coords = {k: _Variable(*v) for k, v in self.grid.coords.items()}
        level_dims, level_coords, level_var2coord = self._build_level_coords(
            var_info_map
        )
        self.coords.update(level_coords)
        time_dims, time_coords, time_var2coord = self._build_time_coords(var_info_map)
        self.coords.update(time_coords)
        self.var_specs = self._build_var_specs(
            var_info_map, time_dims, time_var2coord, level_dims, level_var2coord
        )
        self.attrs = self._build_attrs()
        self.item_to_varname = partial(item_to_varname, vert_levels=vert_level_map)

        predicates.append(self._same_grid)
        self.item_match = partial(item_match, predicates=predicates)

    def __repr__(self):
        summary = [
            "Coordinates:",
            repr(self.coords),
            # "Variable names:",
            # repr(self._var_spec.),
            "Variable specs",
            repr(self.var_specs),
            "Attributes:",
            repr(self.attrs),
        ]
        return "\n".join(summary)

    @property
    def var_names(self):
        return sorted(list(self.var_specs.keys()))

    @staticmethod
    def _build_level_coords(
        var_info_map: Dict[str, VarInfo]
    ) -> Tuple[Dict[str, int], Dict[str, _Variable], Dict[str, str]]:
        def _name(v: Sequence[Any]) -> str:
            return tokenize(*v)

        def _sort(v: VarInfo) -> LevelCoord:
            vert_level = v["level"]
            coords = sorted(v["level_value"], reverse=vert_level.reverse)
            dimname = _name(coords)
            return LevelCoord(vert_level, dimname, coords)

        def _levels() -> Dict[str, LevelCoord]:
            levels = {k: _sort(v) for k, v in var_info_map.items() if v["level"]}
            s = set([(v.level, v.name) for v in levels.values()])
            names = {
                name: "{:s}{:d}".format(level.type, i + 1)
                for (i, (level, name)) in enumerate(s)
            }
            return {
                k: LevelCoord(v.level, names[v.name], v.values)
                for (k, v) in levels.items()
            }

        levels = _levels()
        coords = {}
        dims = {}
        var2coord = {}
        for k, v in levels.items():
            var2coord[k] = v.name
            attrs = {
                "units": v.level.units,
                "axis": "Z",
                "positive": "down" if v.level.reverse else "up",
            }
            coords[v.name] = _Variable((v.name), np.array(v.values), attrs)
            dims[v.name] = len(v.values)
        return dims, coords, var2coord

    @staticmethod
    def _build_time_coords(
        var_info_map: Dict[str, VarInfo]
    ) -> Tuple[Dict[str, int], Dict[str, _Variable], Dict[str, str]]:
        def _name(v: Sequence[Any]) -> str:
            return tokenize(*[t.seconds for t in v])

        def _sort(v: VarInfo) -> TimeCoord:
            coords = sorted(v["fcst_time"])
            dimname = _name(coords)
            return TimeCoord(dimname, coords)

        # varname -> TimeCoord
        def _times() -> Dict[str, TimeCoord]:
            times = {k: _sort(v) for k, v in var_info_map.items()}
            s = set([v.name for v in times.values()])
            # Convert hashes to integers. Sort set to ensure consistent mapping
            # Follow Metpy naming: time<N>
            names = {n: "time{:d}".format(i + 1) for (i, n) in enumerate(sorted(s))}
            return {k: TimeCoord(names[v.name], v.values) for (k, v) in times.items()}

        times = _times()
        # Squeeze only when all time dimensions are == 1.
        squeeze = max([len(v.values) for v in times.values()]) == 1
        coords = {}
        dims = {}
        var2coord = {}
        attrs = {"standard_name": "forecast_period"}
        for k, v in times.items():
            var2coord[k] = v.name
            if squeeze:
                coords[v.name] = _Variable((), np.array(v.values[0]), attrs)
            else:
                coords[v.name] = _Variable((v.name), np.array(v.values), attrs)
                dims[v.name] = len(v.values)
        return dims, coords, var2coord

    def _build_attrs(self) -> Dict[str, str]:
        return {
            "Projection": self.grid.cfname,
            "Originating centre": self.commoninfo.centre,
            "Originating subcentre": self.commoninfo.subcentre,
            "History": "Created by pywgrib2_xr-{:s}".format(__version__),
        }

    def _build_var_specs(
        self,
        var_info_map: Dict[str, VarInfo],
        time_dims: Dict[str, int],
        time_var2coord: Dict[str, str],
        level_dims: Dict[str, int],
        level_var2coord: Dict[str, str],
    ) -> Dict[str, VarSpecs]:
        def _make_specs(k, v):
            time_coord = time_var2coord[k]
            if time_coord in time_dims:
                dims = [time_coord]
                shape = [time_dims[time_coord]]
            else:
                dims = []
                shape = []
            if v["level"]:
                level_coord = level_var2coord[k]
                dims.append(level_coord)
                shape.append(level_dims[level_coord])
            else:
                level_coord = None
            dims.extend(list(self.grid.dims))
            shape.extend(self.grid.shape)
            attrs = dict(
                short_name=k.split(".")[0],
                long_name=v["long_name"],
                units=v["units"],
                grid_mapping=self.grid.cfname,
            )
            return VarSpecs(time_coord, level_coord, dims, shape, attrs)

        return {k: _make_specs(k, v) for k, v in var_info_map.items()}

    def _same_grid(self, i: MetaData) -> bool:
        return i.gdtnum == self.commoninfo.gdtnum and i.gdtmpl == self.commoninfo.gdtmpl


def make_template(
    files,
    *predicates,
    vertlevels=None,
    reftime=None,
    save=False,
    invdir=None,
):
    """Creates template from GRIB2 files.

    Parameters
    ----------
    files : str of iterable of str.
        List of GRIB files containing messages with unique `reftime`.
        For example, files for all or a subset of forecast times.
    predicates : callable
        Zero or more boolean functions to select desired variables.
        A variable is selected if one of predicates returns True.
        The default is None, means matches everything.
    vertlevels : str or list of str, optional.
        One of {'isobaric', 'height_asl', 'height_agl', 'sigma', 'hybrid'}.
        Specifies vertical coordinates.
        If None (default), all data variables will be 2-D in space.
    reftime : str or datetime, optional
        Reference time. Default is None. A string must be in the ISO format:
        YYYY-mm-ddTHH:MM:SS.
        This argument must be specified for files with multiple reference times.
    save : bool, optional.
        If True, inventory will be saved to a file. File name and location depends on
        'invdir'. If 'invdir' is given, the inventory file will be a hashed path
        of the GRIB file written to 'invdir'. Otherwise file name will be that of
        the GRIB file, with appended extension ``pyinv``.
        The intention is to allow for temporary inventory when GRIB files are on
        a read-only medium. Default is False.
    invdir : str, optional
        Location of inventory files.

    Returns
    -------
    Template
        Instantiated class defining dataset structure.
        None is returned if no messages match the selection criteria.

    Examples
    --------
    The two equivalent functions select temperature at pressure level:

    >>> lambda x: x.varname == 'TMP' and x.bot_level_code == 100 and x.top_level_code = 255
    >>> lambda x: x.varname == 'TMP' and re.match(r'\\d+ mb', x.level_str)

    To select accumulated 3 hour precipitation, define function `match_pcp3`:

    >>> def match_pcp3(x):
    >>>     return x.varname == 'APCP' and x.end_ft - x.start_ft == timedelta(hours=3)
    """
    if isinstance(files, str):
        files = [files]
    if not vertlevels:
        vertlevels = []
    elif isinstance(vertlevels, str):
        vertlevels = [vertlevels]
    if isinstance(reftime, str):
        reftime = datetime.fromisoformat(reftime)
    vert_level_map = {c: v for c, v in VERT_LEVELS.items() if v.type in vertlevels}
    var_info_map: Dict[str, VarInfo] = {}
    commoninfo = None
    for file in files:
        inventory = load_or_make_inventory(file, save=save, directory=invdir)
        if not inventory:
            continue
        matched_items = (i for i in inventory if item_match(i, predicates))
        if reftime is not None:
            matched_items = (i for i in matched_items if i.reftime == reftime)
        for item in matched_items:
            if commoninfo:
                commoninfo.check_item(item)
            else:
                # Only regular grids are allowed
                if item.npts != item.nx * item.ny:
                    raise ValueError("Thinned grids are not supported")
                commoninfo = CommonInfo(
                    item.reftime, item.centre, item.subcentre, item.gdtnum, item.gdtmpl
                )
            varname = item_to_varname(item, vert_level_map)
            if varname not in var_info_map:
                var_info_map[varname] = {
                    "long_name": item.long_name,
                    "units": item.units,
                    "fcst_time": set(),
                    "level": vert_level_map.get(item.bot_level_code),
                    "level_value": set(),
                }
            # Add time and level values
            varinfo = var_info_map[varname]  # a reference
            varinfo["fcst_time"].add(item.end_ft - item.reftime)
            if varinfo["level"]:
                varinfo["level_value"].add(item.bot_level_value)

    if var_info_map:
        return Template(commoninfo, var_info_map, vert_level_map, predicates)
    return None

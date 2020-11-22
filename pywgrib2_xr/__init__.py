# flake8: noqa

from typing import Any, Dict, NamedTuple, Sequence
import numpy as np

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any

from .version import version as __version__

UNDEFINED = float(np.float32(9.999e20))
"""Missing data value used by `wgrib2`"""


class WgribError(Exception):
    pass


# Like xarray's Variable
class _Variable(NamedTuple):
    dims: Sequence[str]
    data: ArrayLike
    attrs: Dict[str, Any]


from .accessor import Wgrib2DatasetAccessor
from .grids import (
    GDTNum,
    Point,
    Grid,
    GridLatLon,
    GridRotLatLon,
    GridMercator,
    GridPolarStereo,
    GridLambertConformal,
    GridGaussian,
    GridSpaceView,
    grid_fromdict,
    grid_fromgds,
    grid_fromstring,
)
from .inventory import (
    MetaData,
    FileMetaData,
    make_inventory,
    save_inventory,
    load_inventory,
    load_or_make_inventory,
    item_match,
)
from .ip import (
    earth2grid_points,
    grid2earth_grid,
    grid2earth_points,
    ips_grid,
    ips_points,
    ipv_grid,
    ipv_points,
)
from .message import read_msg, decode_msg, write_msg
from .template import Template, make_template
from .wgrib2 import (
    MemoryBuffer,
    RPNRegister,
    free_files,
    set_num_threads,
    status_open,
    wgrib,
)

from . import utils
from .xarray_store import open_dataset

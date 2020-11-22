import ast
import copy
from datetime import datetime
import hashlib
import logging
import os
import pickle
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

try:
    import blosc
except ImportError:
    blosc = None

from . import WgribError
from .wgrib2 import MemoryBuffer, wgrib, free_files

logger = logging.getLogger(__name__)


class MetaData:
    """GRIB2 message metadata.

    Contains subset of decoded elements from sections 1 - 4 of a GRIB2 message.
    """

    __slots__: Tuple[str, ...] = (
        "file",
        "offset",
        "varname",
        "level_str",
        "time_str",
        "discipline",
        "centre",
        "subcentre",
        "mastertab",
        "localtab",
        "long_name",
        "units",
        "pdt",
        "parmcat",
        "parmnum",
        "bot_level_code",
        "bot_level_value",
        "top_level_code",
        "top_level_value",
        "reftime",
        "start_ft",
        "end_ft",
        "npts",
        "nx",
        "ny",
        "gdtnum",
        "gdtmpl",
    )

    def __init__(self, *args, **kwargs) -> None:
        if TYPE_CHECKING:
            self.file: str = kwargs.get("file", "")
            self.offset: str = kwargs["offset"]
            self.varname: str = kwargs["varname"]
            self.level_str: str = kwargs["level_str"]
            self.time_str: str = kwargs["time_str"]
            self.discipline: int = kwargs["discipline"]
            self.centre: str = kwargs["centre"]
            self.subcentre: str = kwargs["subcentre"]
            self.mastertab: int = kwargs["mastertab"]
            self.localtab: int = kwargs["localtab"]
            self.long_name: str = kwargs["long_name"]
            self.units: str = kwargs["units"]
            self.pdt: int = kwargs["pdt"]
            self.parmcat: int = kwargs["parmcat"]
            self.parmnum: int = kwargs["parmnum"]
            self.bot_level_code: int = kwargs["bot_level_code"]
            self.bot_level_value: float = kwargs["bot_level_value"]
            self.top_level_code: int = kwargs["top_level_code"]
            self.top_level_value: Optional[float] = kwargs.get("top_level_value")
            self.reftime: datetime = kwargs["reftime"]
            self.start_ft: datetime = kwargs["start_ft"]
            self.end_ft: datetime = kwargs["end_ft"]
            self.npts: int = kwargs["npts"]
            self.nx: int = kwargs["nx"]
            self.ny: int = kwargs["ny"]
            self.gdtnum: int = kwargs["gdtnum"]
            self.gdtmpl: List[int] = kwargs["gdtmpl"]
        else:
            for s in self.__slots__:
                setattr(self, s, kwargs.get(s))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        for s in self.__slots__:
            if getattr(self, s) != getattr(other, s):
                return False
        return True

    def __repr__(self) -> str:
        width = max([len(x) for x in self.__slots__])
        fmt = "{{:>{:d}}}: {{!r}}".format(width)
        summary = ["<{:s}>".format(self.__class__.__name__)]
        summary.extend([fmt.format(s, getattr(self, s)) for s in self.__slots__])
        return "\n".join(summary)

    # Shorthand for single levels
    @property
    def level_code(self):
        """Shortcut for self.bot_level_code."""
        return self.bot_level_code

    @property
    def level_value(self):
        """Shortcut for self.bot_level_value."""
        return self.bot_level_value


class FileMetaData:
    file: Optional[str]
    meta: List[MetaData]

    def __init__(self, file: Optional[str], inventory: Sequence[MetaData]):
        self.file = file
        self.meta = [self._copy(i) for i in inventory]

    def __repr__(self) -> str:
        if self.file:
            lines = ["<{:s}> {:s}".format(self.__class__.__name__, self.file)]
        else:
            lines = ["<{:s}>".format(self.__class__.__name__)]
        slots = MetaData.__slots__[1:]  # Skip 'file'
        lines.extend(
            [
                "|".join(("{!s}={!s}".format(s, str(getattr(i, s))) for s in slots))
                for i in self.meta
            ]
        )
        return "\n".join(lines)

    def __str__(self) -> str:
        if self.file:
            lines = ["<{:s}> {:s}".format(self.__class__.__name__, self.file)]
        else:
            lines = ["<{:s}>".format(self.__class__.__name__)]
        slots = ("offset", "varname", "level_str", "time_str", "reftime")
        lines.extend(["|".join((str(getattr(i, s)) for s in slots)) for i in self.meta])
        return "\n".join(lines)

    @staticmethod
    def _copy(meta, file=None):
        newmeta = copy.copy(meta)
        newmeta.file = file
        return newmeta

    def to_meta(self, file: str = None) -> List[MetaData]:
        if self.file:
            file = self.file
        elif not file:
            raise ValueError("Misssing argument 'file'")
        return [self._copy(i, file) for i in self.meta]


def item_match(item, predicates=None):
    """Returns True if one of predicates evaluates to True.

    Parameters
    ----------
    item: MetaData
    predicates : sequence
       Sequence of boolean functions accepting `item` as an argument.

    Returns
    -------
    bool
    """
    if not predicates:
        return True
    return next((True for p in predicates if p(item)), False)


# Remove parantheses from level_str
_trans_table = str.maketrans({"(": "", ")": ""})


def _meta_from_string(file: str, s: str) -> MetaData:
    # Will raise IndexError on invalid string
    i = s.index("pyinv")
    tok = s[:i].split(":")
    d: Dict[str, Any] = {"file": file}
    d["offset"] = ":".join(tok[:2])
    d["varname"] = tok[2]
    d["level_str"] = tok[3].translate(_trans_table)
    d["time_str"] = tok[4]
    d.update(ast.literal_eval(s[i + len("pyinv=") :]))
    # Fix level string to eliminate slashes - messing up conversion to NetCDF.
    level_code = d["bot_level_code"]
    if level_code in (21, 22, 23, 24):
        d["level_str"] = d["level_str"].replace("/m^3", "*m-3")
    elif level_code == 109:
        d["level_str"] = d["level_str"].replace("Km^2/kg/s", "K*m2*kg-1*s-1")
    for k in ["reftime", "start_ft", "end_ft"]:
        d[k] = datetime.fromisoformat(d[k])
    return MetaData(**d)


# def make_inventory(file: str) -> Union[None, List[MetaData]]:
def make_inventory(file):
    """Creates inventory for file 'file'.

    Parameters
    ----------
    file : str
        GRIB file name.

    Returns
    -------
    inv : list
        pywgrib2_xr.MetaData for all messages in GRIB file.
    """
    with MemoryBuffer() as buf:
        try:
            wgrib(file, "-rewind_init", file, "-inv", buf, "-pyinv")
            return [_meta_from_string(file, s) for s in buf.get("s").split("\n") if s]
        except WgribError as e:
            logger.error("wgrib2 error: {!r}".format(e))
            return None
        finally:
            free_files(file)


def inventory_name(file: str, directory: Optional[str] = None) -> str:
    ext = ".pinv" if blosc is None else ".binv"
    if directory:
        inv_file = hashlib.md5(file.encode()).hexdigest()
        return os.path.join(directory, inv_file) + ext  # local file
    return file + ext  # collocated with GRIB file


def save_inventory(
    inventory: Sequence[MetaData], file: str, directory: Optional[str] = None
) -> None:
    """Saves inventory to a file.

    Parameters
    ----------
    inventory : sequence of pywgrib2_xr.MetaData
    file : str
        GRIB2 file path.
    directory : str, optional
        Directory where to save the inventory.
    """
    if not inventory:
        logger.warning("inventory is empty")
        return
    if directory:
        os.makedirs(directory, exist_ok=True)
        file_inventory = FileMetaData(file, inventory)
    else:
        file_inventory = FileMetaData(None, inventory)
    inv_file = inventory_name(file, directory)
    try:
        if blosc is None:
            with open(inv_file, "wb") as fp:
                pickle.dump(file_inventory, fp)
        else:
            arr = pickle.dumps(file_inventory)
            packed = blosc.compress(
                arr, typesize=8, cname="lz4", shuffle=blosc.BITSHUFFLE
            )
            with open(inv_file, "wb") as fp:
                fp.write(packed)
    except OSError as e:
        logger.error("Cannot save inventory to file {:s}: {!r}".format(inv_file, e))
        # raise


def load_inventory(
    file: str, directory: Optional[str] = None
) -> Union[None, List[MetaData]]:
    """Retrieves inventory from a file.

    Parameters
    ----------
    file : str
        GRIB file path.
    directory : str, optional
        Directory of the inventory file, if not collocated with GRIB2 file.
        Default is None.

    Returns
    -------
    inventory: list
        List of MetaData for all messages in a GRIB2 file. In case of an error,
        None is returned.
    """
    inv_file = inventory_name(file, directory)
    try:
        with open(inv_file, "rb") as fp:
            data = fp.read()
            if blosc is not None:
                data = blosc.decompress(data)
            file_inventory = pickle.loads(data)
            return file_inventory.to_meta(file)
    except OSError as e:
        logger.info("Cannot load inventory from {:s}: {!r}".format(inv_file, e))
    return None


def load_or_make_inventory(
    file: str, directory: Optional[str] = None, save: Optional[bool] = False
) -> Union[None, List[MetaData]]:
    """Returns inventory for a GRIB2 file.

    Parameters
    ----------
    file : str
        GRIB file path.
    directory : str, optional
        Directory of the inventory file, if not collocated with GRIB2 file.
        Default is None.
    save : bool
        Save created inventory, if inventory file does not exist. Default is False.

    Returns
    -------
    inventory: list
        List of MetaData for all messages in a GRIB2 file. In case of an error,
        None is returned.

    See also
    --------
    pywgrib2_xr.load_inventory, pywgrib2_xr.make_inventory, pywgrib2_xr.save_inventory
    """
    inventory = load_inventory(file, directory)
    if inventory:
        return inventory
    inventory = make_inventory(file)
    if inventory and save:
        save_inventory(inventory, file, directory)
    return inventory

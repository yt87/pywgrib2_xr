from collections import defaultdict
from functools import partial
import logging
from typing import (
    Any,
    Callable,
    DefaultDict,
    Dict,
    List,
    NamedTuple,
    Sequence,
    Tuple,
    Union,
    cast,
)

try:
    from numpy.typing import ArrayLike
except ImportError:
    ArrayLike = Any

import numpy as np
from xarray.backends.locks import SerializableLock

from . import UNDEFINED, _Variable, WgribError
from .wgrib2 import MemoryBuffer, wgrib, free_files
from .inventory import MetaData
from .template import Template

logger = logging.getLogger(__name__)

# wgrib2 returns C float arrays
DTYPE = np.dtype("float32")


HeaderIndices = Tuple[int, ...]
FileIndex = DefaultDict[str, Dict[HeaderIndices, str]]  # file -> Dict
FileIndices = DefaultDict[str, FileIndex]  # variable name -> FileIndex

WGRIB2_LOCK = SerializableLock()


class Dataset(NamedTuple):
    dims: Dict[str, int]
    vars: Dict[str, _Variable]
    attrs: Dict[str, Any]


# FIXME: might use https://github.com/roebel/py_find_1st
def find_1st(array, value):
    return np.nonzero(array == value)[0][0]


def build_file_index(
    items: Sequence[MetaData],
    template: Template,
) -> FileIndices:
    file_indices: FileIndices = defaultdict(cast(Callable, partial(defaultdict, dict)))
    for item in (i for i in items if template.item_match(i)):
        varname = template.item_to_varname(item)
        try:
            specs = template.var_specs[varname]
        except KeyError:
            logger.info("Variable {!s} not found in template, skipping".format(varname))
            continue
        time_coord = specs.time_coord
        level_coord = specs.level_coord
        fcst_time = item.end_ft - item.reftime
        header_indices: Tuple[int, ...] = ()
        found = True
        if time_coord in specs.dims:
            try:
                i = find_1st(template.coords[time_coord].data, fcst_time)
                header_indices = (i,)
            except IndexError:
                found = False
        else:
            if template.coords[time_coord].data != fcst_time:
                found = False
        if not found:
            logger.info(
                "Variable {:s} forecast time {!r} not found in template, "
                "skipping".format(varname, fcst_time)
            )
            continue
        if level_coord in specs.dims:
            try:
                i = find_1st(template.coords[level_coord].data, item.level_value)
                header_indices += (i,)
            except IndexError:
                logger.info(
                    "Variable {:s} level {!r} not found in template, "
                    "skipping".format(varname, item.level_value)
                )
                continue
        file_indices[varname][item.file][header_indices] = item.offset
    return file_indices


def expand_item(item: Sequence[Any], shape: Tuple[int, ...]) -> Tuple[List[Any], ...]:
    expanded_item = []
    for i, size in zip(item, shape):
        if isinstance(i, list):
            expanded_item.append(i)
        elif isinstance(i, np.ndarray):
            expanded_item.append(i.tolist())
        elif isinstance(i, slice):
            expanded_item.append(list(range(i.start or 0, i.stop or size, i.step or 1)))
        elif isinstance(i, int):
            expanded_item.append([i])
        else:
            raise TypeError("Unsupported index type {!r}".format(type(i)))
    return tuple(expanded_item)


class OnDiskArray:
    def __init__(
        self,
        varname: str,
        file_index: FileIndex,
        shape: Sequence[int],
        template: Template,
    ) -> None:
        self.varname = varname
        self.file_index = file_index
        self.shape = tuple(shape)
        self.geo_ndim = len(template.grid.dims)
        self.npts = np.prod(shape[-self.geo_ndim :])
        self.missing_value = UNDEFINED  # wgrib2 missing value
        self.dtype = DTYPE

    def __getitem__(self, item: Tuple[Any, ...]) -> ArrayLike:
        assert isinstance(item, tuple), "Item type must be tuple not {!r}".format(
            type(item)
        )
        assert len(item) == len(self.shape), "Item len must be {!r} not {!r}".format(
            len(self.shape), len(item)
        )

        header_item = expand_item(item[: -self.geo_ndim], self.shape)
        array_field_shape = (
            tuple(len(i) for i in header_item) + self.shape[-self.geo_ndim :]
        )
        array_field = np.full(array_field_shape, fill_value=np.nan, dtype=DTYPE)
        datasize = self.npts * array_field.dtype.itemsize
        for file, index in self.file_index.items():
            # Faster, longer code
            def _get_array_indexes():
                for header_indices, offset in index.items():
                    try:
                        afi = [
                            it.index(ix) for it, ix in zip(header_item, header_indices)
                        ]
                        yield afi, offset
                    except ValueError:
                        continue

            try:
                seq_of_array_field_indexes, offsets = zip(*_get_array_indexes())
            except ValueError:
                continue
            inventory = MemoryBuffer()
            inventory.set("\n".join(offsets))
            output = MemoryBuffer()
            args = [
                file,
                "-rewind_init",
                file,
                "-i_file",
                inventory,
                "-rewind_init",
                inventory,
                "-inv",
                "/dev/null",
                "-no_header",
                "-bin",
                output,
            ]
            try:
                wgrib(*args)
                values = output.get("b")
            except WgribError as e:
                logger.error("wgrib2 error: {:s}".format(str(e)))
                output.close()
                continue
            finally:
                inventory.close()
                output.close()
                free_files(file)
            for pos, array_field_indexes in zip(
                range(0, len(values), datasize), seq_of_array_field_indexes
            ):
                chunk = np.frombuffer(values[pos : pos + datasize], dtype=DTYPE)
                array_field.__getitem__(tuple(array_field_indexes)).flat[:] = chunk

        # Slow, shorter code
        # for header_indices, offset in index.items():
        #    try:
        #        array_field_indexes = [
        #            it.index(ix) for it, ix in zip(header_item, header_indices)
        #        ]
        #    except ValueError:
        #        continue
        #    output = MemoryBuffer()
        #    args = [
        #        path,
        #        "-rewind_init",
        #        path,
        #        "-d",
        #        offset,
        #        "-inv",
        #        "/dev/null",
        #        "-no_header",
        #        "-bin",
        #        output,
        #    ]
        #    #print('=========== calling wgrib', path, header_indices, offset)
        #    try:
        #        wgrib(*args)
        #        values = output.get("a")
        #        array_field.__getitem__(tuple(array_field_indexes)).flat[:] = values
        #    except WgribError as e:
        #        logger.error("wgrib2 error: {!r}".format(e))
        #        output.close()
        #        continue
        #    finally:
        #        output.close()
        #        free_files(path)

        array = array_field[(Ellipsis,) + item[-self.geo_ndim :]]
        array[array == self.missing_value] = np.nan
        for i, it in reversed(list(enumerate(item[: -self.geo_ndim]))):
            if isinstance(it, int):
                array = array[(slice(None, None, None),) * i + (0,)]
        return array


def open_dataset(
    items: Sequence[MetaData],
    template: Template,
) -> Union[Dataset, None]:
    dimensions: Dict[str, int] = {}
    variables: Dict[str, _Variable] = {}
    file_indices = build_file_index(items, template)
    if not file_indices:
        logger.warning("No matching data found")
        return Dataset(dimensions, variables, {})
    for name, file_index in file_indices.items():
        var_specs = template.var_specs[name]
        data = OnDiskArray(name, file_index, var_specs.shape, template)
        variables[name] = _Variable(var_specs.dims, data, var_specs.attrs)
        dimensions.update({k: v for k, v in zip(var_specs.dims, var_specs.shape)})
    variables.update(template.coords)
    variables["reftime"] = _Variable(
        # reftime is the same for all items
        (),
        np.array(items[0].reftime),
        {"standard_name": "reference_time"},
    )
    # Projection variable
    variables[template.grid.cfname] = _Variable((), np.array(0), template.grid.attrs)
    attrs = template.attrs.copy()
    attrs["coordinates"] = " ".join(
        tuple(template.coords.keys()) + ("reftime", template.grid.cfname)
    )
    return Dataset(dimensions, variables, attrs)

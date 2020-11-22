#
# modified code from xarray.backends
#
from collections import defaultdict
import os
from typing import Mapping, Optional, Sequence, Union

import numpy as np

from xarray import Variable, conventions
from xarray.core import indexing, dtypes
from xarray.core.concat import concat
from xarray.core.utils import Frozen, FrozenDict, close_on_error
from xarray.backends.common import AbstractDataStore, BackendArray
from xarray.backends.locks import SerializableLock, ensure_lock

from .wgrib2 import free_files, status_open
from .inventory import MetaData, load_or_make_inventory
from .template import Template

WGRIB2_LOCK = SerializableLock()


class Wgrib2ArrayWrapper(BackendArray):
    def __init__(self, datastore, array):
        self.datastore = datastore
        self.shape = array.shape
        self.dtype = array.dtype
        self.array = array

    def _getitem(self, key):
        with self.datastore.lock:
            return self.array[key]

    def __getitem__(self, key):
        return indexing.explicit_indexing_adapter(
            key, self.shape, indexing.IndexingSupport.OUTER, self._getitem
        )


class Wgrib2DataStore(AbstractDataStore):
    def __init__(self, items, template, lock=None):
        from .dataset import open_dataset

        if lock is None:
            lock = WGRIB2_LOCK
        self.lock = ensure_lock(lock)
        self.filenames = [i.file for i in items]
        self.ds = open_dataset(items, template)

    def open_store_variable(self, name, var):
        if isinstance(var.data, np.ndarray):
            data = var.data
        else:
            wrapped_array = Wgrib2ArrayWrapper(self, var.data)
            data = indexing.LazilyOuterIndexedArray(wrapped_array)

        encoding = {"original_shape": var.data.shape, "dtype": var.data.dtype}

        return Variable(var.dims, data, var.attrs, encoding)

    def get_variables(self):
        return FrozenDict(
            (k, self.open_store_variable(k, v)) for k, v in self.ds.vars.items()
        )

    def get_attrs(self):
        return Frozen(self.ds.attrs)

    def get_dimensions(self):
        return Frozen(self.ds.dims)

    def get_encoding(self):
        dims = self.get_dimensions()
        if "reftime" in dims:
            encoding = {"unlimited_dims": "reftime"}
        else:
            encoding = {}
        return encoding

    def close(self):
        free_files(*self.filenames)


class _MultiFileCloser:
    __slots__ = ("file_objs",)

    def __init__(self, file_objs):
        self.file_objs = file_objs

    def close(self):
        for f in self.file_objs:
            f.close()
        # FIXME: remove this after testing.
        status_open()


def _protect_dataset_variables_inplace(dataset, cache):
    for name, variable in dataset.variables.items():
        if name not in variable.dims:
            # no need to protect IndexVariable objects
            data = indexing.CopyOnWriteArray(variable._data)
            if cache:
                data = indexing.MemoryCachedArray(data)
            variable.data = data


def _open_dataset(
    items: Sequence[MetaData],
    template: Template,
    chunks: Union[None, int, Mapping[str, int]],
    cache: Optional[bool],
):

    if cache is None:
        cache = chunks is None

    def maybe_decode_store(store, lock=False):
        ds = conventions.decode_cf(
            store,
            mask_and_scale=False,
            decode_times=False,
            concat_characters=False,
            decode_coords=True,
        )

        _protect_dataset_variables_inplace(ds, cache)

        if chunks is not None:
            from dask.base import tokenize

            reftime = items[0].reftime
            token = tokenize(
                template,
                reftime,
                chunks,
            )
            name_prefix = "open_dataset-%s" % token
            ds2 = ds.chunk(chunks, name_prefix=name_prefix, token=token)
            ds2._file_obj = ds._file_obj
        else:
            ds2 = ds

        return ds2

    store = Wgrib2DataStore(items, template, lock=None)

    with close_on_error(store):
        ds = maybe_decode_store(store)

    # Ensure source filename always stored in dataset object (GH issue #2550)
    if "source" not in ds.encoding:
        ds.encoding["source"] = " ".join([os.path.basename(i.file) for i in items])

    return ds


def open_dataset(
    filenames,
    template,
    chunks=None,
    preprocess=None,
    parallel=False,
    cache=None,
    save=False,
    invdir=None,
):
    """Opens one or more files as a single dataset.

    Parameters
    ----------
    filenames : string or sequence of strings.
        GRIB files to process.
    template : Template.
        Template specifies dataset structure. See :py:func:`pywgrib2_xr.make_template`.
    chunks : int or dict, optional
        Dictionary with keys given by dimension names and values given by chunk sizes.
        In general, these should divide the dimensions of each dataset. If int, chunk
        each dimension by ``chunks``. By default, chunks will be chosen to load entire
        logical dataset into memory at once.
    preprocess : callable, optional.
        If provided, call this function on each dataset prior to concatenation.
        You can find the file names from which each dataset was loaded in
        ``ds.encoding['source']``.
    parallel : bool, optional.
        If True, the open and preprocess steps of this function will be
        performed in parallel using ``dask.delayed``. Default is False.
    cache : bool, optional
        If True, cache data loaded from the underlying datastore in memory as
        NumPy arrays when accessed to avoid reading from the underlying data-
        store multiple times. Defaults to True unless you specify the `chunks`
        argument to use dask, in which case it defaults to False. Does not
        change the behavior of coordinates corresponding to dimensions, which
        always load their data from disk into a ``pandas.Index``.
    save : bool, optional
        Save inventory files. Default is False.
    invdir : str, optional.
        Inventory location. None means inventory files are collocated with
        data files.
    Returns
    -------
    xarray.Dataset - The newly created dataset.
    """
    if isinstance(filenames, str):
        filenames = [filenames]

    if parallel:
        import dask

        # wrap the open_dataset, getattr, and preprocess with delayed
        open_ = dask.delayed(_open_dataset)
        getattr_ = dask.delayed(getattr)
        if preprocess is not None:
            preprocess = dask.delayed(preprocess)
    else:
        open_ = _open_dataset
        getattr_ = getattr

    def combine_files(files):
        # Create list of MetaData items grouped and sorted by reference time
        d = defaultdict(list)
        for file in files:
            inventory = load_or_make_inventory(file, invdir, save=save)
            if not inventory:
                continue
            for i in (i for i in inventory if template.item_match(i)):
                d[i.reftime].append(i)
        return [d[k] for k in sorted(d)]

    filesets = combine_files(filenames)

    if chunks is None and len(filesets) > 1:
        chunks = {}
    open_kwargs = {
        "template": template,
        "chunks": chunks,
        "cache": cache,
    }
    datasets = [open_(items, **open_kwargs) for items in filesets]
    file_objs = [getattr_(ds, "_file_obj") for ds in datasets]

    if preprocess is not None:
        datasets = [preprocess(ds) for ds in datasets]

    if parallel:
        # calling compute here will return the datasets/file_objs lists,
        # the underlying datasets will still be stored as dask arrays
        datasets, file_objs = dask.compute(datasets, file_objs)

    if len(datasets) == 1:
        return datasets[0]

    # Combine all datasets, closing them in case of a ValueError
    try:
        combined = concat(
            datasets,
            dim="reftime",
            compat="override",
            data_vars="minimal",
            coords="minimal",
            fill_value=dtypes.NA,
            join="exact",
        )
    except ValueError:
        for ds in datasets:
            ds.close()
        raise

    combined._file_obj = _MultiFileCloser(file_objs)
    combined.attrs = datasets[0].attrs
    return combined

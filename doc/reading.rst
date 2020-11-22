
Reading GRIB files
==================

The function :py:func:`~pywgrib2_xr.open_dataset` creates a dataset from one
or more files. Mandatory arguments are:

 * one (string) or more (iterable of strings) GRIB files.
 * template created by a call to :py:func:`~pywgrib2_xr.make_template`.
 * location of inventory files, if not collocated with data files. If not specified
   and the inventory cannot be found, it will be created.

Remaining optional arguments: ``chunks``, ``preprocess``, ``parallel`` and ``cache``
are the same as for :py:func:`xarray.open_mfdataset`.
To continue the example from the previous section:

.. ipython:: python

    import glob
    import pywgrib2_xr as pywgrib2

    @suppress
    files = sorted(glob.glob('/mnt/sdc1/grib2/nam.t00z.afwahi??.tm00.grib2'))[:9]
    tmpl = pywgrib2.make_template(files, lambda x: x.varname == 'APCP')
    ds = pywgrib2.open_dataset(files, tmpl)
    ds

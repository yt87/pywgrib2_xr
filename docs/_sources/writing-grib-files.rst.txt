.. _writing_grib_files:

Writing GRIB2 Files
===================

**wgrib2** and consequently **pywgrib2_xr** does not support creating GRIB2 files
"from scratch". Rather, an existing GRIB2 message is used as a template, the newly
created message shares, by default, both metadata and grid values. New field values
can be set via :py:class:`~pywgrib2_xr.RPNRegister`, metadata can be updated with
the help of over 60 commands ``-set_X`` where ``X`` is the parameter to set.
The function :py:func:`~pywgrib2_xr.write_msg` hides implementation details.
See `wgrib2 -set_metadata documentation <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/set_metadata.html>`__
for detailed desctiption of all possible options.

Examples:

  * Modify model issue time, preserve data values:

    .. code-block:: python

        # Add 1 day + 12 hours to date code for each message in input file
        date_inc = timedelta(days=1, hours=12)
        for item in pywgrib2.inv_from_grib(in_file):
            pywgrib2.write_msg(out_file, in_file, item, date=item.end_ft + date_inc)

    The keyword argument ``date=date_str`` is passed to ``wgrib`` as
    ``'set_date', date_str``.

  * Add calculated wind speed at isobaric levels to a GRIB2 file:

    .. code-block:: python

        gribfile = 'gfs_4_20180930_1800_072.grb2'
        windfile = 'wind.grb2'

        def pred_wind_isobaric(item):
            return item.varname in ('UGRD', 'VGRD') and item.level_code == 100

        inv = pywgrib2.load_or_make_inventory(gribfile, save=True)
        tmpl = pywgrib2.make_template(gribfile, pred_wind_isobaric, vertlevels='isobaric')
        ds = pywgrib2.open_dataset(gribfile, tmpl, chunks={'isobaric1': 1})
        uv = ds['UGRD.isobaric'] + 1j * ds['VGRD.isobaric']
        ds['WIND.isobaric'] = np.abs(uv)
        # See https://github.com/pydata/xarray/issues/2609
        ds['WDIR.isobaric'] = (90.0 - xr.ufuncs.angle(uv, deg=True)) % 360.0
        # Not needed in this example
        # ds['WIND.isobaric'].attrs = 
        # ds['WDIR.isobaric'].attrs =
        meta = next((i for i in inv if pred_wind_isobaric(i)))
        for p in ds['WIND.isobaric'].coords['isobaric1'].values:
            level = '{:d} mb'.format(p // 100)
            wspd = ds['WIND.isobaric'].sel(isobaric1=p) 
            wdir = ds['WDIR.isobaric'].sel(isobaric1=p)
            pywgrib2.write_msg(windfile, gribfile, meta, data=wind.values, var='WIND',
                               lev=level, grib_type='same', append=True)
            pywgrib2.write_msg(windfile, gribfile, meta, data=wind.values, var='WDIR',
                               lev=level, grib_type='same', append=True)

    File ``windfile`` may now be concatenated to ``gribfile``. The argument ``chunks`` in
    the call to ``open_dataset`` can be omitted when memory is not a concern.

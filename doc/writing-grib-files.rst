.. _writing_grib_files:

Writing GRIB Files
==================

**wgrib2** and consequently **pywgrib2_xr** does not support creating GRIB files
"from scratch". Rather, an existing GRIB message is used as a template, the newly
created message shares, by default, both metadata and grid values. New field values
can be set via :py:class:`~pywgrib2_xr.RPNRegister`, metadata can be updated with
the help of over 60 commands ``-set_X`` where ``X`` is the parameter to set.
The function :py:func:`~pywgrib2_xr.write_msg` hides implementation details.
Examples:

  * Modify model issue time, preserve data values::

      # Add 1 day + 12 hours to date code for each message in input file
      date_inc = timedelta(days=1, hours=12)
      for item in pywgrib2.inv_from_grib(in_file):
          pywgrib2.write_msg(out_file, in_file, item, date=item.end_ft + date_inc)

    The keyword argument ``date=date_str`` is passed to ``wgrib`` as
    ``'set_date', date_str``.

  * Write data values for the same element, but different level::

      # item is an inventory item for RH at 700 hPa.
      # rh_ave is a numpy array with calculated data.
      level = "surface - 700 mb"
      pywgrib2.write_msg(out_file, in_file, item, data=rh_ave, lev=level)        

See `wgrib2 -set_metadata documentation <https://www.cpc.ncep.noaa.gov/products/wesley/wgrib2/set_metadata.html>`__
for detailed desctiption of all possible options.

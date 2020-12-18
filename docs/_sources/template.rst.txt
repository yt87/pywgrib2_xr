
Template
========

The template defines dataset structure. It holds parameters common to all messages
within the dataset: data origin (from Section 1), geolocation (Section 3), variable
names, optional forecast times and vertical dimensions. To make a template, use
function :py:func:`~pywgrib2_xr.make_template`. The first argument is a GRIB2 file or
a list of files sharing common **reference time**. Other arguments are optional,
if not specified, all messages present in GRIB2 files will be processed.

:py:func:`~pywgrib2_xr.make_template` uses inventory files to get the required metadata.
If those files do not exist, inventory is created by a call to
:py:func:`~pywgrib2_xr.make_inventory`. 

To select subset of variables, specify one or more boolean functions (predicates)
accepting inventory item as the single input argument. A message is selected if any
of the predicates return True. For example, to select temperature and relative
humidity at 2 m, one could write:

.. code-block:: python

  def tmp_2m(item):
      return item.varname == 'TMP' and item.level_str == '2 m above ground'

  def rh_2m(item):
      return item.varname == 'RH' and item.level_str == '2 m above ground'

and call the above as:

.. code-block:: python

    tmpl = pywgrib2.make_template(gribfiles, tmp_2m, rh_2m)

A shorter version:

.. code-block:: python

   tmpl = pywgrib2.make_template(gribfiles, lambda x: x.varname in ('TMP', 'RH') and
                                 x.level_code==103 and x.level_value==2)

The list of all available attributes is :ref:`here <inventory-content>`.

When a data file contains messages for multiple model outputs,
:py:func:`~pywgrib2_xr.make_template` requires argument ``reftime``. The value does
not matter, as long as it is listed in wgrib2 inventory output.

To group several levels into 3-dimensional spacial array, pass: ``vertlevels=levels``

where ``levels`` is a string or a list of strings specifying vertical dimension(s)
to be combined, for example: ``vertlevels='isobaric'``

combines pressure levels. Available levels are ``isobaric``, ``height_asl``,
``height_asl``, ``sigma``, ``hybrid``.

There are more arguments to :py:func:`~pywgrib2_xr.make_template`, refer to the doc
string for explanation. 

To allow variable with the same names in a GRIB2 file, but describing different
physical quantities to coexist within the same dataset, variable name is made
by concatenating ``varname``, ``level_str`` and ``time_str``, sparated by a dot.
Blanks are replaced by an underscore.

``varname`` is what **wgrib2** terms `extended name`, which can be obtained by passing
the option ``-ext_name`` (or ``-pyinv``). Consider:

.. code-block:: console

    wgrib2 albers.grb

.. parsed-literal::

    1:0:d=2009060500:HGT:200 mb:330 hour fcst:ens std dev

.. code-block:: console

    wgrib2 albers.grb -ext_name

.. parsed-literal::

    1:0:HGT.ens_std_dev

The `level` part is taken verbatim from ``level_str``. Without argument 
``vertlevels='isobaric'``, temperature at 500 hPa is coded
as ``TMP.500_mb``. When ``vertlevels`` is specified, variable name is ``TMP.isobaric``.
Compare:

.. code-block:: python

    files = sorted(glob.glob('nam.t00z.afwahi??.tm00.grib2'))
    tmpl = pywgrib2.make_template(files, lambda x: x.varname=='TMP' and
                                  x.level_code==100 and 90000<x.level_value<100000)
    tmpl.var_names

.. parsed-literal::

    ['TMP.925_mb', 'TMP.950_mb', 'TMP.975_mb']

and:

.. code-block:: python

    tmpl = pywgrib2.make_template(files, lambda x: x.varname == 'TMP' and
                                  x.level_code==100 and 90000<x.level_value<100000,
                                  vertlevels='isobaric')
    tmpl.var_names
    tmpl.var_specs['TMP.isobaric'].level_coord
    tmpl.coords['isobaric1'].data

.. parsed-literal::

    ['TMP.isobaric']
    'isobaric1'
    array([97500, 95000, 92500])

Level dimension name is always level name with appended ordinal. Adding the ordinal
allows variables with different number of levels in the same dataset.
  
To illustrate processing of forecast time consider accumulated precipitation in
NAM GRIB2 files:

.. code-block:: console

    for h in 00 03 06 09 12 15 18 24
    do f=nam.t00z.afwahi${h}.tm00.grib2
    echo $f; wgrib2 $f -match APCP
    done

.. parsed-literal::

    nam.t00z.afwahi00.tm00.grib2
    668:18592315:d=2020060300:APCP:surface:0-0 day acc fcst:
    nam.t00z.afwahi03.tm00.grib2
    668:19041947:d=2020060300:APCP:surface:0-3 hour acc fcst:
    nam.t00z.afwahi06.tm00.grib2
    668:19688872:d=2020060300:APCP:surface:0-6 hour acc fcst:
    713:21326599:d=2020060300:APCP:surface:3-6 hour acc fcst:
    nam.t00z.afwahi09.tm00.grib2
    668:20017699:d=2020060300:APCP:surface:0-9 hour acc fcst:
    713:21642149:d=2020060300:APCP:surface:6-9 hour acc fcst:
    nam.t00z.afwahi12.tm00.grib2
    668:20483592:d=2020060300:APCP:surface:0-12 hour acc fcst:
    713:22152393:d=2020060300:APCP:surface:9-12 hour acc fcst:
    nam.t00z.afwahi15.tm00.grib2
    668:20992733:d=2020060300:APCP:surface:12-15 hour acc fcst:
    nam.t00z.afwahi18.tm00.grib2
    668:21264515:d=2020060300:APCP:surface:12-18 hour acc fcst:
    713:23185255:d=2020060300:APCP:surface:15-18 hour acc fcst:
    nam.t00z.afwahi24.tm00.grib2
    668:21199001:d=2020060300:APCP:surface:12-24 hour acc fcst:
    713:23172832:d=2020060300:APCP:surface:21-24 hour acc fcst:
  
The periods are 0 days (or hours, or seconds), 3, 6, 9 and 12 hours. Accumulated
precipitation for those periods must be separate variables. Each of those variables
will have different forecast time dimension:

.. code-block:: python

    tmpl = pywgrib2.make_template(files, lambda x: x.varname == 'APCP')
    tmpl.var_names
    tc9 = tmpl.var_specs['APCP.surface.9_hour_acc'].time_coord
    tmpl.coords[tc9].data
    tc6 = tmpl.var_specs['APCP.surface.6_hour_acc'].time_coord
    tmpl.coords[tc6].data
    tc3 = tmpl.var_specs['APCP.surface.3_hour_acc'].time_coord
    tmpl.coords[tc3].data

.. parsed-literal::

    ['APCP.surface',
     'APCP.surface.12_hour_acc',
     'APCP.surface.3_hour_acc',
     'APCP.surface.6_hour_acc',
     'APCP.surface.9_hour_acc']

    array([datetime.timedelta(seconds=32400),
           datetime.timedelta(seconds=75600)], dtype=object)

    array([datetime.timedelta(seconds=21600),
           datetime.timedelta(seconds=64800)], dtype=object)

    array([datetime.timedelta(seconds=10800),
           datetime.timedelta(seconds=21600),
           datetime.timedelta(seconds=32400),
           datetime.timedelta(seconds=43200),
           datetime.timedelta(seconds=54000),
           datetime.timedelta(seconds=64800),
           datetime.timedelta(seconds=75600), datetime.timedelta(days=1)],
          dtype=object)

Forecast time dimension name is always ``timeN`` where ``N`` is an ordinal. 
:py:func:`~pywgrib2_xr.make_template` searches the inventory attribute ``time_str``
for keywords indicating type of statistical processing
(`Table 4.10 <https://www.nco.ncep.noaa.gov/pmb/docs/grib2/grib2_doc/grib2_table4-10.shtml>`__),
and, if present, calculates period between ``start_ft`` and ``end_ft``. When the period
is 0, the time part is null, otherwise is formed from the processing type and the period.
For example, the string `12-15 hour acc fcst` translates to `3_hour_acc`, while
`12 hour fcst` is ignored. The time coordinate value is always that of ``end_ft``.

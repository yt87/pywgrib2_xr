
Inventory
=========

**wgrib2** has many options to list content of a GRIB2. Those are identified by
a tag ``inv`` in the second column of **wgrib2** help screen. The default short
listing is a sequence of elements separated by a colon:

.. code-block:: console

    wgrib2 hrrrAK.grib2

.. parsed-literal::

    1:0:d=2020021000:VIS:surface:24 hour fcst:
    2:754142:d=2020021000:LCDC:low cloud layer:24 hour fcst:
    3:1212817:d=2020021000:MCDC:middle cloud layer:24 hour fcst:
    4:1569231:d=2020021000:HCDC:high cloud layer:24 hour fcst:
    5:1782227:d=2020021000:TCDC:entire atmosphere:24 hour fcst:
    6:2164301:d=2020021000:HGT:cloud base:24 hour fcst:
    7:3174056:d=2020021000:HGT:cloud ceiling:24 hour fcst:
    8:4445291:d=2020021000:HGT:cloud top:24 hour fcst:

An extended listing is obtained by adding option ``-Match_inv``:

.. code-block:: console

    wgrib2 hrrAK.grib2 -Match_inv

.. parsed-literal::

    1:0:D=20200210000000:VIS:surface:24 hour fcst::VIS:n=1:npts=1193781:var0_2_1_7_19_0:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=0 dec_scale=2 bin_scale=0 nbits=10:vt=2020021100:
    2:754142:D=20200210000000:LCDC:low cloud layer:24 hour fcst::LCDC:n=2:npts=1193781:var0_2_1_7_6_3:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=0 dec_scale=0 bin_scale=-3 nbits=11:vt=2020021100:
    3:1212817:D=20200210000000:MCDC:middle cloud layer:24 hour fcst::MCDC:n=3:npts=1193781:var0_2_1_7_6_4:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=0 dec_scale=0 bin_scale=-3 nbits=11:vt=2020021100:
    4:1569231:D=20200210000000:HCDC:high cloud layer:24 hour fcst::HCDC:n=4:npts=1193781:var0_2_1_7_6_5:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=0 dec_scale=0 bin_scale=-3 nbits=12:vt=2020021100:
    5:1782227:D=20200210000000:TCDC:entire atmosphere:24 hour fcst::TCDC:n=5:npts=1193781:var0_2_1_7_6_1:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=0 dec_scale=0 bin_scale=-3 nbits=10:vt=2020021100:
    6:2164301:D=20200210000000:HGT:cloud base:24 hour fcst::HGT:n=6:npts=1193781:var0_2_1_7_3_5:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=16.8566 dec_scale=0 bin_scale=-3 nbits=18:vt=2020021100:
    7:3174056:D=20200210000000:HGT:cloud ceiling:24 hour fcst::HGT:n=7:npts=1193781:var0_2_1_7_3_5:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=30.9375 dec_scale=0 bin_scale=-3 nbits=19:vt=2020021100:
    8:4445291:D=20200210000000:HGT:cloud top:24 hour fcst::HGT:n=8:npts=1193781:var0_2_1_7_3_5:pdt=0:d=2020021000:start_FT=20200211000000:end_FT=20200211000000:scaling ref=31.1188 dec_scale=0 bin_scale=-3 nbits=19:vt=2020021100:

This type of listing is used to select messages, either implicitly, as shown in
:ref:`Overview <example-1>`, or explicitly, by saving it to an `inventory file`:

.. code-block:: python

    import pywgrib2_xr as pywgrib2 
    from pywgrib2_xr.utils import remotepath

    in_file = remotepath('nam.t12z.awak3d18.tm00.grib2')
    out_file = '/tmp/subset2.grib2'
    inv_file = '/tmp/nam.t12z.awak3d18.tm00.inv'

    pywgrib2.wgrib(in_file, '-inv', inv_file, '-Match_inv')
    match_str = ':(TMP:2 m above ground|[U|V]GRD:10 m above ground):'
    pywgrib2.wgrib(in_file, '-i_file', inv_file, '-inv', '/dev/null',
                   '-match', match_str, '-grib', out_file)
    pywgrib2.free_files(in_file, out_file)

When the GRIB2 files are accessed frequently it makes sense to create permanent
inventory files. Decoding of message metadata is done only once. Subsequent message
selection is done by reading inventory file, which is much faster.

The above inventories can be useful with the low-level interface is used.
**pywgrib2_xr** uses option ``-pyinv`` which is a new feature in wgrib2 v3.0.0:

.. code-block:: console

  wgrib2 nam.t12z.awak3d18.tm00.grib2 -d 1 -pyinv

.. parsed-literal::

  1:0:PRMSL:mean sea level:18 hour fcst:pyinv={'discipline':0,'centre':'7 - US National Weather Service - NCEP (WMC)','subcentre':'0','mastertab':2,'localtab':1,'reftime':'2018-02-20T12:00:00','npts':235025,'nx':553,'ny':425,'gdtnum':20,'gdtmpl':[6,0,0,0,0,0,0,553,425,30000000,187000000,56,60000000,225000000,11250000,11250000,0,64],'long_name':'Pressure Reduced to MSL','units':'Pa','pdt':0,'parmcat':3,'parmnum':1,'start_ft':'2018-02-21T06:00:00','end_ft':'2018-02-21T06:00:00','bot_level_code':101,'bot_level_value':0,'top_level_code':255}

The inventory is a list of :py:class:`~pywgrib2_xr.MetaData`, each element corresponding
to a line like the above. ``MetaData`` contains also path to the GRIB2 file. This warrants
some careful consideration. When GRIB2 files are accessed via NFS, the mount points do
not have to be the same. Therefore the ``file`` attribute has to be filled when the 
inventory is read from a file.

Inventory is created by a call to :py:func:`~pywgrib2_xr.make_inventory`,
It can be saved to a file by :py:func:`~pywgrib2_xr.save_inventory`. 
To retrieve previously saved inventory, use :py:func:`~pywgrib2_xr.load_inventory`.
Another function :py:func:`~pywgrib2_xr.load_or_make_inventory` combines 
functionality of the three functions in one call. If an inventory exists, it is
retrieved from a file, otherwise created, and optionally saved.

.. code-block:: python

    inv = pywgrib2.make_inventory(in_file)
    pywgrib2.save_inventory(inv, in_file)

Note that the second argument to ``save_inventory()`` is path to the GRIB2 file. 
The inventory file name is created by the function. In this example the inventory is
written to the same location as the GRIB2 file, the file name is that of GRIB2 file
with the suffix ``.binv`` (`Blosc`-compressed inventory). If the GRIB2 file resides
on a read only medium, the inventory must be saved somewhere else.
``save_inventory()`` accepts argument ``directory`` to specify location of
the output file. 

To handle archives with a tree structure, when GRIB2 file names are not unique,
inventory file name is a hash of the path to the GRIB2 file. To illustrate
the concept, assume that the archive is grouped by date.

.. code-block:: console

    ls -l /archive/*

.. parsed-literal::

    /archive/20200912:
    total 38572
    -rw-r--r-- 1 root root 39496058 Sep 12 22:25 nam.t00z.afwaca00.tm00.grib2
    /archive/20200913:
    total 39456
    -rw-r--r-- 1 root root 40401894 Sep 13 22:29 nam.t00z.afwaca00.tm00.grib2

One can create private inventory in ``/tmp/nam`` and access it as follows: 

.. code-block:: python

    import glob
    import pywgrib2_xr as pywgrib2

    gribfiles = glob.glob('/archive/*/*.grib2')
    for file in gribfiles:
        pywgrib2.save_inventory(pywgrib2.make_inventory(file), file, directory='/tmp/nam')
    # Retrieve saved inventory for 13 of September
    inv = pywgrib2.load_inventory('/archive/20200913/nam.t00z.afwaca00.tm00.grib2',
                                  directory='/tmp/nam')
    str(inv).split('\n')[:3]

The inventory files are blosc-compressed pickles. Compression saves both space
(~8 ratio) and time (~15% on write):

.. code-block:: console

    ls /tmp/nam

.. parsed-literal::

    19764fbe34d658b7e1ec1126d31d2737.binv  388fbfdf6e3f866d1b1f182bc795aab4.binv

**pywgrib2_xr** provides script :ref:`pywgrib2 <pywgrib2>` that can list content
of an inventory file.

.. _inventory-content:

Internally, inventory is saves a a class with the following attributes::

  * file: str
  * offset: str
  * varname: str
  * level_str: str
  * time_str: str
  * discipline: int
  * centre: str
  * subcentre: str
  * mastertab: int
  * localtab: int
  * long_name: str
  * units: str
  * pdt: int
  * parmcat: int
  * parmnum: int
  * bot_level_code: int
  * bot_level_value: float
  * top_level_code: int
  * top_level_value: Optional[float]
  * reftime: datetime
  * start_ft: datetime
  * end_ft: datetime
  * npts: int
  * nx: int
  * ny: int
  * gdtnum: int
  * gdtmpl: List[int]

Note that ``reftime``, ``start_ft`` and ``end_ft`` are decoded to
``datetime.datetime``.  Also, ``bot_level_value`` and ``top_level_value`` are scaled.
The latter might be missing if ``top_level_code`` is set to 255, i.e. for single
surface. As a shortcut, ``bot_level_code`` and ``bot_level_value`` can be accessed
as ``level_code`` and ``level_value``.


from contextlib import suppress
from inspect import cleandoc
import os

import xarray as xr

from pywgrib2_xr.inventory import inventory_name, load_inventory
from pywgrib2_xr.script import main

from . import path_to, paths_to


def test_to_nc(tmpdir):
    files = paths_to("CMC_glb_TMP_ISBL_1000_ps30km_2020012512_*.grib2")
    tmplfile = os.fspath(tmpdir / "foo.template")
    ncfile = os.fspath(tmpdir / "foo.nc")
    args = ["template", "-o", tmplfile]
    args.extend(files)
    main(args)
    args = ["to_nc", "-T", tmplfile, "-o", ncfile]
    args.extend(files)
    main(args)
    ds = xr.open_dataset(ncfile, engine="netcdf4")

    assert "TMP.1000_mb" in ds.data_vars
    assert ds.coords["time1"].size == len(files)


def test_to_zarr(tmpdir):
    files = paths_to("CMC_glb_TMP_ISBL_*_ps30km_2020012512_P000.grib2")
    tmplfile = os.fspath(tmpdir / "foo.template")
    zstore = os.fspath(tmpdir / "foo.zarr")
    args = ["template", "-v", "isobaric", "-o", tmplfile]
    args.extend(files)
    main(args)
    args = ["to_zarr", "-T", tmplfile, "-o", zstore]
    args.extend(files)
    main(args)
    ds = xr.open_zarr(zstore)

    assert "TMP.isobaric" in ds.data_vars
    assert ds.coords["isobaric1"].size == len(files)


def test_make_inv_default(capsys):
    file = path_to("CMC_glb_WIND_TGL_10_ps30km_2020012512_P003.grib2")
    expected_inventory = cleandoc(
        """
[<MetaData>
           file: '{:s}'
         offset: '1:0'
        varname: 'UGRD'
      level_str: '10 m above ground'
       time_str: '3 hour fcst'
     discipline: 0
         centre: '54 - Canadian Meteorological Service - Montreal (RSMC)'
      subcentre: '0'
      mastertab: 4
       localtab: 0
      long_name: 'U-Component of Wind'
          units: 'm/s'
            pdt: 0
        parmcat: 2
        parmnum: 2
 bot_level_code: 103
bot_level_value: 10
 top_level_code: 255
top_level_value: None
        reftime: datetime.datetime(2020, 1, 25, 12, 0)
       start_ft: datetime.datetime(2020, 1, 25, 15, 0)
         end_ft: datetime.datetime(2020, 1, 25, 15, 0)
           npts: 49400
             nx: 247
             ny: 200
         gdtnum: 20
         gdtmpl: [6, 255, -1, 255, -1, 255, -1, 247, 200, 32549114, 225385728, 8, 60000000, 249000000, 30000000, 30000000, 0, 64], <MetaData>
           file: '{:s}'
         offset: '2:28085'
        varname: 'VGRD'
      level_str: '10 m above ground'
       time_str: '3 hour fcst'
     discipline: 0
         centre: '54 - Canadian Meteorological Service - Montreal (RSMC)'
      subcentre: '0'
      mastertab: 4
       localtab: 0
      long_name: 'V-Component of Wind'
          units: 'm/s'
            pdt: 0
        parmcat: 2
        parmnum: 3
 bot_level_code: 103
bot_level_value: 10
 top_level_code: 255
top_level_value: None
        reftime: datetime.datetime(2020, 1, 25, 12, 0)
       start_ft: datetime.datetime(2020, 1, 25, 15, 0)
         end_ft: datetime.datetime(2020, 1, 25, 15, 0)
           npts: 49400
             nx: 247
             ny: 200
         gdtnum: 20
         gdtmpl: [6, 255, -1, 255, -1, 255, -1, 247, 200, 32549114, 225385728, 8, 60000000, 249000000, 30000000, 30000000, 0, 64]]
    """.format(
            file, file
        )
    ).strip()

    expected_capture = cleandoc(
        """
<FileMetaData> {:s}
1:0|UGRD|10 m above ground|3 hour fcst|2020-01-25 12:00:00
2:28085|VGRD|10 m above ground|3 hour fcst|2020-01-25 12:00:00
    """.format(
            file
        )
    ).strip()

    args = ["make_inv", file]
    main(args)
    inventory = load_inventory(file)

    args = ["cat_inv", file]
    main(args)

    captured = capsys.readouterr()

    inv_file = inventory_name(file)
    with suppress(OSError):
        os.unlink(inv_file)

    assert str(inventory) == expected_inventory
    assert captured.out.strip() == expected_capture


def test_make_inv_hash(capsys, tmpdir):
    file = path_to("CMC_glb_APCP_SFC_0_ps30km_2020012500_P003.grib2")
    expected = cleandoc(
        """
<FileMetaData> {:s}
1:0|APCP|surface|0-3 hour acc fcst|2020-01-25 00:00:00
    """.format(
            file
        )
    ).strip()

    args = ["make_inv", "-i", tmpdir, "-p", file]
    main(args)
    inv_file = inventory_name(file, tmpdir)
    args = ["cat_hash", inv_file]
    main(args)
    captured = capsys.readouterr()

    assert captured.out.strip() == expected

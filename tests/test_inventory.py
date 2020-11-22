import datetime
import os
import re

import pytest

from pywgrib2_xr.inventory import (
    MetaData,
    FileMetaData,
    make_inventory,
    save_inventory,
    load_inventory,
    inventory_name,
    item_match,
)

from . import path_to


grib_file = "CMC_geps-prob_TEMP_TGL_2m_latlon0p5x0p5_2020012400_P012_all-products.grib2"


@pytest.fixture(scope="module")
def geps_inventory():
    return make_inventory(path_to(grib_file))


def test_inventory_entry(geps_inventory):
    expected = """<MetaData>
           file: '{:s}'
         offset: '9:1365319'
        varname: 'TMP.max_all_members'
      level_str: '2 m above ground'
       time_str: '12 hour fcst'
     discipline: 0
         centre: '54 - Canadian Meteorological Service - Montreal (RSMC)'
      subcentre: '0'
      mastertab: 4
       localtab: 0
      long_name: 'Temperature'
          units: 'K'
            pdt: 2
        parmcat: 0
        parmnum: 0
 bot_level_code: 103
bot_level_value: 2
 top_level_code: 255
top_level_value: None
        reftime: datetime.datetime(2020, 1, 24, 0, 0)
       start_ft: datetime.datetime(2020, 1, 24, 12, 0)
         end_ft: datetime.datetime(2020, 1, 24, 12, 0)
           npts: 259560
             nx: 721
             ny: 360
         gdtnum: 0
         gdtmpl: [6, 0, 0, 0, 0, 0, 0, 721, 360, 0, 0, -90000000, 180000000, 48, 89500000, 180000000, 500000, 500000, 64]""".format(
        path_to(grib_file)
    )
    assert len(geps_inventory) == 9
    assert str(geps_inventory[8]) == expected


def test_file_inventory(geps_inventory):
    file = path_to(grib_file)
    expected = """<FileMetaData> {:s}
1:0|TMP.10%_level|2 m above ground|12 hour fcst|2020-01-24 00:00:00
2:172157|TMP.25%_level|2 m above ground|12 hour fcst|2020-01-24 00:00:00
3:338201|TMP.50%_level|2 m above ground|12 hour fcst|2020-01-24 00:00:00
4:500321|TMP.75%_level|2 m above ground|12 hour fcst|2020-01-24 00:00:00
5:663082|TMP.90%_level|2 m above ground|12 hour fcst|2020-01-24 00:00:00
6:828571|TMP.ens_spread|2 m above ground|12 hour fcst|2020-01-24 00:00:00
7:1035301|TMP.ens_mean|2 m above ground|12 hour fcst|2020-01-24 00:00:00
8:1186177|TMP.min_all_members|2 m above ground|12 hour fcst|2020-01-24 00:00:00
9:1365319|TMP.max_all_members|2 m above ground|12 hour fcst|2020-01-24 00:00:00
""".format(
        file
    )

    file_meta = FileMetaData(file, geps_inventory)
    assert str(file_meta) == expected.strip()


def test_search_inventory_one(geps_inventory):
    def predicate(x):
        return x.varname == "TMP.max_all_members"

    d = dict(
        file=path_to(grib_file),
        offset="9:1365319",
        varname="TMP.max_all_members",
        level_str="2 m above ground",
        time_str="12 hour fcst",
        discipline=0,
        centre="54 - Canadian Meteorological Service - Montreal (RSMC)",
        subcentre="0",
        mastertab=4,
        localtab=0,
        long_name="Temperature",
        units="K",
        pdt=2,
        parmcat=0,
        parmnum=0,
        bot_level_code=103,
        bot_level_value=2,
        top_level_code=255,
        top_level_value=None,
        reftime=datetime.datetime(2020, 1, 24, 0, 0),
        start_ft=datetime.datetime(2020, 1, 24, 12, 0),
        end_ft=datetime.datetime(2020, 1, 24, 12, 0),
        npts=259560,
        nx=721,
        ny=360,
        gdtnum=0,
        gdtmpl=[
            6,
            0,
            0,
            0,
            0,
            0,
            0,
            721,
            360,
            0,
            0,
            -90000000,
            180000000,
            48,
            89500000,
            180000000,
            500000,
            500000,
            64,
        ],
    )
    expected = MetaData(**d)

    matched_items = [x for x in geps_inventory if item_match(x, [predicate])]

    assert len(matched_items) == 1
    assert matched_items[0] == expected


def test_inventory_reftime():
    gribfile = path_to("CMC_glb_TMP_ISBL_1000_ps30km_P000.grib2")

    reftime = datetime.datetime.strptime("2020012512", "%Y%m%d%H")
    inventory = make_inventory(gribfile)
    matched_items = [
        x for x in inventory if item_match(x, [lambda x: x.reftime == reftime])
    ]

    assert len(matched_items) == 1


def test_search_inventory_many(geps_inventory):
    def m(x):
        return re.match(r"TMP.\d+%_level", x.varname)

    matched_items = [x for x in geps_inventory if m(x)]
    assert len(matched_items) == 5


@pytest.mark.parametrize(
    "directory",
    [pytest.param(None, id="default"), pytest.param("/tmp/test_pywgrib2", id="hash")],
)
def test_save_inventory(directory):
    gribfile = path_to("CMC_glb_ps30km_2020012512.grib2")
    if directory:
        os.makedirs(directory, exist_ok=True)

    inventory = make_inventory(gribfile)
    assert inventory is not None

    save_inventory(inventory, gribfile, directory)
    inventory_file = inventory_name(gribfile, directory)
    inventory_saved = load_inventory(gribfile, directory)

    os.unlink(inventory_file)
    if directory:
        os.rmdir(directory)

    assert inventory_saved == inventory

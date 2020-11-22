import pytest

from pywgrib2_xr import __version__
from pywgrib2_xr.inventory import load_or_make_inventory
from pywgrib2_xr.dataset import open_dataset
from pywgrib2_xr.template import make_template

from . import path_to, paths_to


@pytest.fixture(scope="module")
def filepaths():
    return paths_to("CMC_glb_TMP_ISBL_*_2020012500_*.grib2")


@pytest.fixture(scope="function")
def template(filepaths, tmpdir):
    return make_template(filepaths, vertlevels="isobaric", save=False, invdir=tmpdir)


def test_open_dataset(filepaths, template, tmpdir):
    expected_dims = {
        "time1": 3,
        "isobaric1": 3,
        "y": 200,
        "x": 247,
    }
    expected_vars = set(
        [
            "TMP.isobaric",
            "x",
            "y",
            "longitude",
            "latitude",
            "isobaric1",
            "time1",
            "reftime",
            "polar_stereographic",
        ]
    )
    expected_attrs = {
        "Projection": "polar_stereographic",
        "Originating centre": "54 - Canadian Meteorological Service - Montreal (RSMC)",
        "Originating subcentre": "0",
        "coordinates": "longitude latitude x y isobaric1 time1 reftime polar_stereographic",
        "History": "Created by pywgrib2_xr-{:s}".format(__version__),
    }

    metadata = [i for p in filepaths for i in load_or_make_inventory(p, tmpdir)]
    ds = open_dataset(metadata, template)

    assert ds.dims == expected_dims
    assert set(ds.vars.keys()) == expected_vars
    assert ds.attrs == expected_attrs


def test_open_dataset_empty(template, tmpdir):
    paths = [path_to("CMC_glb_APCP_SFC_0_ps30km_2020012500_P003.grib2")]

    metadata = [i for p in paths for i in load_or_make_inventory(p, tmpdir)]
    ds = open_dataset(metadata, template)

    assert ds.dims == {} and ds.vars == {}

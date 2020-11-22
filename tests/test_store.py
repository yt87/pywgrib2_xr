import numpy as np
import pytest

from pywgrib2_xr.xarray_store import open_dataset
from pywgrib2_xr.inventory import make_inventory, save_inventory
from pywgrib2_xr.template import make_template

from . import assert_dict_equal, path_to, paths_to


@pytest.fixture(scope="module")
def filepaths():
    return paths_to("CMC_glb_TMP_ISBL_*_2020012500_*.grib2")


@pytest.fixture(scope="function")
def template(filepaths, tmpdir):
    return make_template(filepaths, vertlevels=["isobaric"], save=True, invdir=tmpdir)


def test_xarray_open_dataset(template, tmpdir):
    expected_projection = "polar_stereographic"
    expected_variables = set(["TMP.isobaric"])
    expected_coords = set(
        [
            "x",
            "y",
            "polar_stereographic",
            "isobaric1",
            "time1",
            "longitude",
            "latitude",
            "reftime",
        ]
    )
    expected_projection_attrs = {
        "grid_mapping_name": "polar_stereographic",
        "straight_vertical_longitude_from_pole": 249.0,
        "standard_parallel": 60.0,
        "latitude_of_projection_origin": 90,
        "code": 6,
        "shape": "sphere",
        "earth_radius": 6371229.0,
        "GRIB_gdtnum": 20,
        "GRIB_gdtmpl": np.array(
            [
                6,
                255,
                -1,
                255,
                -1,
                255,
                -1,
                247,
                200,
                32549114,
                225385728,
                8,
                60000000,
                249000000,
                30000000,
                30000000,
                0,
                64,
            ],
            dtype=np.int32,
        ),
        "GRIB_Npts": 247 * 200,
        "GRIB_Nx": 247,
        "GRIB_Ny": 200,
        "GRIB_La1": 32.549113999999996,
        "GRIB_Lo1": 225.385728,
        "GRIB_winds": "grid",
        "GRIB_LaD": 60.0,
        "GRIB_LoV": 249.0,
        "GRIB_Dx": 30000.0,
        "GRIB_Dy": 30000.0,
        "GRIB_LaO": 90.0,
    }

    files = paths_to("CMC_glb_TMP_ISBL_*_2020012512_*.grib2")
    for file in files:
        inventory = make_inventory(file)
        save_inventory(inventory, file, tmpdir)

    ds = open_dataset(files, template, invdir=tmpdir)

    assert set(ds.data_vars.keys()) == expected_variables
    assert set(ds.coords.keys()) == expected_coords
    assert ds.attrs["Projection"] == expected_projection
    assert_dict_equal(ds[expected_projection].attrs, expected_projection_attrs)


def test_xarray_open_dataset_empty(template, tmpdir):
    file = path_to("CMC_glb_APCP_SFC_0_ps30km_2020012500_P003.grib2")

    ds = open_dataset(file, template, invdir=tmpdir)

    assert ds.dims == {} and ds.data_vars == {}


# dask 2.9.2 needs a patch: see https://github.com/dask/dask/pull/5852
def test_xarray_open_dataset_dims(template, tmpdir):
    expected_dims = {
        "isobaric1": 3,
        "reftime": 2,
        "time1": 3,
        "x": 247,
        "y": 200,
    }

    files = paths_to("CMC_glb_TMP_ISBL_*_20200125*.grib2")
    for file in files:
        inventory = make_inventory(file)
        save_inventory(inventory, file, tmpdir)
    ds = open_dataset(files, template, invdir=tmpdir)

    assert ds.dims == expected_dims


def test_xarray_open_dataset_gdas(tmpdir):
    expected_dims = {
        "reftime": 2,
        "time1": 7,
        "longitude": 192,
        "latitude": 94,
    }

    file = path_to("gdas_tmp2m.grib2")
    template = make_template(file, reftime="2020-02-29T00", save=True, invdir=tmpdir)
    ds = open_dataset(file, template, invdir=tmpdir)

    assert ds.dims == expected_dims

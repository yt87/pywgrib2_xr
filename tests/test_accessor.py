# from contextlib import suppress
import numpy as np

from pywgrib2_xr import UNDEFINED
from pywgrib2_xr.template import make_template
from pywgrib2_xr.grids import Point, grid_fromstring
from pywgrib2_xr.xarray_store import open_dataset

from . import path_to


def array_from_text(file):
    def fill_nan(a):
        m = np.isclose(a, UNDEFINED)
        a[m] = np.nan
        return a

    with open(file) as fp:
        s = fp.read()
    line, rest = s.split("\n", 1)
    nx, ny = [int(_) for _ in line.split()]
    return [
        fill_nan(np.fromstring(chunk, sep="\n")).reshape(ny, nx)
        for chunk in rest.split(line)
    ]


def test_dataset_winds():
    gribfile = path_to("CMC_glb_WIND_TGL_10_ps30km_2020012512_P003.grib2")
    textfile = gribfile.replace(".grib2", ".text")
    expected_u, expected_v = array_from_text(textfile)

    template = make_template(gribfile)
    ds = open_dataset(gribfile, template)
    ds2 = ds.wgrib2.winds("earth")

    assert np.allclose(
        ds2["UGRD.10_m_above_ground"].values, expected_u, rtol=2.0e-2, atol=5e-2
    )
    assert np.allclose(
        ds2["VGRD.10_m_above_ground"].values, expected_v, rtol=2.0e-2, atol=5e-2
    )
    assert ds2.wgrib2.get_grid().params["GRIB_winds"] == "earth"


def test_dataset_location():
    # wgrib2 -ijlat 10 30 -ijlat 130 92
    lon = [224.353273, 270.247763]
    lat = [39.466247, 57.40005]
    gribfiles = [
        path_to("CMC_glb_WIND_TGL_10_ps30km_2020012512_P003.grib2"),
        path_to("CMC_glb_TMP_ISBL_1000_ps30km_2020012512_P003.grib2"),
    ]
    expected_tmp = [285.905, 265.28]
    expected_uwind = [3.2496, 2.0557]
    expected_vwind = [-0.8308, 3.2671]

    template = make_template(gribfiles)
    ds = open_dataset(gribfiles, template)
    point = Point(lon, lat)
    ds2 = ds.wgrib2.location(point)

    assert np.allclose(
        ds2["UGRD.10_m_above_ground"].values,
        expected_uwind,
        rtol=1.0e-2,
        atol=5e-2,
    )
    assert np.allclose(
        ds2["VGRD.10_m_above_ground"].values,
        expected_vwind,
        rtol=1.0e-2,
        atol=5e-2,
    )
    assert np.allclose(ds2["TMP.1000_mb"].values, expected_tmp, rtol=1.0e-2, atol=5e-2)
    assert ds2.attrs["Projection"] == "points"


def test_dataset_grid():
    grid = grid_fromstring("nps:210:60 184.359:97:47625 42.085:69:47625", winds="grid")
    gribfiles = [
        path_to("CMC_glb_WIND_TGL_10_ps30km_2020012512_P003.grib2"),
        path_to("CMC_glb_TMP_ISBL_1000_ps30km_2020012512_P003.grib2"),
    ]
    textfile = path_to("ak214.text")
    expected_uwind, expected_vwind, expected_tmp = array_from_text(textfile)

    template = make_template(gribfiles)
    ds = open_dataset(gribfiles, template)
    ds2 = ds.wgrib2.grid(grid, iptype="bilinear")

    kwargs = dict(rtol=1.0e-2, atol=5e-2, equal_nan=True)
    assert np.allclose(ds2["TMP.1000_mb"].values, expected_tmp, **kwargs)
    assert np.allclose(ds2["UGRD.10_m_above_ground"].values, expected_uwind, **kwargs)
    assert np.allclose(ds2["VGRD.10_m_above_ground"].values, expected_vwind, **kwargs)

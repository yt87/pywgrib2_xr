from pywgrib2_xr.grids import (
    GDTNum,
    GridLatLon,
    GridRotLatLon,
    GridMercator,
    GridPolarStereo,
    GridLambertConformal,
    GridGaussian,
    GridSpaceView,
    grid_fromstring,
)

from . import assert_dict_equal

gdtmpl_latlon = [
    6,
    255,
    -1,
    255,
    -1,
    255,
    -1,
    720,
    361,
    0,
    -1,
    -90000000,
    0,
    48,
    90000000,
    359500000,
    500000,
    500000,
    64,
]
params_latlon = {
    "GRIB_gdtnum": GDTNum.LATLON,
    "GRIB_gdtmpl": gdtmpl_latlon,
    "GRIB_Npts": 259920,
    "GRIB_Ni": 720,
    "GRIB_Nj": 361,
    "GRIB_La1": -90.0,
    "GRIB_Lo1": 0.0,
    "GRIB_La2": 90.0,
    "GRIB_Lo2": 359.5,
    "GRIB_winds": "earth",
    "GRIB_Di": 0.5,
    "GRIB_Dj": 0.5,
}

gdtmpl_rot_latlon = [
    6,
    255,
    -1,
    255,
    -1,
    255,
    -1,
    1102,
    1076,
    0,
    -1,
    -48510002,
    297422769,
    56,
    48240002,
    36512780,
    90000,
    90000,
    64,
    -31758312,
    267597031,
    0,
]
params_rot_latlon = {
    "GRIB_gdtnum": GDTNum.ROT_LATLON,
    "GRIB_gdtmpl": gdtmpl_rot_latlon,
    "GRIB_Npts": 1102 * 1076,
    "GRIB_Ni": 1102,
    "GRIB_Nj": 1076,
    "GRIB_La1": -48.510002,
    "GRIB_Lo1": 297.422769,
    "GRIB_La2": 48.240002,
    "GRIB_Lo2": 36.512780,
    "GRIB_winds": "grid",
    "GRIB_Di": 0.09,
    "GRIB_Dj": 0.09,
    "GRIB_LaSP": -31.758312,
    "GRIB_LoSP": 267.597031,
    "GRIB_Rot": 0,
}

gdtmpl_mercator = [
    6,
    255,
    -1,
    255,
    -1,
    255,
    -1,
    321,
    225,
    18073000,
    198475000,
    56,
    20000000,
    23088000,
    206131000,
    64,
    0,
    2500000,
    2500000,
]
params_mercator = {
    "GRIB_gdtnum": GDTNum.MERCATOR,
    "GRIB_gdtmpl": gdtmpl_mercator,
    "GRIB_winds": "grid",
    "GRIB_Npts": 72225,
    "GRIB_Ni": 321,
    "GRIB_Nj": 225,
    "GRIB_La1": 18.073,
    "GRIB_Lo1": 198.475,
    "GRIB_LaD": 20.0,
    "GRIB_La2": 23.088,
    "GRIB_Lo2": 206.131,
    "GRIB_Di": 2500.0,
    "GRIB_Dj": 2500.0,
}

gdtmpl_polar_stereo = [
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
    56,
    60000000,
    249000000,
    30000000,
    30000000,
    0,
    64,
]
params_polar_stereo = {
    "GRIB_gdtnum": GDTNum.POLAR_STEREO,
    "GRIB_gdtmpl": gdtmpl_polar_stereo,
    "GRIB_Npts": 247 * 200,
    "GRIB_Nx": 247,
    "GRIB_Ny": 200,
    "GRIB_La1": 32.549114,
    "GRIB_Lo1": 225.385728,
    "GRIB_winds": "grid",
    "GRIB_LaD": 60.0,
    "GRIB_LoV": 249.0,
    "GRIB_LaO": 90.0,
    "GRIB_Dx": 30000.0,
    "GRIB_Dy": 30000.0,
}

gdtmpl_lambert_conformal = [
    6,
    255,
    -1,
    255,
    -1,
    255,
    -1,
    349,
    277,
    1000000,
    214500000,
    56,
    50000000,
    253000000,
    32463000,
    32463000,
    0,
    64,
    50000000,
    50000000,
    -90000000,
    0,
]
params_lambert_conformal = {
    "GRIB_gdtnum": GDTNum.LAMBERT_CONFORMAL,
    "GRIB_gdtmpl": gdtmpl_lambert_conformal,
    "GRIB_Npts": 349 * 277,
    "GRIB_Nx": 349,
    "GRIB_Ny": 277,
    "GRIB_La1": 1.0,
    "GRIB_Lo1": 214.5,
    "GRIB_winds": "grid",
    "GRIB_LaD": 50.0,
    "GRIB_LoV": 253.0,
    "GRIB_Dx": 32463.0,
    "GRIB_Dy": 32463.0,
    "GRIB_Latin1": 50.0,
    "GRIB_Latin2": 50.0,
    "GRIB_LaSP": -90.0,
    "GRIB_LoSP": 0.0,
}

gdtmpl_gaussian = [
    6,
    255,
    -1,
    255,
    -1,
    255,
    -1,
    3072,
    1536,
    0,
    -1,
    -89910324,
    0,
    48,
    89910324,
    359882813,
    117188,
    768,
    64,
]
params_gaussian = {
    "GRIB_gdtnum": GDTNum.GAUSSIAN,
    "GRIB_gdtmpl": gdtmpl_gaussian,
    "GRIB_Npts": 3072 * 1536,
    "GRIB_Ni": 3072,
    "GRIB_Nj": 1536,
    "GRIB_La1": -89.910324,
    "GRIB_Lo1": 0.0,
    "GRIB_La2": 89.910324,
    "GRIB_Lo2": 359.882813,
    "GRIB_Di": 0.117188,
    "GRIB_winds": "earth",
    "GRIB_N": 768,
}

gdtmpl_space_view = [
    3,
    255,
    -1,
    4,
    63781400,
    4,
    63567550,
    3712,
    3712,
    0,
    41000000,
    0,
    3622,
    3610,
    1856000,
    1856000,
    64,
    0,
    6610700,
    0,
    0,
]
params_space_view = {
    "GRIB_gdtnum": GDTNum.SPACE_VIEW,
    "GRIB_gdtmpl": gdtmpl_space_view,
    "GRIB_Npts": 3712 * 3712,
    "GRIB_Nx": 3712,
    "GRIB_Ny": 3712,
    "GRIB_Lap": 0.0,
    "GRIB_Lop": 41.0,
    "GRIB_Dx": 3622,
    "GRIB_Dy": 3610,
    "GRIB_Xp": 1856.0,
    "GRIB_Yp": 1856.0,
    "GRIB_OriAngle": 0.0,
    "GRIB_Nr": 6.6107,
    "GRIB_Xo": 0,
    "GRIB_Yo": 0,
}


def test_grids_latlon_gds():
    expected_globe = {"shape": "sphere", "earth_radius": 6371229.0, "code": 6}

    grid = GridLatLon(gdtmpl_latlon)
    assert_dict_equal(grid.params, params_latlon)
    assert_dict_equal(grid.globe, expected_globe)


def test_grids_latlon_fromstring():
    s = "latlon 0:720:0.5 -90:361:0.5"

    grid = grid_fromstring(s, winds="earth")
    assert grid.gdtnum == GDTNum.LATLON
    assert_dict_equal(grid.params, params_latlon)


def test_grids_rot_latlon_gds():
    grid = GridRotLatLon(gdtmpl_rot_latlon)
    assert_dict_equal(grid.params, params_rot_latlon)


def test_grids_rot_latlon_fromstring():
    s = "rot-ll:267.597031:-31.758312:0 297.422769:1102:0.09 -48.510002:1076:0.09"

    grid = grid_fromstring(s, winds="grid")
    assert grid.gdtnum == GDTNum.ROT_LATLON
    assert_dict_equal(grid.params, params_rot_latlon)


def test_grids_mercator_gds():
    grid = GridMercator(gdtmpl_mercator)
    assert_dict_equal(grid.params, params_mercator)


def test_grids_mercator_fromstring():
    s = "mercator:20.0 198.475:321:2500:206.131 18.073:225:2500:23.088"

    grid = grid_fromstring(s)
    assert grid.gdtnum == GDTNum.MERCATOR
    assert_dict_equal(grid.params, params_mercator)


def test_grids_polar_stereo_gds():
    grid = GridPolarStereo(gdtmpl_polar_stereo)
    assert_dict_equal(grid.params, params_polar_stereo)


def test_grids_polar_stereo_fromstring():
    s = "nps:249.0:60.0 225.385728:247:30000 32.549114:200:30000"

    grid = grid_fromstring(s, winds="grid")
    assert grid.gdtnum == GDTNum.POLAR_STEREO
    assert_dict_equal(grid.params, params_polar_stereo)


def test_grids_lambert_conformal_gds():
    grid = GridLambertConformal(gdtmpl_lambert_conformal)
    assert_dict_equal(grid.params, params_lambert_conformal)


def test_grids_lambert_conformal_fromstring():
    s = "lambert:253.0:50.0:50.0:50.0 214.5:349:32463 1.0:277:32463"

    grid = grid_fromstring(s, winds="grid")
    assert grid.gdtnum == GDTNum.LAMBERT_CONFORMAL
    assert_dict_equal(grid.params, params_lambert_conformal)


def test_grids_gaussian_gds():
    grid = GridGaussian(gdtmpl_gaussian)
    assert_dict_equal(grid.params, params_gaussian)


def test_grids_gaussian_fromstring():
    s = "gaussian 0.0:3072:0.117188 -89.910324:1536"

    grid = grid_fromstring(s, winds="earth")
    assert grid.gdtnum == GDTNum.GAUSSIAN
    assert_dict_equal(grid.params, params_gaussian)


def test_grids_space_view():
    expected_globe = {
        "shape": "ellipsoid",
        "semi_major_axis": 6378140.0,
        "semi_minor_axis": 6356755.0,
        "code": 3,
    }

    grid = GridSpaceView(gdtmpl_space_view)
    print(grid.params)
    assert_dict_equal(grid.params, params_space_view)
    assert_dict_equal(grid.globe, expected_globe)

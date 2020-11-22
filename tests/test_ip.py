import numpy as np
import pytest

from pywgrib2_xr.ip import (
    earth2grid_points,
    grid2earth_grid,
    grid2earth_points,
    ips_grid,
    ips_points,
    ipv_grid,
    ipv_points,
)
from pywgrib2_xr.grids import (
    grid_fromstring,
    GridPolarStereo,
    Point,
)

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
grid_polar_stereo = GridPolarStereo(gdtmpl_polar_stereo)


def test_earth2grid_points():
    # corners, counter-clockwise
    lon = [225.385728, 287.623114, 338.997404, 159.004745]
    lat = [32.549114, 24.537424, 46.277950, 65.235347]
    expected_xpts = [0, 246, 246, 0]
    expected_ypts = [0, 0, 199, 199]

    point = Point(lon, lat)
    ret = earth2grid_points(grid_polar_stereo, point)

    assert np.allclose(ret["xpts"], expected_xpts, atol=3e-5)
    assert np.allclose(ret["ypts"], expected_ypts, atol=3e-5)


def test_grid2earth_grid():
    expected_lon = [225.385728, 287.623114, 338.997404, 159.004745]
    expected_lat = [32.549114, 24.537424, 46.277950, 65.235347]

    ret = grid2earth_grid(grid_polar_stereo)

    assert ret["lon"].shape == (200, 247)
    corners = [(0, 0), (0, 246), (199, 246), (199, 0)]
    lon = [ret["lon"][c] for c in corners]
    lat = [ret["lat"][c] for c in corners]
    assert np.allclose(lon, expected_lon, atol=1e-6)
    assert np.allclose(lat, expected_lat, atol=1e-6)


def test_grid2earth_points():
    xpts = [0, 100, 200]
    ypts = [0, 10, 150]
    expected_lon = [225.385728, 252.933682, 315.553421]
    expected_lat = [32.549114, 38.898723, 55.470095]

    ret = grid2earth_points(grid_polar_stereo, xpts, ypts)

    assert np.allclose(ret["lon"], expected_lon, atol=1e-6)
    assert np.allclose(ret["lat"], expected_lat, atol=1e-6)


# Generates scalar data
def fun(lon, lat):
    return np.cos(np.radians(lat)) * np.sin(np.radians(lon))


grid_latlon = grid_fromstring("latlon 0:36:10 -90:19:10")


@pytest.fixture(scope="module")
def data():
    d = grid_latlon.params
    lon = np.arange(0, 359, d["GRIB_Di"])
    lat = np.arange(-90, 91, d["GRIB_Dj"])
    return fun(*np.meshgrid(lon, lat))


# Generates vector data
@pytest.fixture(scope="module")
def uvdata(data):
    udata = np.zeros(data.shape, dtype=np.float32)
    vdata = np.ones(data.shape, dtype=np.float32)
    return udata, vdata


def test_ips_grid_bilinear(data):
    grid_out = grid_fromstring("nps:0:60 320:12:600000 40:8:600000")
    ret = grid2earth_grid(grid_out)
    expected_lon = ret["lon"]
    expected_lat = ret["lat"]
    # True values on interpolated grid
    expected_grid = fun(expected_lon, expected_lat).reshape(8, 12)

    ret2 = ips_grid(data, "bilinear", grid_latlon, grid_out)

    assert np.allclose(ret2["lon"], expected_lon)
    assert np.allclose(ret2["lat"], expected_lat)
    assert np.allclose(ret2["data"], expected_grid, atol=3e-3, rtol=3e-3)


def test_ips_grid_neighbour(data):
    grid_out = grid_fromstring("nps:0:60 320:12:600000 40:8:600000")
    ret = grid2earth_grid(grid_out)
    expected_lon = ret["lon"]
    expected_lat = ret["lat"]
    # True values on interpolated grid
    expected_grid = fun(expected_lon, expected_lat).reshape(8, 12)

    ret2 = ips_grid(data, "neighbour", grid_latlon, grid_out)

    assert np.allclose(ret2["lon"], expected_lon)
    assert np.allclose(ret2["lat"], expected_lat)
    assert np.allclose(ret2["data"], expected_grid, atol=6e-1, rtol=1e-1)


def test_ips_grid_budget(data):
    grid_out = grid_fromstring("nps:0:60 320:12:600000 40:8:600000")
    ret = grid2earth_grid(grid_out)
    expected_lon = ret["lon"]
    expected_lat = ret["lat"]
    # True values on interpolated grid
    expected_grid = fun(expected_lon, expected_lat).reshape(8, 12)

    ret2 = ips_grid(data, "budget", grid_latlon, grid_out)

    assert np.allclose(ret2["lon"], expected_lon)
    assert np.allclose(ret2["lat"], expected_lat)
    print(np.abs(ret2["data"] - expected_grid).max())
    assert np.allclose(ret2["data"], expected_grid, atol=3e-3, rtol=3e-3)


def test_ips_grid_spectral(data):
    grid_out = grid_fromstring("nps:0:60 320:12:600000 40:8:600000")
    ret = grid2earth_grid(grid_out)
    expected_lon = ret["lon"]
    expected_lat = ret["lat"]
    # True values on interpolated grid
    expected_grid = fun(expected_lon, expected_lat).reshape(8, 12)

    ret2 = ips_grid(data, "spectral", grid_latlon, grid_out)

    assert np.allclose(ret2["lon"], expected_lon)
    assert np.allclose(ret2["lat"], expected_lat)
    print(np.abs(ret2["data"] - expected_grid).max())
    assert np.allclose(ret2["data"], expected_grid, atol=3e-3, rtol=3e-3)


def test_ips_points_bilinear(data):
    lon = [10, 130, 310]
    lat = [-10, 34, 85]
    expected = fun(lon, lat)

    point = Point(lon, lat)
    ret = ips_points(data, "bilinear", grid_latlon, point)

    assert np.allclose(ret["data"], expected, atol=3e-3, rtol=3e-3)


def test_ipv_grid(uvdata):
    grid_out = grid_fromstring("nps:0:60 320:12:600000 40:8:600000", winds="earth")
    expected_u = 0.0
    expected_v = 1.0

    u, v = uvdata
    ret = ipv_grid(u, v, "bilinear", grid_latlon, grid_out)

    assert np.allclose(ret["udata"], expected_u, atol=3e-3, rtol=3e-3)
    assert np.allclose(ret["vdata"], expected_v, atol=3e-3, rtol=3e-3)


def test_ipv_points(uvdata):
    lon = [10, 130, 310]
    lat = [-10, 34, 85]
    expected_u = 0.0
    expected_v = 1.0

    u, v = uvdata
    point = Point(lon, lat)
    ret = ipv_points(u, v, "bilinear", grid_latlon, point)

    assert np.allclose(ret["udata"], expected_u, atol=3e-3, rtol=3e-3)
    assert np.allclose(ret["vdata"], expected_v, atol=3e-3, rtol=3e-3)

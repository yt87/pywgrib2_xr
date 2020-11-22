import dill as pickle

import pytest

from pywgrib2_xr import __version__
from pywgrib2_xr.template import VarSpecs, make_template

from . import path_to, paths_to


def test_template_defaults():
    expected_specs = {
        "TMP.1000_mb": VarSpecs(
            time_coord="time1",
            level_coord=None,
            dims=["time1", "y", "x"],
            shape=[3, 200, 247],
            attrs={
                "short_name": "TMP",
                "long_name": "Temperature",
                "units": "K",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "TMP.850_mb": VarSpecs(
            time_coord="time1",
            level_coord=None,
            dims=["time1", "y", "x"],
            shape=[3, 200, 247],
            attrs={
                "short_name": "TMP",
                "long_name": "Temperature",
                "units": "K",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "TMP.700_mb": VarSpecs(
            time_coord="time1",
            level_coord=None,
            dims=["time1", "y", "x"],
            shape=[3, 200, 247],
            attrs={
                "short_name": "TMP",
                "long_name": "Temperature",
                "units": "K",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "APCP.surface.3_hour_acc": VarSpecs(
            time_coord="time2",
            level_coord=None,
            dims=["time2", "y", "x"],
            shape=[1, 200, 247],
            attrs={
                "short_name": "APCP",
                "long_name": "Total Precipitation",
                "units": "kg/m^2",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "APCP.surface.6_hour_acc": VarSpecs(
            time_coord="time3",
            level_coord=None,
            dims=["time3", "y", "x"],
            shape=[1, 200, 247],
            attrs={
                "short_name": "APCP",
                "long_name": "Total Precipitation",
                "units": "kg/m^2",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "UGRD.10_m_above_ground": VarSpecs(
            time_coord="time1",
            level_coord=None,
            dims=["time1", "y", "x"],
            shape=[3, 200, 247],
            attrs={
                "short_name": "UGRD",
                "long_name": "U-Component of Wind",
                "units": "m/s",
                "grid_mapping": "polar_stereographic",
            },
        ),
        "VGRD.10_m_above_ground": VarSpecs(
            time_coord="time1",
            level_coord=None,
            dims=["time1", "y", "x"],
            shape=[3, 200, 247],
            attrs={
                "short_name": "VGRD",
                "long_name": "V-Component of Wind",
                "units": "m/s",
                "grid_mapping": "polar_stereographic",
            },
        ),
    }
    expected_attrs = {
        "Projection": "polar_stereographic",
        "Originating centre": "54 - Canadian Meteorological Service - Montreal (RSMC)",
        "Originating subcentre": "0",
        "History": "Created by pywgrib2_xr-{:s}".format(__version__),
    }
    expected_coord_keys = [
        "latitude",
        "longitude",
        "time1",
        "time2",
        "time3",
        "x",
        "y",
    ]

    files = paths_to("CMC_glb_*_2020012512_*.grib2")
    template = make_template(files)

    assert template.attrs == expected_attrs
    assert sorted(template.coords) == expected_coord_keys
    assert template.var_specs == expected_specs


def test_template_coords():
    expected_var_names = [
        "APCP.surface.3_hour_acc",
        "APCP.surface.6_hour_acc",
        "TMP.isobaric",
        "UGRD.10_m_above_ground",
        "VGRD.10_m_above_ground",
    ]
    expected_coord_keys = [
        "isobaric1",
        "latitude",
        "longitude",
        "time1",
        "time2",
        "time3",
        "x",
        "y",
    ]

    files = paths_to("CMC_glb_*_2020012512_*.grib2")
    template = make_template(files, vertlevels=["isobaric"])

    assert template.var_names == expected_var_names
    assert sorted(template.coords.keys()) == expected_coord_keys


def test_template_empty():
    files = paths_to("CMC_glb_TMP_*_2020012512_*.grib2")

    def match(x):
        return x.varname.startswith("APCP")

    template = make_template(files, match, vertlevels=["isobaric"])

    assert template is None


def test_template_pickable():
    files = paths_to("CMC_glb_*_2020012512_*.grib2")

    def match(x):
        return x.varname.startswith("APCP")

    template = make_template(files, match, vertlevels=["isobaric"])

    unpickled = pickle.loads(pickle.dumps(template))

    assert template.attrs == unpickled.attrs
    assert set(template.coords.keys()) == set(unpickled.coords.keys())
    assert template.var_specs == unpickled.var_specs
    assert template.grid == unpickled.grid


def test_template_reftime():
    gribfile = path_to("CMC_glb_TMP_ISBL_1000_ps30km_P000.grib2")
    reftime = "2020-01-25T12"
    template = make_template(gribfile, reftime=reftime)

    assert len(template.var_specs["TMP.1000_mb"].shape) == 2


def test_template_no_reftime():
    gribfile = path_to("CMC_glb_TMP_ISBL_1000_ps30km_P000.grib2")
    with pytest.raises(ValueError) as excinfo:
        make_template(gribfile)

    assert "Reference times differ" in str(excinfo.value)

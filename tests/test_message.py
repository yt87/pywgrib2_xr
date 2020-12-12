from datetime import datetime
import os
import numpy as np

from pywgrib2_xr import (
    MemoryBuffer,
    wgrib,
    free_files,
    make_inventory,
    read_msg,
    decode_msg,
    write_msg,
)

from . import path_to, paths_to

gribfile = path_to("CMC_glb_TMP_ISBL_1000_ps30km_P000.grib2")


def test_read():
    msg = read_msg(gribfile, 1)

    assert len(msg) == 31433
    assert msg[:4] == b"GRIB"
    assert msg[-4:] == b"7777"


def test_decode():
    expected_mean = 268.018

    inv = make_inventory(gribfile)
    array = decode_msg(gribfile, inv[0])

    assert abs(array.mean() - expected_mean) < 1e-3


def test_write(tmpdir):
    outfile = os.path.join(tmpdir, "rh1.grib2")
    write_msg(outfile, gribfile, 1, date="2020-11-03", ftime="6 hour fcst")
    inv = make_inventory(outfile)
    assert inv[0].reftime == datetime.fromisoformat("2020-11-03")
    assert inv[0].end_ft == datetime.fromisoformat("2020-11-03T06:00:00")


def test_write_data(tmpdir):
    nx, ny = 247, 200
    data = 100.0 * np.random.random_sample((ny, nx))
    outfile = os.path.join(tmpdir, "rh2.grib2")
    write_msg(outfile, gribfile, 1, data, var="RH", grib_type="aec", bin_prec=7)
    inv = make_inventory(outfile)
    array = decode_msg(outfile, inv[0])

    assert np.allclose(array, data, rtol=1e-2, atol=5e-1)
    assert inv[0].varname == "RH"


def test_roundtrip(tmpdir):
    infile = path_to('gfs_tsoil.grib2')
    outfile = os.path.join(tmpdir, "t_soil.grib2")

    inv = make_inventory(infile)
    array = decode_msg(infile, inv[0]).copy()   # make it writable
    write_msg(outfile, infile, 1, array, var="TSOIL", grib_type="same", bin_prec=10)
    inv2 = make_inventory(outfile)
    array2 = decode_msg(outfile, inv2[0])

    assert np.allclose(array, array2, rtol=1e-2, atol=1e-1)



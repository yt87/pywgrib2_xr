from contextlib import contextmanager
import glob
import os
import re

import pytest
import numpy as np

_datadir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def path_to(basename):
    return os.path.join(_datadir, basename)


def paths_to(pattern):
    return glob.glob(os.path.join(_datadir, pattern))


# copied from xarray.tests.__init__
@contextmanager
def raises_regex(error, pattern):
    __tracebackhide__ = True
    with pytest.raises(error) as excinfo:
        yield
    message = str(excinfo.value)
    if not re.search(pattern, message):
        raise AssertionError(
            f"exception {excinfo.value!r} did not match pattern {pattern!r}"
        )


def assert_dict_equal(d1, d2):
    assert len(d1) == len(d2), "{:d} != {:d}".format(len(d1), len(d2))
    for k, v in d1.items():
        assert k in d2
        if isinstance(v, float):
            assert np.isclose(v, d2[k], rtol=1e-5), "{:s}: {!f} != {!f}".format(
                k, v, d2[k]
            )
        elif isinstance(v, list) and all(isinstance(i, int) for i in v):
            # elif isinstance(v, np.ndarray):
            # Special case for gdtmpl
            assert np.allclose(
                v, d2[k], rtol=1e-5, atol=1e-5
            ), "{:s}: {!r} != {!r}".format(k, v, d2[k])
        else:
            assert v == d2[k], "{:s}: {!r} != {!r}".format(k, v, d2[k])

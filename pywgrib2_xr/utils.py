from datetime import datetime, timedelta
import glob
import logging
import os
from urllib.error import URLError
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)
# Allow user to specify directory when pywgrib2_xr is installed by conda
DATADIR = os.environ.get('DATADIR',
	os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data")))
DEFAULT_CACHE = os.path.join(os.environ["HOME"], ".cache", "pywgrib2")
URL = "https://ftpprd.ncep.noaa.gov/data/nccf/com"


def localpath(file):
    """Returns path to `file` on the disk.

    Parameters
    ----------
    file: str
        File name.

    Returns
    -------
    str
        Absolute path to `file`.
    """
    return os.path.join(DATADIR, file)


def localpaths(pattern):
    """Returns files in data directory matching pattern.

    Parameters
    ----------
    pattern: str
        Glob pattern to match requested files.

    Returns
    -------
    list
        List of paths to files matching `pattern`.
    """
    return glob.glob(os.path.join(DATADIR, pattern))


def remotepath(file, cachedir=DEFAULT_CACHE):
    """Returns path to `file`.

    Tries data directory first, then cache, downloads file from ftpprd as
    the last resort.

    Parameters
    ----------
    file: str
        File name.
    cachedir: str
        Cache directory. Default is ~/.cache/pywgrib2. The directory is created
        if it does not exist.

    Returns
    -------
    str
        Absolute path to `file`.
    """
    # test files
    path = os.path.join(DATADIR, file)
    if os.path.isfile(path):
        return path
    # downloaded files
    path = os.path.join(cachedir, file)
    if os.path.isfile(path):
        return path
    # download previous day data
    if not os.path.isdir(DEFAULT_CACHE):
        try:
            os.makedirs(DEFAULT_CACHE)
        except OSError as e:
            logger.error("Cannot create data cache: {!r}".format(e))
            return None
    t = datetime.today() - timedelta(days=1)
    # figure out remote directory
    if file.startswith("nam.t"):
        tokens = ["nam", "prod", t.strftime("nam.%Y%m%d")]
    elif file.startswith("gfs.t"):
        tokens = ["gfs", "prod", t.strftime("gfs.%Y%m%d")]
    elif file.startswith("CMC_reg"):
        tokens = ["gfs", "prod", t.strftime("gfs.%Y%m%d")]
    else:
        raise ValueError("Only GFS and NAM data can be retrieved")
    tokens.append(file)
    url = os.path.join(URL, *tokens)
    try:
        logger.info("Downloading {:s} as {:s}".format(url, path))
        p, m = urlretrieve(url, path)
        assert p == path
    except URLError as e:
        logger.error("Cannot retrieve file {:s} from server: {!r}".format(url, e))
        return None
    return path


# FIXME: for test, remove
if __name__ == "__main__":
    import sys

    file = sys.argv[1]
    remotepath(file)

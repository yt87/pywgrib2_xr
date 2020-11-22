from cpython.mem cimport PyMem_Malloc, PyMem_Free
import numpy as np
cimport numpy as np
# cimport openmp

np.import_array()

from . import UNDEFINED
cdef double FILL = UNDEFINED

cdef extern from "numpy/arrayobject.h":
    void PyArray_ENABLEFLAGS(np.ndarray arr, int flags)

cdef extern from 'pywgrib2.h':
    void status_ffopen()
    int ll2ij(unsigned char **sec, double *grid_lon, double *grid_lat, int npts,
              double *lon, double *lat, double *x, double *y)
    int sec3latlon(unsigned char **sec, double **lon, double **lat)
    void gdswzd(int igdtnum, int* igdtmpl, int igdtlen, int iopt, int npts,
                double fill, double *xpts, double *ypts, double *rlon,
                double *rlat, int *nret, double *crot, double *srot,
                double *xlon, double *xlat, double *ylon, double *ylat,
                double *area)
    int wgrib2(int ac, const char *av[])
    int wgrib2_free_file(const char *filename)
    size_t wgrib2_get_mem_buffer_size(int n)
    int wgrib2_get_mem_buffer(unsigned char *buffer, size_t size, int n)
    int wgrib2_set_mem_buffer(const unsigned char *data, size_t ndata, int n)
    size_t wgrib2_get_reg_size(int n)
    int wgrib2_get_reg_data(float *data, size_t size, int reg)
    int wgrib2_set_reg(float *data, size_t size, int reg)

    void IPOLATES(int *ip, int *ipopt, int *gdtnumi, int *gdtmpli,
                  int *igdtleni, int *gdtnumo, int *gdtmplo, int *gdtleno,
                  int *mi, int *mo, int *km, int *ibi, unsigned char *li,
                  double *gi, int *no, double *rlat, double *rlon, int *ibo,
                  unsigned char *lo, double *go, int *iret)
    void IPOLATEV(int *ip, int *ipopt, int *gdtnumi, int *gdtmpli,
                  int *igdtleni, int *gdtnumo, int *gdtmplo, int *gdtleno,
                  int *mi, int *mo, int *km, int *ibi, unsigned char *li,
                  double *ui, double *vi, int *no, double *rlat, double *rlon,
                  double *crot, double *srot, int *ibo, unsigned char *lo,
                  double *uo, double *vo, int *iret)


# def set_num_threads(int n):
#     cdef int max_threads = openmp.omp_get_max_threads()
#     if n > max_threads:
#         n = max_threads
#     if n < 1:
#         n = 1
#     openmp.omp_set_num_threads(n)


def wgrib(args):
    cdef int argc = len(args) + 1
    cdef const char **argv = <const char **> PyMem_Malloc(argc * sizeof(char*))
    try:
        argv_bytes = ['wgrib2'.encode()]
        argv_bytes.extend([str(a).encode() for a in args])
        for k, a in enumerate(argv_bytes):
            argv[k] = a
        return wgrib2(argc, argv)
    finally:
        PyMem_Free(argv)


def free_file(char *file):
    # Always return 0. wgrib2_free_file issues only warnings
    wgrib2_free_file(&file[0])
    return 0


def status_open():
    status_ffopen()


def get_mem_buf(int n):
    cdef size_t bufsize = wgrib2_get_mem_buffer_size(n)
    if bufsize < 1:
        return b''
    cdef unsigned char *cbuf = \
            <unsigned char*> PyMem_Malloc(bufsize * sizeof(unsigned char*))
    if not cbuf:
        raise MemoryError()
    cdef bytes py_string
    rc = wgrib2_get_mem_buffer(cbuf, bufsize, n)
    if rc == 0:
        py_string = cbuf[:bufsize]   # indexing needed to read null bytes 
    PyMem_Free(cbuf)
    return None if rc else py_string


def set_mem_buf(int n, const unsigned char[:] data):
    rc = wgrib2_set_mem_buffer(&data[0], data.size, n)
    return None if rc else 0


def get_reg_data(int n):
    cdef size_t bufsize = wgrib2_get_reg_size(n)
    cdef np.ndarray[float, ndim=1, mode='c'] arr = np.empty((bufsize,),
                                                            dtype=np.float32)
    rc = wgrib2_get_reg_data(&arr[0], bufsize, n)
    return None if rc else arr


def set_reg_data(int n, np.ndarray[float] arr):
    rc = wgrib2_set_reg(&arr[0], arr.size, n)
    return None if rc else 0


def gdswiz(int gdtnum, np.ndarray[int] gdtmpl, int opt,
           np.ndarray[double] xpts, np.ndarray[double] ypts,
           np.ndarray[double] rlon, np.ndarray[double] rlat,
           np.ndarray[double] crot, np.ndarray[double] srot,
           np.ndarray[double] xlon, np.ndarray[double] xlat,
           np.ndarray[double] ylon, np.ndarray[double] ylat,
           np.ndarray[double] area):
    cdef int gdtlen, nret, npts
    gdtlen = gdtmpl.size
    npts = xpts.size
    gdswzd(gdtnum, &gdtmpl[0], gdtlen, opt, npts, FILL, &xpts[0], &ypts[0],
           &rlon[0], &rlat[0], &nret, &crot[0], &srot[0], &xlon[0], &xlat[0],
           &ylon[0], &ylat[0], &area[0])
    return nret


def ipolates(int ip, np.ndarray[int] ipopt,
             int gdtnum_in, np.ndarray[int] gdstmpl_in,
             int gdtnum_out, np.ndarray[int] gdstmpl_out,
             int m_in, int m_out, int km,
             np.ndarray[int] ib_in, np.ndarray[np.uint8_t] l_in,
             np.ndarray[double] g_in, np.ndarray[double] rlat,
             np.ndarray[double] rlon, np.ndarray[int] ib_out,
             np.ndarray[np.uint8_t] l_out, np.ndarray[double] g_out):
    cdef int iret, n_out
    cdef int gdtlen_in = gdstmpl_in.size
    cdef int gdtlen_out = gdstmpl_out.size
    if gdtnum_out < 0:
        n_out = m_out
    IPOLATES(&ip, &ipopt[0], &gdtnum_in, &gdstmpl_in[0], &gdtlen_in,
             &gdtnum_out, &gdstmpl_out[0], &gdtlen_out, &m_in, &m_out, &km,
             &ib_in[0], &l_in[0], &g_in[0], &n_out, &rlat[0], &rlon[0],
             &ib_out[0], &l_out[0], &g_out[0], &iret)
    return iret, n_out


def ipolatev(int ip, np.ndarray[int] ipopt,
             int gdtnum_in, np.ndarray[int] gdstmpl_in,
             int gdtnum_out, np.ndarray[int] gdstmpl_out,
             int m_in, int m_out, int km,
             np.ndarray[int] ib_in, np.ndarray[np.uint8_t] l_in,
             np.ndarray[double] u_in, np.ndarray[double] v_in,
             np.ndarray[double] rlat, np.ndarray[double] rlon,
             np.ndarray[double] crot, np.ndarray[double] srot,
             np.ndarray[int] ib_out, np.ndarray[np.uint8_t] l_out,
             np.ndarray[double] u_out, np.ndarray[double] v_out):
    cdef int iret, n_out = m_out
    cdef int gdtlen_in = gdstmpl_in.size
    cdef int gdtlen_out = gdstmpl_out.size
    cdef np.ndarray[double] xpts
    cdef np.ndarray[double] ypts
    cdef np.ndarray[double] xlon
    cdef np.ndarray[double] xlat
    cdef np.ndarray[double] ylon
    cdef np.ndarray[double] ylat
    cdef np.ndarray[double] area
    if gdtnum_out < 0:
        xpts = np.empty(n_out, dtype=np.float64)
        ypts = np.empty(n_out, dtype=np.float64)
        xlon = np.empty(n_out, dtype=np.float64)
        xlat = np.empty(n_out, dtype=np.float64)
        ylon = np.empty(n_out, dtype=np.float64)
        ylat = np.empty(n_out, dtype=np.float64)
        area = np.empty(n_out, dtype=np.float64)
        gdswzd(gdtnum_in, &gdstmpl_in[0], gdtlen_in, -1, m_out, FILL,
               &xpts[0], &ypts[0], &rlon[0], &rlat[0], &iret,
               &crot[0], &srot[0], &xlon[0], &xlat[0],
               &ylon[0], &ylat[0], &area[0])
        if iret < 0:
            return 2, 0     # Unrecognised projection
    IPOLATEV(&ip, &ipopt[0], &gdtnum_in, &gdstmpl_in[0], &gdtlen_in,
             &gdtnum_out, &gdstmpl_out[0], &gdtlen_out, &m_in, &m_out, &km,
             &ib_in[0], &l_in[0], &u_in[0], &v_in[0], &n_out,
             &rlat[0], &rlon[0], &crot[0], &srot[0], &ib_out[0], &l_out[0],
             &u_out[0], &v_out[0], &iret)
    return iret, n_out


cdef unsigned char** mksec(unsigned char* sec3):
    cdef unsigned char** sec = \
        <unsigned char**> PyMem_Malloc(4 * sizeof(unsigned char*))
    sec[0] = b''
    sec[1] = b'00000015010007000002010107e4020a0000000001'  # dummy
    sec[2] = b''
    sec[3] = sec3
    return sec


def latlon2xy(unsigned char* sec3,
              np.ndarray[double] grid_lon, np.ndarray[double] grid_lat,
              np.ndarray[double] lon, np.ndarray[double] lat):
    cdef int iret
    cdef int npts = lon.size
    cdef np.ndarray[double] x = np.empty(npts, dtype=np.float64)
    cdef np.ndarray[double] y = np.empty(npts, dtype=np.float64)
    try:
        sec = mksec(&sec3[0])
        iret = ll2ij(&sec[0], &grid_lon[0], &grid_lat[0], npts, &lon[0], &lat[0],
                     &x[0], &y[0])
        if iret != 0:
            return None
    finally:
        PyMem_Free(sec)
    return x, y


def latlon(unsigned char *sec3, int npoints): 
    # sections is a list of length >= 4 of bytes
    cdef double* lon = NULL
    cdef double* lat = NULL
    cdef int iret
    cdef np.ndarray[np.double_t, ndim=1] lon_array, lat_array
    cdef np.npy_intp npts[1]
    cdef unsigned char** sec
    try:
        sec = mksec(&sec3[0])
        iret = sec3latlon(&sec[0], &lon, &lat)
    finally:
        PyMem_Free(sec)
    if iret != 0:
        return None
    npts[0] = <np.npy_intp> npoints
    lon_array = np.PyArray_SimpleNewFromData(1, npts, np.NPY_FLOAT64, lon)
    # FIXME: check for memory leak
    PyArray_ENABLEFLAGS(lon_array, np.NPY_ARRAY_OWNDATA)
    lat_array = np.PyArray_SimpleNewFromData(1, npts, np.NPY_FLOAT64, lat)
    PyArray_ENABLEFLAGS(lat_array, np.NPY_ARRAY_OWNDATA)
    return lon_array, lat_array

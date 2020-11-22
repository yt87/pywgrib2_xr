// direct access to wgrib2 functions
//
#include <stddef.h>
#include <setjmp.h>
#include "pywgrib2.h"

extern enum output_order_type output_order;

extern int gctpc_ll2xy_init(unsigned char **sec, double *grid_lon, double *grid_lat);
extern int gctpc_ll2xy(int n, double *lon, double *lat, double *x, double *y);
extern int gctpc_get_latlon(unsigned char **sec, double **lon, double **lat);
extern int get_latlon(unsigned char **sec, double **lon, double **lat);
extern jmp_buf fatal_err;


int ll2ij(unsigned char **sec, double *grid_lon, double *grid_lat, int npts,
          double *lon, double *lat, double *x, double *y)
{
    int i;

    output_order = wesn;
    if (setjmp(fatal_err)) {
        return 9;
    }
    i = gctpc_ll2xy_init(sec, grid_lon, grid_lat);
    if (i != 0) {
        return i;
    }
    i = gctpc_ll2xy(npts, lon, lat, x, y);
    return i;
}


int sec3latlon(unsigned char **sec, double **lon, double **lat)
{
    int i;

    output_order = wesn;
    if (setjmp(fatal_err)) {
        return 9;
    }
    i = gctpc_get_latlon(sec, lon, lat);
    if (i != 0) {
        i = get_latlon(sec, lon, lat);
    }
    return i;
}

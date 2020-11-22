// local functions
//
#include "wgrib2/wgrib2.h"
#include "wgrib2/wgrib2_api.h"
#include "wgrib2/iplib_d.h"

extern int ll2ij(unsigned char **sec, double *grid_lon, double *grid_lat, int npts,
                 double *lon, double *lat, double *x, double *y);
extern int sec3latlon(unsigned char **sec, double **lon, double **lat);

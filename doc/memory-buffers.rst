Memory Buffers
==============

**wgrib2** C API has an unorthodox design. Usually, libraries are written
first,  executables call functions from those libraries. In case of **wgrib2**,
the C ``main`` functions was made a library function. As a consequence,
all arguments must be strings. Data returned by ``wgrib2`` is written to
memory buffers. The API provides methods to read those buffers. ``wgrib2`` 
can also process data written to memory buffers by the client application.

There can be up to 30 distinct memory buffers (and 20 RPN registers, used
to pass calculated data, those are also chunks of memory). The buffers are
identifiable by a number.
In order to free the library user from keeping track of those numbers,
``pywgrib2_xr`` has its own classes :py:class:`~pywgrib2_xr.MemoryBuffer`
and :py:class:`~pywgrib2_xr.RPNRegister` that shadow their ``wgrib2``
counterparts.
Instantiating a class retrieves available number from a pool, calling
:py:meth:`~pywgrib2_xr.MemoryBuffer.close` returns buffer number
to the pool. It *does not* free allocated memory. Closing the buffer can
also be achieved by using the ``with`` construct.

Examples:

1. Create a short inventory of a GRIB2 file in memory, then print it.

  .. code-block:: python

      import pywgrib2_xr as pywgrib2
      from pywgrib2_xr.utils import localpath
      file = localpath('CMC_glb_TMP_ISBL_850_ps30km_2020012500_P000.grib2')
      with pywgrib2.MemoryBuffer() as buf:
      args = [file, '-inv', buf]
      pywgrib2.wgrib(*args)
      inv = buf.get('s')
      print(inv)

.. parsed-literal::

    1:0:d=2020012500:TMP:850 mb:anl:

Here, the argument ``'s'`` in a call to ``buf.get()`` means the returned data should
be a string.

2. Read values and geolocation data into ``numpy`` arrays.

  .. code-block:: python

      import pywgrib2_xr as pywgrib2
      from pywgrib2_xr.utils import localpath
      from contextlib import ExitStack
      file = localpath('CMC_glb_ps30km_2020012512.grib2')
      with ExitStack() as stack:
          data_reg = stack.enter_context(pywgrib2.RPNRegister())
          lon_reg = stack.enter_context(pywgrib2.RPNRegister())
          lat_reg = stack.enter_context(pywgrib2.RPNRegister())
          inv_buf = stack.enter_context(pywgrib2.MemoryBuffer())
          args = [file, '-rewind_init', file, '-d', 3,
                  '-inv', inv_buf, '-ftn_api_fn0', '-rpn_sto', data_reg,
                  '-rpn', 'rcl_lon:sto_{}'.format(lon_reg),
                  '-rpn', 'rcl_lat:sto_{}'.format(lat_reg)]
          pywgrib2.wgrib(*args)
          npts, nx, ny = [int(i) for i in buf.get('s').split()[2:5]]
          tmp = data_reg.get().reshape((ny, nx))
          lon = lon_reg.get().reshape((ny, nx))
          lat = lat_reg.get().reshape((ny, nx))
          print(lon[:3,:3])
          print(lat[:3,:3])
          print(tmp[0,0], tmp[-1, -1])

.. parsed-literal::

    [[225.38573 225.62788 225.87093]
     [225.2796  225.5226  225.76648]
     [225.17259 225.41641 225.66115]]
    [[32.549114 32.637794 32.725685]
     [32.752975 32.842205 32.93064 ]
     [32.957066 33.04685  33.135838]]
    288.38113 285.1811

All three registers and the memory buffers are available for reuse.

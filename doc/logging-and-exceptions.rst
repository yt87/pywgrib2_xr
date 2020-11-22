Logging and Exceptions
======================

Exception Handling
------------------

**pywgrib2_xr** defines exception :py:class:`~pywgrib2_xr.WgribError`
which is raised when a C function returns nonzero status. If that function
writes an error message to ``stderr``, it will be captured as exception value:

.. ipython:: python
   :okexcept:

   import pywgrib2_xr as pywgrib2

   pywgrib2.wgrib('nonexistent')

If the error is not fatal for the calling code, it should be handled as follows::

  >>> file = '/tmp/gfs.grib2'
  >>> try:
  ...    wgrib2(file, '-foo')
  >>> except pywgrib2.WgribError as e:
         print(e)
         ...
         cleaning code here
         ...
  >>> finally:
  ...    pywgrib2.free_files(file)

The ``finally`` clause ensures that ``file`` is closed. The function ``wgrib``
does not close files on exit. One can try to set ``wgrib2`` arguments
``'-transient', file``, but this does not work when ``wgrib`` call fails::

  >>> pywgrib2.wgrib('gfs.grib2', '-foo', '-transient', 'gfs.grib2')

  >>> pywgrib2.status_open()
  <stdin>:1: UserWarning: 
  file: gfs.grib2 r:perm file_offset=0 usage=0

The function :py:func:`~pywgrib2_xr.status_open`, intended for debugging,
prints files opened by the C code. 

When the C function prints a message but returns 0, the message is treated
as a warning::

  >>> pywgrib.free_files('nonexistent')
  <stdin>:1: UserWarning: 
  Warning wgrib2_free_file: nonexistent not found

Logging
-------

**pywgrib2_xr** uses Python module
`logging <https://docs.python.org/3/howto/logging.html>`__.
By defaults, all emmited messages are output to Python's ``stderr``. It is
possible to set logging level and a different output stream::

  >>> import logging
  >>> logging.basicConfig(filename='my.log', level=logging.DEBUG)
  >>> pywgrib2.wgrib('gfs.grib2', '-inv', 'gfs.inv')
  >>>
  $ cat my.log
  $ DEBUG:pywgrib2_xr.wgrib2:args: ('gfs.grib2', '-inv', 'gfs.inv')
  
Setting level to ``DEBUG`` outputs arguments passed to ``wgrib``.



Logging and Exceptions
======================

Exception Handling
------------------

**pywgrib2_xr** defines exception :py:class:`~pywgrib2_xr.WgribError`
which is raised when a C function returns nonzero status. If that function
writes an error message to ``stderr``, it will be captured as exception value:

.. code-block:: python

    import pywgrib2_xr as pywgrib2

    file = 'nonexistent'
    try:
        pywgrib2.wgrib('nonexistent')
    except WgribError as e:
        print(e)
    finally:
        pywgrib2.free_files(file)

.. parsed-literal::

    \*** FATAL ERROR: missing input file nonexistent \***

    \*** arg list to wgrib2: wgrib2 nonexistent

The ``finally`` clause ensures that ``file`` is closed. The function ``wgrib``
does not close files on exit. One can try to set ``wgrib2`` arguments
``'-transient', file``, but this does not work when ``wgrib`` call fails:

.. code-block:: python

    file = 'gfs_tsoil.grib2'
    try:
        pywgrib2.wgrib(file, '-foo', '-transient', file)
    except Exception as e:
        print(e)
    pywgrib2.status_open()

.. parsed-literal::

    \*** FATAL ERROR: unknown option -foo \***

    \*** arg list to wgrib2: wgrib2 gfs_tsoil.grib2 -foo -transient gfs_tsoil.grib2

    <stdin>:1: UserWarning: 
    file: gfs_tsoil.grib2 r:perm file_offset=0 usage=0

The function :py:func:`~pywgrib2_xr.status_open`, intended for debugging,
prints files opened by the C code. 

Logging
-------

**pywgrib2_xr** uses Python module
`logging <https://docs.python.org/3/howto/logging.html>`__.
By defaults, all emmited messages are output to Python's ``stderr``. It is
possible to set logging level and a different output stream:

.. code-block:: python

    import logging
    logging.basicConfig(filename='my.log', level=logging.DEBUG)
    pywgrib2.wgrib('gfs.grib2', '-inv', 'gfs.inv')

.. parsed-literal::

    cat my.log
    DEBUG:pywgrib2_xr.wgrib2:args: ('gfs.grib2', '-inv', 'gfs.inv')
  
Setting level to ``DEBUG`` outputs arguments passed to ``wgrib``.



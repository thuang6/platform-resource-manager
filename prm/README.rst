PRM
===


Getting started
-----------------------

Building
^^^^^^^^

.. code-block:: shell

    pipenv shell
    tox 

    # offline fast re-build using .pex-build cache
    # (reuse cache from 1 week)
    PEX_OPTIONS='--no-index --cache-ttl=600000' tox

Running
^^^^^^^

.. code-block:: shell

    ./dist/owca-prm.pex -c mesos_prm.yaml -r prm.detector:ContentionDetector -l info


#!/bin/bash

#run python test cases

sudo -u postgres psql -c "alter user geoshape with superuser;"

/var/lib/geonode/bin/python /var/lib/geonode/rogue_geonode/manage.py test fulcrum_importer.tests.test_fulcrum_importer fulcrum_importer.tests.test_viewer fulcrum_importer.tests.test_tasks fulcrum_importer.tests.test_filters

sudo -u postgres psql -c "alter user geoshape with nosuperuser;"

#!/bin/bash
patch -p0 ./venv/lib/python3.6/site-packages/oauth2client/contrib/django_util/__init__.py to-file.patch

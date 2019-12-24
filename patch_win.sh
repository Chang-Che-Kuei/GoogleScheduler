#!/bin/bash
patch -p0 ./venv/Lib/site-packages/oauth2client/contrib/django_util/__init__.py to-file.patch

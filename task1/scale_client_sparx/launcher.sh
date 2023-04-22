#!/bin/sh
sleep 60
cd /
cd home/pi/Desktop/scale_client_sparx
python3 data/pub.py & /usr/bin/python -m scale_client --config /home/pi/Desktop/scale_client_sparx/scale_client/config/sparx.yml --log-level info
cd /

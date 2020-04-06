#!/bin/bash

java -Xms32G -Xmx65G \
    -cp /data/matsim-12.0-SNAPSHOT/matsim-12.0-SNAPSHOT.jar \
    org.matsim.run.Controler /data/input/config.xml


#!/bin/bash

#SBATCH -p fn1                                      # Use fn1 partition

#SBATCH -N 1                                        # number of compute nodes
#SBATCH -n 64                                       # number of CPU cores to reserve on this compute node

#SBATCH -t 1-00:00                                  # wall time (D-HH:MM)
#SBATCH -o slurm.%j.out                             # STDOUT (%j = JobId)
#SBATCH -e slurm.%j.err                             # STDERR (%j = JobId)
#SBATCH --mail-type=ALL                             # Send a notification when a job starts, stops, or fails
#SBATCH --mail-user=bmbrownl@asu.edu                # send-to address

# interactive -n 8 -N 1 --mem=32000 -t 0-04:00      # interactive

java -Xms16G -Xmx32G \
    -cp /home/bmbrownl/icarus/run/matsim.jar \
    org.matsim.run.Controler /home/bmbrownl/icarus/run/input/config.xml

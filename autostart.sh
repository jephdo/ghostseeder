#!/bin/bash
ps -ef | pgrep -fl ghostseeder.py
# if not found - equals to 1, start it
if [ $? -eq 1 ] 
then
    echo "Ghostseeder not running"
    startghostseed
fi
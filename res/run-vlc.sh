#!/bin/bash

export DISPLAY=:0 && su -c "cvlc --no-osd --no-video-title-show --network-caching=200 rtp://@:7236" letsving
#export DISPLAY=:0 && su -c "cvlc --no-osd --no-video-title-show --network-caching=200 --no-ts-trust-pcr --h264-fps=23 rtp://@:7236" letsving

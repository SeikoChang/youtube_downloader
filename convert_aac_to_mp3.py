#!/usr/bin/env python
# -*- coding: utf-8 -*-

# chcp 65001       #转换为utf-8代码页
# chcp 936           #转换为默认的gb

import os

from helpers import download_ffmpeg
from helpers import ffmpeg_aac_convert_mp3

target = "Youtube"
ffmpeg_binary = download_ffmpeg()

# traverse root directory, and list directories as dirs and files as files
for root, dirs, files in os.walk(target):
    path = root.split(os.sep)
    for file in files:
        filename, fileext = os.path.splitext(file)
        base = os.path.basename(file)
        name, ext = os.path.splitext(base)
        if fileext not in ['mp3']:
            mp3 = ffmpeg_aac_convert_mp3(aac=os.path.join(root, file), target=target, ffmpeg=ffmpeg_binary, skip=True)


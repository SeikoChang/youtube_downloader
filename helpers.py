#!/usr/bin/env python
# -*- coding: utf-8 -*-

# chcp 65001       #转换为utf-8代码页
# chcp 936           #转换为默认的gb

from download_file import download_file
from pytube import YouTube
from pytube.helpers import uniqueify
from pytube.helpers import safe_filename
import sys
import os
import tempfile
import logging
import subprocess
import shutil
import platform
import zipfile
import contextlib
import lzma
import tarfile
import stat
import argparse
import ntpath

PY3K = sys.version_info >= (3, 0)
if PY3K:
    import urllib.request as urllib2
    import urllib.parse as urlparse
else:
    import urllib2
    import urlparse


logger = logging.getLogger(__name__)


def get_terminal_size_windows():
    try:
        from ctypes import windll, create_string_buffer
        import struct
        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12
        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
        if res:
            (bufx, bufy, curx, cury, wattr,
             left, top, right, bottom,
             maxx, maxy) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            sizex = right - left + 1
            sizey = bottom - top + 1
            return sizex, sizey
    except:
        pass


def get_terminal_size_stty():
    try:
        return map(int, subprocess.check_output(['stty', 'size']).split())
    except:
        pass


def get_terminal_size_tput():
    try:
        return map(int, [subprocess.check_output(['tput', 'lines']), subprocess.check_output(['tput', 'rows'])])
    except:
        pass


def get_terminal_size():
    return get_terminal_size_windows() or get_terminal_size_stty() or get_terminal_size_tput() or (25, 80)


def detect_platform():
    is_64bit = platform.machine().endswith('64')
    arch = '64bit' if is_64bit else '32bit'
    logger.info(platform.system())
    logger.info(platform.release())
    logger.info(platform.version())
    logger.info(arch)

    # logger.info("Your system is %s %s" % (platform.system(), arch))
    if platform.system().lower() == "windows":
        logger.info("Your system is windows %s" % arch)
    elif platform.system().lower() == "linux":
        logger.info("Your system is Linux %s" % arch)
        logger.info(platform.linux_distribution)
    elif platform.system().lower() == "darwin":
        logger.info("Your system is MacOS %s" % arch)
        logger.info(platform.mac_ver)
    else:
        logger.info("Unidentified system")

    return platform.system(), arch


def fib(n):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n-1)+fib(n-2)


def symlink(source, link_name):
    os_symlink = getattr(os, "symlink", None)
    try:
        os_symlink(source, link_name)
    except:
        try:
            import ctypes
            csl = ctypes.windll.kernel32.CreateSymbolicLinkW
            csl.argtypes = (ctypes.c_wchar_p,
                            ctypes.c_wchar_p, ctypes.c_uint32)
            csl.restype = ctypes.c_ubyte
            flags = 1 if os.path.isdir(source) else 0
            if csl(link_name, source, flags) == 0:
                raise ctypes.WinError()
        except:
            try:
                import win32file
                win32file.CreateSymbolicLink(fileSrc, fileTarget, 1)
            except:
                print('unable to create symbolic link from [{src}] to [{dst}]'.format(
                    src=source, dst=link_name))


def copyfile(source, destination, skip=True):
    if skip == True and os.path.isfile(source) and os.path.isfile(destination) and (os.path.getsize(source) == os.path.getsize(destination)):
        pass
    else:
        shutil.copyfile(source, destination)

    st = os.stat(source)
    shutil.copymode(source, destination)
    os.chown(destination, st[stat.ST_UID], st[stat.ST_GID])
    # return True if skip == True and os.path.isfile(source) and os.path.isfile(destination) and (os.path.getsize(source) == os.path.getsize(destination)) else shutil.copyfile(source, destination)


def median(lst):
    # sortedLst = sorted(lst)
    lstLen = len(lst)
    index = (lstLen - 1) // 2

    if (lstLen % 2):
        return lst[index]
    else:
        return lst[index]


def unzip_without_overwrite(src_path, dst_dir, pwd=None):
    with zipfile.ZipFile(src_path) as zf:
        members = zf.namelist()
        for member in members:
            arch_info = zf.getinfo(member)
            arch_name = arch_info.filename.replace('/', os.path.sep)
            dst_path = os.path.join(dst_dir, arch_name)
            dst_path = os.path.normpath(dst_path)
            if not os.path.exists(dst_path):
                zf.extract(arch_info, dst_dir, pwd)


def filename_fix_existing(filename):
    """Expands name portion of filename with numeric ' (x)' suffix to
    return filename that doesn't exist already.
    """
    head, tail = ntpath.split(filename)
    base = os.path.basename(filename)
    name, ext = os.path.splitext(base)

    if not head:
        head = u'.'

    try:
        name, ext = tail.rsplit('.', 1)
    except:
        # handle those filename without extention name
        name = tail.rsplit(os.sep, 1)[0]
        ext = None
    names = [x for x in os.listdir(head) if x.startswith(name)]
    if ext:
        names = [x.rsplit('.', 1)[0] for x in names]
    else:
        names = [x.rsplit(os.sep, 1)[0] for x in names]
    suffixes = [x.replace(name, '') for x in names]
    # filter suffixes that match ' (x)' pattern
    suffixes = [x[2:-1] for x in suffixes
                if x.startswith('_(') and x.endswith(')')]
    indexes = [int(x) for x in suffixes
               if set(x) <= set('0123456789')]
    idx = 1
    if indexes:
        idx += sorted(indexes)[-1]

    if ext:
        out = '{0}_({1}).{2}'.format(name, idx, ext)
    else:
        out = '{0}_({1})'.format(name, idx)
    out = os.path.join(head, out)
    return out


def to_unicode(filename):
    """:return: filename decoded from utf-8 to unicode"""
    if PY3K:
        # [ ] test this on Python 3 + (Windows, Linux)
        # [ ] port filename_from_headers once this works
        # [ ] add test to repository / Travis
        return filename
    else:
        if isinstance(filename, unicode):
            return filename
        else:
            return unicode(filename, 'utf-8')


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def download_ffmpeg(out=os.getcwd()):
    platform, arch = detect_platform()
    if platform.lower() == "windows":
        if arch.lower() == '32bit':
            ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip"
        elif arch.lower() == '64bit':
            ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip"
        ffmpeg = download_file(url=ffmpeg_url, out=out)
        logger.info("%s downloaded" % ffmpeg)
        #unzip_without_overwrite(src_path=ffmpeg, dst_dir=out)
        with zipfile.ZipFile(ffmpeg, 'r') as zip_ref:
            # zip_ref.extractall(out)
            for file in zip_ref.filelist:
                if not os.path.exists(file.filename):
                    zip_ref.extract(file, out)
                if file.filename.endswith("ffmpeg.exe") and (not file.is_dir()) and int(file.file_size) > 0:
                    ffmpeg_binary = file.filename
                    break

    elif platform.lower() == "linux":
        if arch.lower() == '32bit':
            ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        elif arch.lower() == '64bit':
            ffmpeg_url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
        ffmpeg = download_file(url=ffmpeg_url, out=out)
        logger.info("%s downloaded" % ffmpeg)
        with contextlib.closing(lzma.LZMAFile(ffmpeg)) as xz:
            with tarfile.open(fileobj=xz) as f:
                # f.extractall(out)
                for member in f.members:
                    if not os.path.exists(member.name):
                        f.extractfile(member)
                    if member.name.endswith('ffmpeg') and int(member.size) > 0 and int(member.mode) == 493:
                        ffmpeg_binary = member.name
                        break

    elif platform.lower() == "darwin":
        ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/macos64/static/ffmpeg-latest-macos64-static.zip"
        ffmpeg = download_file(url=ffmpeg_url, out=out)
        logger.info("%s downloaded" % ffmpeg)
        #unzip_without_overwrite(src_path=ffmpeg, dst_dir=out)
        with zipfile.ZipFile(ffmpeg, 'r') as zip_ref:
            # zip_ref.extractall(out)
            for file in zip_ref.filelist:
                if not os.path.exists(file.filename):
                    zip_ref.extract(file, out)
                if file.filename.endswith("ffmpeg") and (not file.is_dir()) and int(file.file_size) > 0:
                    ffmpeg_binary = file.filename
                    break

    else:
        ffmpeg_url = False
        logger.error("Unsupported system")
        return False

    filesize = os.path.getsize(ffmpeg_binary)
    logger.info("ffmpeg location on [{path}], size = [{size}]".format(
        path=ffmpeg_binary, size=filesize))

    return ffmpeg_binary


def ffmpeg_join_audio_video(video_path: str, audio_path: str, target: str = None, ffmpeg: str = None, skip: bool = True) -> str:
    final_path = None
    target = target or os.getcwd()
    ffmpeg = ffmpeg or "ffmpeg"

    if video_path and os.path.exists(video_path) and audio_path and os.path.exists(audio_path):
        base = os.path.basename(video_path)
        name, ext = os.path.splitext(base)
        filename = to_unicode(safe_filename(name))
        final_path = os.path.join(
            target, f"{filename}_HQ{ext}"
        )
        if not all([os.path.exists(final_path), skip]):
            if ext.lower() == '.webm':
                cmd = [ffmpeg, "-i", video_path, "-i", audio_path,
                       "-c:v", "copy", "-c:a", "libvorbis", "-strict experimental", final_path, "-y", ]
            else:
                cmd = [ffmpeg, "-i", video_path, "-i", audio_path,
                       "-codec", "copy", final_path, "-y", ]

            subprocess.call(cmd)

    return final_path


def ffmpeg_aac_convert_mp3(aac: str, sampling: str = None, abr: str = None, target: str = None, ffmpeg: str = None, skip: bool = True) -> str:
    final_path = None
    sampling = sampling or "44100"
    abr = abr or "192k"
    target = target or os.getcwd()
    ffmpeg = ffmpeg or "ffmpeg"

    if aac and os.path.exists(aac):
        base = os.path.basename(aac)
        name, _ = os.path.splitext(base)
        final_path = os.path.join(
            target, f"{name}.mp3"
        )
        if not all([os.path.exists(final_path), skip]):
            subprocess.call(  # nosec
                [ffmpeg, "-i", aac, "-vn", "-ar",
                    sampling, "-ac", "2", "-b:a", abr, final_path, "-y", ]
            )

    return final_path


def ffmpeg_join_audio_video_ex(youtube: YouTube, resolution: str, target: str = None, ffmpeg: str = None) -> None:
    """
    Decides the correct video stream to download, then calls _ffmpeg_downloader.

    :param YouTube youtube:
        A valid YouTube object.
    :param str resolution:
        YouTube video resolution.
    :param str target:
        Target directory for download
    """

    target = target or os.getcwd()
    ffmpeg = ffmpeg or "ffmpeg"
    video_stream = audio_stream = None

    if resolution == "best":
        highest_quality_stream = (
            youtube.streams.filter(progressive=False).order_by(
                "resolution").last()
        )
        mp4_stream = (
            youtube.streams.filter(progressive=False, subtype="mp4")
            .order_by("resolution")
            .last()
        )
        if highest_quality_stream.resolution == mp4_stream.resolution:
            video_stream = mp4_stream
        else:
            video_stream = highest_quality_stream
    else:
        video_stream = youtube.streams.filter(
            progressive=False, resolution=resolution, subtype="mp4"
        ).first()
        if not video_stream:
            video_stream = youtube.streams.filter(
                progressive=False, resolution=resolution
            ).first()

    audio_stream = youtube.streams.get_audio_only(video_stream.subtype)
    if not audio_stream:
        audio_stream = youtube.streams.filter(
            only_audio=True).order_by("abr").last()

    video_path = video_stream.download()
    audio_path = audio_stream.download()

    final_path = ffmpeg_join_audio_video(
        video_path, audio_path, target, ffmpeg)

    return video_path, audio_path, final_path

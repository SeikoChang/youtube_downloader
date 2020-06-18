#!/usr/bin/env python
# -*- coding: utf-8 -*-

# chcp 65001       #转换为utf-8代码页
# chcp 936           #转换为默认的gb

"""A simple command line application to download youtube videos."""
from __future__ import absolute_import
from __future__ import print_function

import sys
import os
import tempfile
import logging
import argparse
import time
import datetime
import gzip
import json
import io
import subprocess
import shutil
import ntpath
import re
import operator
import platform
from download_file import download_file as download_file
import zipfile
import ntpath
import contextlib
import lzma
import tarfile
import stat

from pytube import __version__
from pytube import YouTube
from pytube import Playlist
from pytube.helpers import regex_search
from pytube import cli

PY3K = sys.version_info >= (3, 0)
if PY3K:
    import urllib.request as urllib2
    import urllib.parse as urlparse
else:
    import urllib2
    import urlparse


logger = logging.getLogger(__name__)


def get_arguments():
    print(main.__doc__)

    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)
    defaultIni = '{name}.{ext}'.format(name=filename, ext='ini')
    defaultLog = "{name}.{ext}".format(name=filename, ext='log')

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('url', nargs='?', help=(
        'The YouTube /watch url'
    )
    )

    parser.add_argument('playlist', nargs='?', help=(
        'The YouTube playlist url, for example : "https://www.youtube.com/playlist?list={self.playlist_id}"'
    )
    )

    parser.add_argument(
        "-f", "--file", action="store", type=str, default=defaultIni, help=(
            "identify the file path stored The YouTube /watch url(s), default file name = \"%s\"" % defaultIni
        )
    )

    parser.add_argument(
        "-lkp", "--listkeep", type=str2bool, nargs='?', const=False, default=False, help=(
            "identify if keep item in -f --file {file} after successfully download file"
        )
    )

    parser.add_argument(
        '-v', '--version', action='version', version='%(prog)s ' + __version__, help=(
            'Get current version of Pytube'
        )
    )

    parser.add_argument(
        '-t', '--itag', type=int, default=18, help=(
            'The itag for the desired stream'
        )
    )

    parser.add_argument(
        '-l', '--list', action='store_true', help=(
            'The list option causes pytube cli to return a list of streams available to download'
        )
    )

    parser.add_argument(
        '-bpr', '--build-playback-report', action='store_true', help=(
            'Save the html and js to disk'
        )
    )

    parser.add_argument(
        "-o", "--out", action="store", type=str, help=(
            "identify the destnation folder/filename to store the file"
        )
    )

    parser.add_argument(
        "-rp", "--replace", type=str2bool, nargs='?', const=True, default=True, help=(
            "identify if replace the existed file with the same filename \
            or download new file with prefix file name, \
            this only be taken when skip = False"
        )
    )

    parser.add_argument(
        "-sp", "--skip", type=str2bool, nargs='?', const=True, default=True, help=(
            "identify if skip the existed file"
        )
    )

    parser.add_argument(
        "-r", "--retry", action="store", type=int, default=3, help=(
            "retry time when get file failed"
        )
    )

    parser.add_argument(
        "-lf", "--logfile", action="store", type=str, default=defaultLog, help=(
            "identify the log file name"
        )
    )

    parser.add_argument(
        "-ll", "--verbosity", type=str, default="DEBUG", choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help=(
            "identify output verbosity"
        )
    )

    parser.add_argument(
        "-q", "--quiet", type=str2bool, nargs='?', const=True, default=True, help=(
            "identify if enable the silent mode"
        )
    )

    parser.add_argument(
        "-x", "--proxy", action="store_true", help=(
            "set proxy use for downloading stream"
        )
    )

    parser.add_argument(
        "-qt", "--quality", default='NORMAL', const='NORMAL', nargs='?', type=str, choices=['HIGH', 'NORMAL', 'LOW', 'ALL'], help=(
            "choose the quality of video to download"
        )
    )

    parser.add_argument(
        "-m", "--mode", default='VIDEO_AUDIO', const='VIDEO_AUDIO', nargs='?', type=str, choices=['VIDEO_AUDIO', 'VIDEO', 'AUDIO', 'ALL'], help=(
            "choose only video/audio or video and audio together"
        )
    )

    parser.add_argument(
        "-cap", "--caption", action="store_false", help=(
            "download all available caption for all languages if available \
             or download specific language caption only"
        )
    )

    parser.add_argument(
        "-tar",
        "--target",
        action="store",
        type=str,
        default="Youtube",
        help=(
            "The output directory for the downloaded stream. "
            "Default is current working directory"
        ),
    )

    parser.add_argument(
        "-ff",
        "--ffmpeg",
        action="store",
        type=str,
        default=os.getcwd(),
        help=(
            "The output directory for the downloaded ffmpeg binary. "
            "Default is current working directory"
        ),
    )

    parser.add_argument(
        "-j",
        "--join",
        type=str2bool,
        nargs='?',
        default=True,
        const=True,
        help=(
            "join original best audio/video files"
        )
    )

    parser.add_argument(
        "-fkp",
        "--filekeep",
        type=str2bool,
        nargs='?',
        default=True,
        const=True,
        help=(
            "keep original audio/video files after joined"
        )
    )

    args = parser.parse_args(sys.argv[1:])
    print(args)
    if not (args.url or args.playlist or os.path.exists(args.file)):
        parser.print_help()
        open(defaultIni, mode='a+')

    return args


def set_logger(logfile=None, verbosity='WARNING', quiet=False):
    LogLevel = loglevel_converter(verbosity)
    formatter = '%(asctime)s:[%(process)d]:[%(levelname)s]: %(message)s'

    logging.basicConfig(
        level=LogLevel,
        format=formatter,
        datefmt='%a %b %d %H:%M:%S CST %Y'
    )

    logger = logging.getLogger(__name__)
    logger.handlers = []
    logger.setLevel(LogLevel)

    # new file handler
    if logfile:
        handler = logging.FileHandler(
            filename=logfile, mode='a+', encoding='utf-8', delay=True)
        handler.setLevel(LogLevel)
        # set logging format
        formatter = logging.Formatter(formatter)
        handler.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(handler)

    if quiet:
        logging.disable(logging.CRITICAL)
    else:
        logging.disable(logging.NOTSET)

    # module = sys.modules['__main__'].__file__
    # logger = logging.getLogger(module)

    return logger


def loglevel_converter(loglevel):
    numeric_level = getattr(logging, loglevel.upper(), logging.info)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return numeric_level


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


def download_ffmpeg(out=os.getcwd()):
    platform, arch = detect_platform()
    if platform.lower() == "windows":
        if arch.lower() == '32bit':
            ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/win32/static/ffmpeg-latest-win32-static.zip"
        elif arch.lower() == '64bit':
            ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/win64/static/ffmpeg-latest-win64-static.zip"
        ffmpeg = download_file(url=ffmpeg_url, out=out)
        logger.info("%s downloaded" % ffmpeg)
        with zipfile.ZipFile(ffmpeg, 'r') as zip_ref:
            zip_ref.extractall(out)
            for file in zip_ref.filelist:
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
                f.extractall(out)
                for member in f.members:
                    if member.name.endswith('ffmpeg') and int(member.size) > 0 and int(member.mode) == 493:
                        ffmpeg_binary = member.name
                        break

    elif platform.lower() == "darwin":
        ffmpeg_url = "https://ffmpeg.zeranoe.com/builds/macos64/static/ffmpeg-latest-macos64-static.zip"
        ffmpeg = download_file(url=ffmpeg_url, out=out)
        logger.info("%s downloaded" % ffmpeg)
        with zipfile.ZipFile(ffmpeg, 'r') as zip_ref:
            zip_ref.extractall(out)
            for file in zip_ref.filelist:
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


def is_watchUrl(string):
    rtv = False
    try:
        regex_search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", string, group=1)
        rtv = True
    except:
        rtv = False

    return rtv


def is_playList(string):
    return (f"playlist?list=" in string)


def build_playback_report(url):
    """Serialize the request data to json for offline debugging.
    :param str url:
        A valid YouTube watch URL.
    """
    yt = YouTube(url)
    d = datetime.datetime.now()
    ts = int(time.mktime(d.timetuple()))
    fp = os.path.join(
        os.getcwd(),
        'yt-video-{yt.video_id}-{ts}.json.tar.gz'.format(yt=yt, ts=ts),
    )

    js = yt.js
    watch_html = yt.watch_html
    vid_info = yt.vid_info

    with gzip.open(fp, 'wb') as fh:
        fh.write(
            json.dumps({
                'url': url,
                'js': js,
                'watch_html': watch_html,
                'video_info': vid_info,
            })
            .encode('utf8'),
        )


def display_streams(url):
    """Probe YouTube video and lists its available formats.
    :param str url:
        A valid YouTube watch URL.
    """
    streams = list()
    try:
        yt = YouTube(url)
        for stream in yt.streams:
            streams.append(stream)
            logger.debug(stream)
    except:
        logger.error('Unable to list all streams from Video = [%s]' % url)

    return streams


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


def display_progress_bar(bytes_received, filesize, ch='█', scale=0.55):
    """Display a simple, pretty progress bar.
    Example:
    ~~~~~~~~
    PSY - GANGNAM STYLE(강남스타일) MV.mp4
    ↳ |███████████████████████████████████████| 100.0%
    :param int bytes_received:
        The delta between the total file size (bytes) and bytes already
        written to disk.
    :param int filesize:
        File size of the media stream in bytes.
    :param ch str:
        Character to use for presenting progress segment.
    :param float scale:
        Scale multipler to reduce progress bar size.
    """
    _, columns = get_terminal_size()
    max_width = int(columns * scale)

    filled = int(round(max_width * bytes_received / float(filesize)))
    remaining = max_width - filled
    bar = ch * filled + ' ' * remaining
    percent = round(100.0 * bytes_received / float(filesize), 1)
    text = ' ↳ |{bar}| {percent}%\r'.format(bar=bar, percent=percent)
    sys.stdout.write(text)
    sys.stdout.flush()


def on_progress(stream, chunk, bytes_remaining):
    """On download progress callback function.
    :param object stream:
        An instance of :class:`Stream <Stream>` being downloaded.
    :param file_handle:
        The file handle where the media is being written to.
    :type file_handle:
        :py:class:`io.BufferedWriter`
    :param int bytes_remaining:
        How many bytes have been downloaded.
    """
    filesize = stream.filesize
    bytes_received = filesize - bytes_remaining
    display_progress_bar(bytes_received, filesize)


def get_correct_yt(url):
    yt = None
    # Get Youtube Object with correct filename

    if args.proxy:
        logger.info('via proxy = [%s]' % args.proxy)
        proxy_params = {urlparse.urlparse(args.url).scheme: args.proxy}
    else:
        proxy_params = None

    for i in range(1, args.retry+1):
        try:
            yt = YouTube(
                url, on_progress_callback=on_progress, proxies=proxy_params)
            filename = to_unicode(yt.streams.first().default_filename)
            if 'YouTube' not in filename:
                break
        except Exception as ex:
            logger.error('Unable to get FileName from = [%s]' % url)
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger.error('Due to the reason = [%s]' % message)

    return yt


def _download(yt, itag=18, out=None, replace=True, skip=True, proxies=None, retry=10):
    """Start downloading a YouTube video.
    :param str url:
        A valid YouTube watch URL.
    :param str itag:
        YouTube format identifier code.
    """

    thumbnail_url = yt.thumbnail_url
    stream = yt.streams.get_by_itag(itag)
    filesize = stream.filesize
    filename = to_unicode(stream.default_filename)
    logger.info('Youtube filename = [%s]' % filename)
    logger.info('Youtube filesize = [%s]' % filesize)
    logger.info('\n{title} |\n{description} |\n\n{views} views | {rating} rating | {length} secs'.format(
        title=yt.title,
        description=yt.description,
        views=yt.views,
        rating=yt.rating,
        length=yt.length,
        thumbnail_url=yt.thumbnail_url
    ))
    print('\n{title} |\n{description} |\n\n{views} views | {rating} rating | {length} secs'.format(
        title=yt.title,
        description=yt.description,
        views=yt.views,
        rating=yt.rating,
        length=yt.length,
        thumbnail_url=yt.thumbnail_url
    ))
    print('\n{fn} | {fs} bytes'.format(
        fn=filename,
        fs=filesize
    ))

    # detect of out is a directory
    outdir = None
    if out:
        if os.path.isdir(out):
            outdir = out
            out = None
        else:
            filename = out
    if outdir:
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        filename = os.path.join(outdir, filename)
    filename = to_unicode(filename)

    # check file existance and decide skip or not
    # add numeric ' (x)' suffix if filename already exists
    if os.path.exists(filename):
        fsize = os.path.getsize(filename)
        logger.info(
            'filename = [%s] filesize = [%s] already exists in system' % (filename, fsize))
        if fsize == filesize:
            if skip:
                logger.info('filename = [%s] filesize = [%s] already exists in system and skip download again' % (
                    filename, fsize))
                return filename, thumbnail_url
            elif not replace:
                filename = filename_fix_existing(filename)
        else:
            name, ext = os.path.splitext(filename)
            filename = filename_fix_existing(filename)
            # TODO this workaround, need remove after
            # give second chance
            if skip:
                try:
                    oldfilename = u'{}{}{}'.format(name, '_(1)', ext)
                    fsize = os.path.getsize(oldfilename)
                    logger.debug('Trying to check filename = [%s] and filesize = [%s] if exists and match' % (
                        oldfilename, fsize))
                    if fsize == filesize:
                        logger.info('filename = [%s] filesize = [%s] already exists in system and skip download again' % (
                            oldfilename, fsize))
                        return oldfilename, thumbnail_url
                except:
                    pass

    name, ext = os.path.splitext(filename)
    logger.info('target local filename = [%s]' % filename)
    logger.info('target local filesize = [%s]' % filesize)

    # create tmp file
    (fd, tmpfile) = tempfile.mkstemp(
        suffix=ext, prefix="", dir=outdir, text=False)
    tmpfile = to_unicode(tmpfile)
    os.close(fd)
    os.unlink(tmpfile)
    logger.info('target local tmpfile  = [%s]' % tmpfile)
    tmppath, tmpbase = ntpath.split(tmpfile)
    tmpname, tmpext = os.path.splitext(tmpbase)

    try:
        stream.download(output_path=tmppath, filename=tmpname,
                        filename_prefix=None, skip_existing=skip)
        sys.stdout.write('\n')
        shutil.move(tmpfile, filename)
        logger.info("File = [{0}] Saved".format(filename))
    except KeyboardInterrupt:
        sys.exit(1)

    sys.stdout.write('\n')
    return (filename, thumbnail_url)


def get_captions(yt, lang):
    if lang:
        filename = to_unicode(yt.streams.first().default_filename)
        codes = query_captions_codes(yt)
        for code in codes:
            if (lang == True) or (code.lower() == lang.lower()):
                logger.info(
                    'downloading captions for language code = [%s]' % code)
                filepath = yt.captions[code].download(
                    title=filename, srt=True, output_path=args.target)
                logger.info(
                    'captions downloaded = [%s]' % filepath)

    return True


def query_captions_codes(yt):
    codes = list()
    captions = yt.captions
    logger.debug('captions = %s' % captions)
    for caption in captions:
        logger.debug('caption = %s' % caption)
        code = caption.code
        logger.debug('code = [%s]' % code)
        codes.append(code)

    return codes


def get_url_list(args):
    downloads = list()
    if args.url:
        if args.itag:
            downloads.append(args.url)
    elif args.playlist:
        playlist = Playlist(args.playlist)
        for video in playlist:
            # video.streams.get_highest_resolution().download()
            downloads.append(video)
    elif args.file:
        with open(args.file, "r") as fp:
            for line in fp:
                if is_watchUrl(line):
                    downloads.append(line)
                elif is_playList(line):
                    playlist = Playlist(line)
                    for video in playlist:
                        downloads.append(video + '\n')

        logger.debug('All required download URLs = %s' % downloads)
        with open(args.file, "w") as f:
            for url in downloads:
                f.write(url)

    return downloads


def get_target_itags(yt, quality='NORMAL', mode='VIDEO_AUDIO'):
    itags = list()
    itags.append(18)

    start = time.time()
    if mode.upper() == 'VIDEO_AUDIO':
        streams = yt.streams.filter(
            progressive=True).order_by('itag')
    elif mode.upper() == 'VIDEO':
        streams = yt.streams.filter(only_video=True).order_by('itag')
    elif mode.upper() == 'AUDIO':
        streams = yt.streams.filter(only_audio=True).order_by('itag')
    elif mode.upper() == 'ALL':
        streams = yt.streams
    else:
        return itags

    end_streams = time.time()
    logger.debug("take = [{time}] secs".format(time=end_streams-start))

    rank = {
        stream.itag: stream.filesize for stream in streams if isinstance(stream.filesize, int)}
    end_rank = time.time()
    logger.debug("generate rank take = [{time}] secs".format(
        time=end_rank-start))
    logger.debug(rank)

    # block below temporary because the performance is the same same comparing above one line sentence.
    # rank = dict()
    # for itag in streams.itag_index:
    #    itag_filesize = streams.itag_index[itag].filesize
    #    if isinstance(itag_filesize, int):
    #        rank[itag] = int(itag_filesize)
    #    end_stream = time.time()
    #    logger.debug("take = [{time}] secs".format(time=end_stream-start))
    # end_rank = time.time()
    # logger.debug("generate rank take = [{time}] secs".format(time=end_rank-start))
    # logger.debug(rank)

    sorted_rank = sorted(rank.items(), key=operator.itemgetter(1))
    logger.debug(sorted_rank)

    if quality.upper() == 'HIGH':
        itags = [sorted_rank[-1][0]]
    elif quality.upper() == 'NORMAL':
        itags = [median(sorted_rank)[0]]
    elif quality.upper() == 'LOW':
        itags = [sorted_rank[0][0]]
    elif quality.upper() == 'ALL':
        itags = [itag[0] for itag in sorted_rank]
    else:
        return itags

    end = time.time()
    logger.debug(
        "get_target_itags() take = [{time}] secs".format(time=end-start))

    return itags


def update_item_in_file(file, item):
    with open(file, "r") as f:
        lines = f.readlines()
    with open(file, "w") as f:
        for line in lines:
            if line != item:
                f.write(line)


def download_youtube_by_itag(yt, itag):
    filepath = None
    try:
        url = yt.watch_url
        stream = yt.streams.get_by_itag(itag)
        title = stream.title
        resolution = stream.resolution
        video_codec = stream.video_codec
        abr = stream.abr
        audio_codec = stream.audio_codec
        fps = stream.fps
        bitrate = stream.bitrate
        filesize = stream.filesize
        filename = '{title}_{video}_{video_codec}_{audio}_{audio_codec}_{fps}_{bitrate}_{filesize}'.format(
            title=title, video=resolution, video_codec=video_codec, audio=abr, audio_codec=audio_codec, fps=fps, bitrate=bitrate, filesize=filesize)

        filepath = yt.streams.get_by_itag(itag).download(
            output_path=args.target, filename=filename)
    except:
        logger.error("Unable to download YT, url = [{url}], itag = [{itag}".format(url=url, itag=itag))
    return filepath


def ffmpeg_process(youtube: YouTube, resolution: str, target: str = None, ffmpeg: str = "ffmpeg") -> None:
    """
    Decides the correct video stream to download, then calls _ffmpeg_downloader.

    :param YouTube youtube:
        A valid YouTube object.
    :param str resolution:
        YouTube video resolution.
    :param str target:
        Target directory for download
    """
    youtube.register_on_progress_callback(on_progress)
    target = target or os.getcwd()

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
    if video_stream is None:
        print(f"Could not find a stream with resolution: {resolution}")
        print("Try one of these:")
        display_streams(youtube)
        sys.exit()

    audio_stream = youtube.streams.get_audio_only(video_stream.subtype)
    if not audio_stream:
        audio_stream = youtube.streams.filter(
            only_audio=True).order_by("abr").last()
    if not audio_stream:
        print("Could not find an audio only stream")
        sys.exit()

    video_path = audio_path = final_path = None
    video_path = download_youtube_by_itag(youtube, video_stream.itag)
    audio_path = download_youtube_by_itag(youtube, audio_stream.itag)
    if all([video_path, audio_path]):
        final_path = os.path.join(
            target, f"{video_stream.title}_HQ.{video_stream.subtype}"
        )
        subprocess.run(  # nosec
            [ffmpeg, "-i", video_path, "-i", audio_path,
                "-codec", "copy", final_path, "-y", ]
        )

    return video_path, audio_path, final_path


def main():
    start = time.time()
    """Command line application to download youtube videos."""
    logger = set_logger(logfile=args.logfile,
                        verbosity=args.verbosity, quiet=args.quiet)
    logger.debug('System out encoding = [%s]' % sys.stdout.encoding)

    if not (args.url or args.playlist or os.path.exists(args.file)):
        sys.exit(1)

    downloads = list()
    if args.list:
        display_streams(args.url)

    if args.build_playback_report:
        build_playback_report(args.url)

    if args.file or args.playlist or args.file:
        downloads = get_url_list(args)
        for url in downloads:
            start_url = time.time()
            logger.info("Trying to download URL = {url}".format(url=url))
            for i in range(1, args.retry+1):
                yt = get_correct_yt(url)
                if not yt:
                    continue
                logger.info("Title = {title}".format(title=yt.title))
                get_captions(yt, args.caption)

                itags = get_target_itags(
                    yt=yt, quality=args.quality, mode=args.mode)

                logger.debug("itag list = {itags}".format(itags=itags))

                # download target youtube
                for i, itag in enumerate(itags):
                    start_itag = time.time()
                    filepath = download_youtube_by_itag(yt, itag)
                    if filepath:
                        logger.info(
                            "Successfully download to {filepath}".format(filepath=filepath))

                    end_itag = time.time()
                    duration = end_itag - start_itag
                    logger.debug(
                        ("URL processing finished, execution in [%s] seconds") % (duration))

                # update items in ini file
                else:
                    # join video/audio if required
                    if args.join:
                        ffmpeg_binary = download_ffmpeg()
                        os.chmod(ffmpeg_binary, stat.S_IRWXU |
                                 stat.S_IRWXG | stat.S_IRWXO)
                        #copyfile(ffmpeg_binary, "ffmpeg")
                        video_path, audio_path, final_path = ffmpeg_process(
                            yt, "best", args.target, ffmpeg_binary)
                        if not args.filekeep:
                            os.unlink(video_path)
                            os.unlink(audio_path)

                    if args.file and (not args.listkeep):
                        update_item_in_file(args.file, item=url)

                # break retry level here
                break

            # failed after retry multiple times
            else:
                logger.fatal(
                    "Download Youtube Video/Audio from URL = [{url}] FAILED".format(url=url))

            end_url = time.time()
            duration = end_url - start_url
            logger.debug(
                ("URL processing finished, execution in [%s] seconds") % (duration))

        # finish all downloads
        else:
            logger.info(
                "Download all Youtube Video/Audio, there are total URLs = {urls} to be processed".format(urls=len(downloads)))

    end = time.time()
    duration = end - start
    logger.info(
        ("Script Running Finished, Execution in [%s] Seconds") % (duration))

    return True


def unitest():
    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)
    test_file = '{name}.{ext}_unittest'.format(name=filename, ext='ini')

    # url = 'https://www.youtube.com/watch?v=F1fqet9V494'
    url = 'https://www.youtube.com/watch?v=xwsYvBYZcx4'
    playlist = 'https://www.youtube.com/playlist?list=PLteWjpkbvj7rUU5SFt2BlNVCQqkjulPZR'

    def test1():
        logger.info(
            "Testing with 'display_streams()' for url =  {0}".format(url))
        args.list = True
        main()

    def test2():
        logger.info(
            "Testing with 'build_playback_report()' for url = {0}".format(url))
        args.build_playback_report = True
        main()

    def test3():
        logger.info(
            "Testing with 'get_captions(lang=zh-TW)' for url = {0}".format(url))
        args.caption = 'zh-TW'
        main()
        logger.info(
            "Testing with 'get_captions(lang=True)' for url = {0}".format(url))
        args.caption = True
        main()

    def test4():
        logger.info("Testing with download file from ini file")
        main()

    def test5():
        logger.info("Testing with download all files from ini file")
        args.replace = True
        args.quality = 'All'
        args.mode = 'ALL'
        main()

    def test6():
        logger.info("Testing with downloading playlist from input")
        args.replace = False
        args.skip = True
        args.playlist = playlist
        main()

    args.url = url
    test3()
    test2()
    test1()
    args.url = None
    args.file = test_file
    fp = to_unicode(args.file)
    with open(fp, mode='w+') as fh:
        fh.write(url)
    test4()
    test5()

    test6()
    with open(fp, mode='w+') as fh:
        fh.write(playlist)
    test4()


if __name__ == "__main__":  # Only run if this file is called directly
    args = get_arguments()
    # unitest()
    main()
    # download_ffmpeg()
    # sys.exit(main())

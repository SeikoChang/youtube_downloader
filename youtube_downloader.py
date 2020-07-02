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
import zipfile
import contextlib
import lzma
import tarfile
import stat

from urllib.parse import parse_qs

from pytube import __version__
from pytube import request, YouTube
from pytube import Playlist
from pytube.helpers import regex_search
from pytube import cli
from pytube.helpers import cache, deprecated, install_proxy, uniqueify
from pytube.helpers import safe_filename

from download_file import download_file as download_file
from helpers import get_terminal_size_windows
from helpers import get_terminal_size_stty
from helpers import get_terminal_size_tput
from helpers import get_terminal_size
from helpers import detect_platform
from helpers import fib
from helpers import symlink
from helpers import copyfile
from helpers import median
from helpers import unzip_without_overwrite
from helpers import filename_fix_existing
from helpers import to_unicode
from helpers import str2bool
from helpers import download_ffmpeg
from helpers import ffmpeg_join_audio_video
from helpers import ffmpeg_aac_convert_mp3


PY3K = sys.version_info >= (3, 0)
if PY3K:
    import urllib.request as urllib2
    import urllib.parse as urlparse
else:
    import urllib2
    import urlparse


base = os.path.basename(__file__)
filename, file_extension = os.path.splitext(base)
defaultIni = '{name}.{ext}'.format(name=filename, ext='ini')
defaultLog = "{name}.{ext}".format(name=filename, ext='log')

logger = logging.getLogger(__name__)


def get_arguments():
    print(main.__doc__)

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('url', nargs='?', help=(
        'The YouTube /watch url, for example : "https://www.youtube.com/watch?v=yWebbSWPG4g"'
    )
    )

    parser.add_argument('playlist', nargs='?', help=(
        'The YouTube playlist url, for example : "https://www.youtube.com/playlist?list=PLohb4k71XnPaQRTvKW4Uii1oq-JPGpwWF"'
    )
    )

    parser.add_argument('channel', nargs='?', help=(
        'The YouTube playlist url, for example : "https://www.youtube.com/channel/UCFdTiwvDjyc62DBWrlYDtlQ"'
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
        "-q", "--quiet", type=str2bool, nargs='?', const=False, default=False, help=(
            "identify if enable the silent mode"
        )
    )

    parser.add_argument(
        "-x", "--proxy", action="store_true", help=(
            "set proxy use for downloading stream"
        )
    )

    parser.add_argument(
        "-qt", "--quality", default='HIGH', const='HIGH', nargs='?', type=str, choices=['HIGH', 'NORMAL', 'LOW', 'ALL'], help=(
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

    parser.add_argument(
        "-c",
        "--convert",
        type=str2bool,
        nargs='?',
        default=True,
        const=True,
        help=(
            "convert aac to mp3"
        )
    )

    args = parser.parse_args(sys.argv[1:])
    print(args)
    if not any([args.url, args.playlist, args.channel, os.path.exists(args.file)]):
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


def is_channel(string):
    # example, https://www.youtube.com/channel/UCFdTiwvDjyc62DBWrlYDtlQs
    try:
        regex_search(r"(channel/)([0-9A-Za-z_-]{24}).*", string, group=1)
        return True
    except:
        return False

    # return (f"channel" in string)


def is_playList(string):
    # return (f"playlist?list=" in string)
    # example, https://www.youtube.com/playlist?list=PL-g0fdC5RMboYEyt6QS2iLb_1m7QcgfHk
    try:
        regex_search(
            r"(playlist\?list=)([0-9A-Za-z_-]{24,34}).*", string, group=1)
        return True
    except:
        return False


def is_watchUrl(string):
    # - :samp:`https://youtube.com/watch?v={video_id}`
    # - :samp:`https://youtube.com/embed/{video_id}`
    # - :samp:`https://youtu.be/{video_id}`
    try:
        regex_search(r"(?:v=|/)([0-9A-Za-z_-]{11}).*", string, group=1)
        return True
    except:
        return False


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


def remove_item_in_file(file, item):
    if file and os.path.exists(file):
        with open(file, "r") as f:
            lines = f.readlines()
        with open(file, "w") as f:
            for line in lines:
                if line.strip('\n') != item:
                    f.write(line)


def get_correct_yt(url, retry):
    yt = None
    # Get Youtube Object with correct filename

    if args.proxy:
        logger.info('via proxy = [%s]' % args.proxy)
        proxy_params = {urlparse.urlparse(args.url).scheme: args.proxy}
    else:
        proxy_params = None

    for i in range(1, retry+100+1):
        logger.debug(f"{i} retry in get_correct_yt()")
        try:
            filename = None
            #while filename in [None, "YouTube"]:
            yt = YouTube(
                url, on_progress_callback=on_progress, proxies=proxy_params)
            filename = to_unicode(safe_filename(yt.title))
            logger.debug("URL      = {url}".format(url=url))
            logger.debug("Filename = {filename}".format(filename=filename))
            if filename != 'YouTube':
                break

        except Exception as ex:
            logger.error('Unable to get FileName from = [%s]' % url)
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(ex).__name__, ex.args)
            logger.error('Due to the reason = [%s]' % message)
    else:
        logger.error(
            "Unable to get correct YouTube object for {retry} times, skip download this time".format(retry=args.retry))
        yt = None

    return yt


def get_videos_from_channel(url):
    videos = list()

    try:
        channel_id: str = regex_search(
            r"(?:channel|\/)([0-9A-Za-z_-]{24}).*", url, group=1)
    except IndexError:  # assume that url is just the id
        channel_id = url

    channel_url = f"https://www.youtube.com/channel/{channel_id}/videos"
    html = request.get(channel_url)

    video_regex = re.compile(r"href=\"(/watch\?v=[\w-]*)")
    videos = uniqueify(video_regex.findall(html))

    videos = [f"https://www.youtube.com{video_id}" for video_id in videos]

    return videos


def get_correct_videos_from_channel(url, retry):
    videos = list()
    i = 1
    while len(videos) == 0:
        videos = get_videos_from_channel(url)

        logger.debug(f"{i} retry in get_correct_videos_from_channel()")
        #logger.info(fib(i))
        i+=1
        if i > retry+100: break

    logger.info('channel = {url}'.format(url=url))
    logger.info('{videos} Videos found from channel'.format(videos=len(videos)))

    return videos


def get_videos_from_playlist(url):
    videos = list()
    playlist = Playlist(url)
    title = playlist.title()
    for video in playlist:
        # video.streams.get_highest_resolution().download()
        videos.append(f"{video}")

    return videos, title


def get_correct_videos_from_playlist(url, retry):
    videos = list()
    title = None
    i = 1
    while len(videos) == 0 or title == None:
        videos, title = get_videos_from_playlist(url)

        logger.debug(f"{i} retry in get_correct_videos_from_playlist()")
        #logger.info(fib(i))
        i+=1
        if i > retry+100: break

    logger.info('Playlist = {url}'.format(url=url))
    logger.info('Title = {title}'.format(title=title))
    logger.info('{videos} Videos found from playlist'.format(videos=len(videos)))

    return uniqueify(videos)


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
    logger.debug(f'target local tmpfile name = [{tmpname}], ext = [{tmpext}]')

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
        filename = to_unicode(safe_filename(yt.title))
        codes = query_captions_codes(yt)
        for code in codes:
            if (lang == True) or (code.lower() == lang.lower()):
                # logger.info('downloading captions for language code = [%s]' % code)
                try:
                    filepath = yt.captions[code].download(
                        title=filename, srt=True, output_path=args.target)
                    logger.info(
                        'captions language code = [{code}] downloaded [{filepath}]'.format(code=code, filepath=filepath))
                except:
                    logger.error(
                        'unable to download caption code = [{code}'.format(code=code))

    return True


def query_captions_codes(yt):
    codes = list()
    captions = yt.captions
    logger.debug('captions = %s' % captions)
    for caption in captions:
        # logger.debug('caption = %s' % caption)
        code = caption.code
        # logger.debug('code = [%s]' % code)
        codes.append(code)

    return codes


def get_url_list_from_file(file, retry):
    file = file or defaultIni
    downloads = list()
    urls = list()

    if file and os.path.exists(file):
        with open(file, "r") as fp:
            for line in fp:
                downloads.append(line.strip('\n'))

        downloads = uniqueify(downloads)
        with open(file, "w") as f:
            for url in downloads:
                f.write(f"{url}\n")

        for url in downloads:
            urls += get_url_by_item(url, retry)

        urls = uniqueify(urls)
        with open(file, "w") as f:
            for url in urls:
                f.write(f"{url}\n")

    return urls


def get_url_list(args):
    downloads = list()
    if args.url:
        downloads.append(args.url)
    elif args.playlist:
        downloads = get_correct_videos_from_playlist(args.playlist, args.retry)
    elif args.file and os.path.exists(args.file):
        downloads = get_url_list_from_file(args.file, args.retry)

    logger.debug('All required download URLs = %s' % downloads)

    return downloads


def get_url_by_item(item, retry):
    downloads = list()

    if is_channel(item):
        logger.debug("[%s] is_channel" % item)
        videos = get_correct_videos_from_channel(item, retry)
        downloads += videos
    elif is_playList(item):
        logger.debug("[%s] is_playList" % item)
        videos = get_correct_videos_from_playlist(item, retry)
        downloads += videos
    elif is_watchUrl(item):
        logger.debug("[%s] is_watchUrl" % item)
        downloads.append(item)

    return downloads


def get_target_itags(yt, quality='NORMAL', mode='VIDEO_AUDIO'):
    itags = list()
    itags.append(18)

    start = time.time()
    if mode.upper() == 'VIDEO_AUDIO':
        streams = yt.streams.filter(
            progressive=True).order_by('resolution').desc()
    elif mode.upper() == 'VIDEO':
        streams = yt.streams.filter(
            only_video=True).order_by('resolution').desc()
    elif mode.upper() == 'AUDIO':
        streams = yt.streams.filter(
            only_audio=True, subtype='mp4').order_by('abr').desc()
    elif mode.upper() == 'ALL':
        streams = yt.streams
    else:
        return itags

    end_streams = time.time()
    logger.debug("take = [{time}] secs".format(time=end_streams-start))

    rank = {
        stream.itag: stream.filesize_approx for stream in streams if isinstance(stream.filesize_approx, int)}
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

    if quality.upper() == 'BEST':
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


def download_youtube_by_itag(yt, itag, target):
    target = target or os.getcwd()
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
        filename = to_unicode(safe_filename(filename))
        logger.debug("Filename = {filename}".format(filename=filename))

        yt.register_on_progress_callback(on_progress)
        filepath = yt.streams.get_by_itag(itag).download(
            output_path=target, filename=filename)
    except:
        logger.error("Unable to download YT, url = [{url}], itag = [{itag}]".format(
            url=url, itag=itag))

    return filepath


def download_youtube_by_url_list(file, urls, caption, quality, mode, target, join, filekeep, listkeep, convert, retry):
    file = file or defaultIni

    if join or convert:
        ffmpeg_binary = download_ffmpeg()
        os.chmod(ffmpeg_binary, stat.S_IRWXU |
                 stat.S_IRWXG | stat.S_IRWXO)
        # copyfile(ffmpeg_binary, "ffmpeg")

    for url in urls:
        start_url = time.time()
        logger.info("Trying to download URL = {url}".format(url=url))
        for _ in range(1, retry+1):
            yt = get_correct_yt(url, retry)
            if not yt:
                continue

            logger.info("Title = {title}".format(title=yt.title))
            logger.info("Description = {description}".format(
                description=yt.description))
            logger.info("Views = {views}".format(views=yt.views))
            logger.info("Rating = {rating}".format(rating=yt.rating))
            logger.info("Length = {length}".format(length=yt.length))
            logger.info("Thumbnail_url = {thumbnail_url}".format(
                thumbnail_url=yt.thumbnail_url))

            get_captions(yt, caption)

            itags = get_target_itags(
                yt=yt, quality=quality, mode=mode)

            logger.debug("itag list = {itags}".format(itags=itags))

            # download target youtube
            for _, itag in enumerate(itags):
                start_itag = time.time()
                stream = yt.streams.get_by_itag(itag)
                logger.info("Filesize = {filesize}".format(
                    filesize=stream.filesize))

                filepath = download_youtube_by_itag(yt, itag, target)
                if filepath:
                    logger.info(
                        "Successfully download to {filepath}".format(filepath=filepath))

                    if convert:
                        try:
                            mp3 = ffmpeg_aac_convert_mp3(
                                aac=filepath, target=target)
                            logger.info(
                                "Successfully {filepath} convert to {mp3}".format(filepath=filepath, mp3=mp3))
                        except:
                            logger.warning(
                                "Unable to convert {filepath} to mp3 file".format(
                                    filepath=filepath)
                            )

                end_itag = time.time()
                duration = end_itag - start_itag
                logger.debug(
                    "URL = [{url}] processing finished".format(url=url))
                logger.debug(
                    "Execution in [{duration}] seconds with filesize [{filesize}]".format(duration=duration, filesize=stream.filesize))

                logger.debug(
                    "Average speed = [{avg} Mbps]".format(avg=stream.filesize/8/1024/duration))

            # update items in ini file
            else:
                # join video/audio if required
                if join:
                    video_itag = get_target_itags(yt=yt, quality='BEST', mode='VIDEO')
                    video_path = download_youtube_by_itag(yt=yt, itag=video_itag[0], target=target)
                    audio_itag = get_target_itags(yt=yt, quality='BEST', mode='AUDIO')
                    audio_path = download_youtube_by_itag(yt=yt, itag=audio_itag[0], target=target)

                    join_path = ffmpeg_join_audio_video(video_path=video_path, audio_path=audio_path, target=target, ffmpeg=ffmpeg_binary)
                    logger.info(join_path)
                    logger.info("[{join_path}] Joint to HQ vidoe Successfully".format(join_path=join_path))

                if convert:
                    mp3 = ffmpeg_aac_convert_mp3(aac=audio_path, target=target, ffmpeg=ffmpeg_binary)
                    logger.info(audio_path)
                    logger.info("[{mp3}] Covert to mp3 Successfully".format(mp3=mp3))

                if any([join, convert]) and not filekeep:
                    os.unlink(video_path)
                    os.unlink(audio_path)

                if file and os.path.exists(file) and (not listkeep):
                    remove_item_in_file(file, item=url)

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
            "Download all Youtube Video/Audio, there are total URLs = {urls} to be processed".format(urls=len(urls)))

    return True


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

    if any([args.url, args.playlist, args.channel, os.path.exists(args.file)]):
        downloads = get_url_list(args)
        download_youtube_by_url_list(
            args.file, downloads, args.caption, args.quality, args.mode, args.target, args.join, args.filekeep, args.listkeep, args.convert, args.retry)

    end = time.time()
    duration = end - start
    logger.info(
        ("Script Running Finished, Execution in [%s] Seconds") % (duration))

    return True


def unitest():
    base = os.path.basename(__file__)
    filename, _ = os.path.splitext(base)
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

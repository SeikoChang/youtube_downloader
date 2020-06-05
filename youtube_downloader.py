#!/usr/bin/env python
# -*- coding: utf-8 -*-

#chcp 65001       #转换为utf-8代码页
#chcp 936           #转换为默认的gb

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

from pytube import __version__
from pytube import YouTube

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

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('url', nargs='?', help=(
        'The YouTube /watch url'
        )
    )

    parser.add_argument(
        "-f", "--file", action="store", type=str, default='{name}.{ext}'.format(name=filename, ext='ini'), help=(
            "identify the file path stored The YouTube /watch url(s), default file name = \"{name}.{ext}\"".format(name=filename, ext='ini')
        )
    )

    parser.add_argument(
        "-lkp", "--listkeep", type=str2bool, nargs='?', const=False, help=(
            "idenfify if keep item in -f --file {file} after successfully download file"
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
        "-rp", "--replace", type=str2bool, nargs='?', const=True, help=(
            "idenfify if replace the existed file with the same filename \
            or download new file with prefix file name, \
            this only be taken when skip = False"
        )
    )

    parser.add_argument(
        "-sp", "--skip", type=str2bool, nargs='?', const=True, help=(
            "idenfify if skip the existed file"
        )
    )

    parser.add_argument(
        "-r", "--retry",action="store", type=int, default=1, help=(
            "retry time when get file failed"
        )
    )

    parser.add_argument(
        "-lf", "--logfile", action="store", type=str, default="{name}.{ext}".format(name=filename, ext='log'), help=(
            "identify the log file name"
        )
    )

    parser.add_argument(
        "-ll", "--verbosity", type=str, default="DEBUG", choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help=(
            "identify output verbosity"
        )
    )

    parser.add_argument(
        "-q", "--quiet", type=str2bool, nargs='?', const=True, help=(
            "idenfify if enable the silent mode"
        )
    )

    parser.add_argument(
        "-x", "--proxy", action="store_true", help=(
            "set proxy use for downloading stream"
        )
    )

    parser.add_argument(
        "-qt", "--quality", type=str, choices=['HIGH', 'NORMAL', 'LOW', 'ALL'], help=(
            "choose the quality of video to download"
        )
    )

    parser.add_argument(
        "-m", "--mode", type=str, choices=['VIDEO_AUDIO', 'VIDEO', 'AUDIO', 'ALL'], help=(
            "choose only video/audio or video and audio together"
        )
    )

    parser.add_argument(
        "-cap", "--caption", action="store_true", help=(
            "download all available cpation for all languages if available \
             or download specific language caption only"
        )
    )

    parser.set_defaults(listkeep=False)
    parser.set_defaults(replace=True)
    parser.set_defaults(skip=True)
    parser.set_defaults(quiet=False)
    args = parser.parse_args(sys.argv[1:])
    print(args)
    if not (args.url or os.path.exists(args.file)):
        parser.print_help()
        base = os.path.basename(__file__)
        filename, file_extension = os.path.splitext(base)
        inputfile = '{name}.{ext}'.format(name=filename, ext='ini')
        open(inputfile, mode='a+')

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
        handler = logging.FileHandler(filename=logfile, mode='a+', encoding='utf-8', delay=True)
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

    #module = sys.modules['__main__'].__file__
    #logger = logging.getLogger(module)

    return logger


def loglevel_converter(loglevel):
    numeric_level = getattr(logging, loglevel.upper(), logging.info)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return numeric_level


def median(lst):
    #sortedLst = sorted(lst)
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
    indexes  = [int(x) for x in suffixes
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


def get_captions(url, lang):
    captions = None
    try:
        yt = YouTube(url)
        captions = yt.captions.all()
        logger.info('captions = %s' % captions)
        p = re.compile('<Caption lang=".*" code="(.*)">')
        for caption in captions:
            result = p.search(str(caption))
            if result:
                code = result.group(1)
                if (lang == True) or (code.lower() == lang.lower()):
                    logger.debug('captions code = [%s]' % code)
                    cap = caption.generate_srt_captions()
                    filename = yt.streams.first().default_filename
                    name, ext = os.path.splitext(filename)
                    fp = to_unicode('{}_{}.txt'.format(name, code))
                    with open(fp, 'wb') as fh:
                        fh.write(cap.encode('utf8'))
    except:
        logger.warning('no any captions found!')

    return captions


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
    streams = []
    try:
        yt = YouTube(url)
        for stream in yt.streams.all():
            streams.append(stream)
            print(stream)
    except:
        logger.error('Unable to list all streams from Video = [%s]' % url)

    return streams


def get_target_itags(url, quality='NORMAL', mode='VIDEO_AUDIO'):
    itags = [18]
    yt = YouTube(url)
    if mode and quality:
        if mode.upper() == 'VIDEO_AUDIO':
            streams = yt.streams.filter(progressive=True).order_by('itag').all()
        elif mode.upper() == 'VIDEO':
            streams= yt.streams.filter(only_video=True).order_by('itag').all()
        elif mode.upper() == 'AUDIO':
            streams = yt.streams.filter(only_audio=True).order_by('itag').all()
        elif mode.upper() == 'ALL':
            streams = yt.streams.all()
        else:
            return itags

        p = re.compile('.*itag=\"(.*)\" mime_type=.*')
        rank = {}
        for stream in streams:
            filesize = stream.filesize
            result = p.search(str(stream))
            if result:
                itag = result.group(1)
                rank[itag] = int(filesize)

        sorted_rank = sorted(rank.items(), key=operator.itemgetter(1))

        if quality.upper() == 'HIGH':
            itags = [sorted_rank[-1][0]]
        elif quality.upper() == 'NORMAL':
            itags = [median(sorted_rank)[0]]
        elif quality.upper() == 'LOW':
            itags = [sorted_rank[0][0]]
        elif quality.upper() == 'ALL':
            itags = rank.keys()
        else:
            return itags

    return itags


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


def on_progress(stream, chunk, file_handle, bytes_remaining):
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


def download(url, itag=18, out=None, replace=True, skip=True, proxies=None):
    """Start downloading a YouTube video.
    :param str url:
        A valid YouTube watch URL.
    :param str itag:
        YouTube format identifier code.
    """
    # TODO(nficano): allow download target to be specified
    # TODO(nficano): allow dash itags to be selected
    yt = YouTube(url, on_progress_callback=on_progress, proxies=proxies)
    stream = yt.streams.get_by_itag(itag)
    filename = to_unicode(stream.default_filename)
    thumbnail_url = yt.thumbnail_url
    filesize = stream.filesize
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
        logger.info('filename = [%s] filesize = [%s] already exists in system' % (filename, fsize))
        if fsize == filesize:
            if skip:
                logger.info('filename = [%s] filesize = [%s] already exists in system and skip download again' % (filename, fsize))
                return filename, thumbnail_url
            elif not replace:
                filename = filename_fix_existing(filename)
        else:
            name, ext = os.path.splitext(filename)
            filename = filename_fix_existing(filename)
            #TODO this workaround, need remove after
            # give second chance
            if skip:
                try:
                    oldfilename = u'{}{}{}'.format(name, '_(1)', ext)
                    fsize = os.path.getsize(oldfilename)
                    logger.debug('Trying to check filename = [%s] and filesize = [%s] if exists and match' % (oldfilename, fsize))
                    if fsize == filesize:
                        logger.info('filename = [%s] filesize = [%s] already exists in system and skip download again' % (oldfilename, fsize))
                        return oldfilename, thumbnail_url
                except:
                    pass

    name, ext = os.path.splitext(filename)
    logger.info('target local filename = [%s]' % filename)
    logger.info('target local filesize = [%s]' % filesize)

    # create tmp file
    (fd, tmpfile) = tempfile.mkstemp(suffix=ext, prefix="", dir=outdir, text=False)
    tmpfile = to_unicode(tmpfile)
    os.close(fd)
    os.unlink(tmpfile)
    logger.info('target local tmpfile  = [%s]' % tmpfile)
    tmppath, tmpbase = ntpath.split(tmpfile)
    tmpname, tmpext = os.path.splitext(tmpbase)

    try:
        stream.download(output_path=tmppath, filename=tmpname, filename_prefix=None, skip_existing=skip)
        sys.stdout.write('\n')
        shutil.move(tmpfile, filename)
        logger.info("File = [{0}] Saved".format(filename))
    except KeyboardInterrupt:
        sys.exit(1)

    sys.stdout.write('\n')
    return (filename, thumbnail_url)


def main():
    """Command line application to download youtube videos."""
    logger = set_logger(logfile=args.logfile, verbosity=args.verbosity, quiet=args.quiet)
    logger.debug('System out encoding = [%s]' % sys.stdout.encoding)

    if not (args.url or os.path.exists(args.file)):
        sys.exit(1)

    if args.proxy:
        logger.info('via proxy = [%s]' % args.proxy)
        proxy_params = {urlparse.urlparse(args.url).scheme: args.proxy}
    else:
        proxy_params = None

    downloads = []
    if args.url:
        if args.list:
            display_streams(args.url)

        elif args.build_playback_report:
            build_playback_report(args.url)

        elif args.caption:
            get_captions(args.url, args.caption)

        elif args.itag:
            downloads.append(args.url)

    elif args.file:
        with open(args.file) as fp:
            for line in fp:
                downloads.append(line)

    if len(downloads) > 0:
        itags = [args.itag]
        for url in downloads:
            logger.info("trying to download url = {0}".format(url))
            if args.quality and args.mode:
                itags = get_target_itags(url=url, quality=args.quality, mode=args.mode)
            for i in range(1, args.retry+1):
                get_captions(url, True)
                replace = args.replace
                if len(itags) > 2:
                    # change replace mode to always False if mutiple target found
                    logger.debug('target number of files = [%s]' % len(itags))
                    replace = False
                for i, itag in enumerate(itags):
                    logger.debug('itag = [%s]' % itag)
                    filename = download(url=url, itag=itag, out=args.out, replace=replace, skip=args.skip, proxies=proxy_params)
                    if filename:
                        logger.info("Youtube Vidoe/Audio from URL = [{0}] downloaded successfully to [{1}]".format(url, filename))
                        if  args.file and (not args.listkeep):
                            with open(args.file, "r") as f:
                                lines = f.readlines()
                            with open(args.file, "w") as f:
                                for line in lines:
                                    if line != url:
                                        f.write(line)
                else:
                    break

    return True


def unitest():
    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)
    #url = 'https://www.youtube.com/watch?v=F1fqet9V494'
    url = 'https://www.youtube.com/watch?v=xwsYvBYZcx4'

    def test1():
        logger.info("Testing with 'display_streams()' for url =  {0}".format(url))
        args.list = True
        main()

    def test2():
        logger.info("Testing with 'build_playback_report()' for url = {0}".format(url))
        args.build_playback_report = True
        main()

    def test3():
        logger.info("Testing with 'get_captions(lang=zh-TW)' for url = {0}".format(url))
        args.caption = 'zh-TW'
        main()
        logger.info("Testing with 'get_captions(lang=True)' for url = {0}".format(url))
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

    args.url = url ; test3(); test2(); test1()
    args.url = None ; args.file ='{name}.{ext}_unittest'.format(name=filename, ext='ini')
    fp = to_unicode(args.file)
    with open(fp, mode='w+') as fh:
        fh.write(url)
    test4();test5()


if __name__ == "__main__":  # Only run if this file is called directly
    args = get_arguments()
    unitest()
    #sys.exit(main())


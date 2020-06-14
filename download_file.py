#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""A simple command line application to download files."""
from __future__ import ( division, absolute_import, print_function, unicode_literals )

import sys, os, tempfile, logging
import socket
import logging
import argparse
import traceback
import tempfile
import posixpath
import shutil
import datetime
import ntpath

PY3K = sys.version_info >= (3, 0)
if PY3K:
    import http.client as httplib
    import urllib.request as urllib2
    import urllib.parse as urlparse
else:
    import httplib
    import urllib2
    import urlparse


logger = logging.getLogger(__name__)


def loglevel_converter(loglevel):
    numeric_level = getattr(logging, loglevel.upper(), logging.info)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % loglevel)
    return numeric_level


def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def get_arguments():
    print(main.__doc__)
    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-u", "--url", action="store", type=str, help=(
            "identify the url to download"
        )
    )
    parser.add_argument(
        "-o", "--out", action="store", type=str, help=(
            "identify the destnation folder/filename to store the file"
        )
    )
    parser.add_argument(
        "-rp", "--replace", type=str2bool, nargs='?', const=True, help=(
            "idenfify if replace the exist file"
        )
    )
    parser.add_argument(
        "-sk", "--skip", type=str2bool, nargs='?', const=True, help=(
            "idenfify if skip the existed file or redownload it again"
        )
    )
    parser.add_argument(
        "-r", "--retry",action="store", type=int, default=2, help=(
            "retry time when get file failed"
        )
    )
    parser.add_argument(
        "-lf", "--logfile", action="store", type=str, default="{name}.{ext}".format(name=filename, ext='log'), help=(
            "identify the log file name"
        )
    )
    parser.add_argument(
        "-ll", "--verbosity", type=str, default="INFO", choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'], help=(
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
            "set proxy"
        )
    )

    parser.set_defaults(replace=True)
    parser.set_defaults(quiet=False)
    args = parser.parse_args(sys.argv[1:])
    print(args)
    if not args.url:
        parser.print_help()
        sys.exit(1)

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


def filename_from_url(url):
    """:return: detected filename as unicode or None"""
    # [ ] test urlparse behavior with unicode url
    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)
    logger.debug('scheme = [%s], netloc = [%s], path = [%s], query = [%s], fragment = [%s]' % (scheme, netloc, path, query, fragment))
    filename = posixpath.basename(path)
    if len(filename.strip(" \n\t.")) == 0:
        return None
    return to_unicode(filename)


def filename_from_headers(headers):
    """Detect filename from Content-Disposition headers if present.
    http://greenbytes.de/tech/tc2231/

    :param: headers as dict, list or string
    :return: filename from content-disposition header or None
    """
    if type(headers) == str:
        headers = headers.splitlines()
    if type(headers) == list:
        headers = dict([x.split(':', 1) for x in headers])
    #logging.debug('headers = [%s]' % headers)
    cdisp = headers.get("Content-Disposition")
    if not cdisp:
        return None
    cdtype = cdisp.split(';')
    if len(cdtype) == 1:
        return None
    if cdtype[0].strip().lower() not in ('inline', 'attachment'):
        return None
    # several filename params is illegal, but just in case
    fnames = [x for x in cdtype[1:] if x.strip().startswith('filename=')]
    if len(fnames) > 1:
        return None
    name = fnames[0].split('=')[1].strip(' \t"')
    name = os.path.basename(name)
    if not name:
        return None
    return name


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


def detect_filename(out=None, headers=None, url=None, default="download.file"):
    """Return filename for saving file. If no filename is detected from output
    argument, url or headers, return default (download.file)
    """
    names = dict(out='', url='', headers='')
    if out:
        names["out"] = out or None
    if headers:
        names["headers"] = filename_from_headers(headers) or None
    if url:
        names["url"] = filename_from_url(url) or None

    return names["out"] or names["headers"] or names["url"]  or default


def exists_at_path(file_path: str, filesize: int) -> bool:
    return os.path.isfile(file_path) and os.path.getsize(file_path) == filesize


def download_file(url, out=None, logfile=None, verbosity='WARNING', quiet=False, proxy=False, skip=True, replace=True, retry=2):
    """
    Download and save a file specified by url to dest directory,
    """

    logger = set_logger(logfile=logfile, verbosity=verbosity, quiet=quiet)

    if not url:
        logger.critical('Target URL = [%s] not identified ! Skip downloading this time', url)
        return False

    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'}

    response = False
    e = False

    # timeout in seconds
    timeout = 10
    socket.setdefaulttimeout(timeout)

    request = urllib2.Request(url, headers=hdr)

    opener = urllib2.build_opener()
    logger.info('trying download file from = [%s] to = [%s]' % (url, out))
    if proxy:
        logger.info('via proxy = [%s]', proxy)
        proxy_params = {urlparse.urlparse(url).scheme: proxy}
        opener.add_handler(urllib2.ProxyHandler(proxy_params))
    urllib2.install_opener(opener)

    for i in range(1, int(retry)+1):
        try:
            # [Seiko] Set Timeout for Http Request by 10 Seconds
            response = urllib2.urlopen(request, timeout = timeout)
            logger.debug('Http Responese Header = [\n{}]'.format(response.info()))
            real_url = response.geturl()
            logger.debug('URL Redirection to = [{}]'.format(real_url))
            code = response.getcode()
            logger.info('Http Return Code = [{}]'.format(code))
            if code != 200:
                logger.error("[{}] IS CURRENTLY NOT AVAILABLE \n {}".format(url, response.read()))
            size = response.length
            logger.info('File Size = [{}]'.format(size))
        except urllib2.HTTPError as e:
            logger.exception('HTTP Error {}: {}'.format(str(e.code), str(e.msg)))
        except urllib2.URLError as e:
            logger.exception('URL Error = ' + str(e.reason))
        except httplib.HTTPException as e:
            logger.exception('HTTP Exception')
        except urllib2.socket.timeout as e:
            logger.exception('Urllib2 Timeout Exception')
        except ValueError:
            logger.exception('Unknown url type: %s' % url)
        except Exception:
            logger.exception('Generic Exception: ' + traceback.format_exc())

        if response:
            break
        else:
            pass
    else:
        logger.critical('Unable to get file from = [%s] retry = [%s]' % (url, retry))
        if e:
            return e
        else:
            return None

    # get filename of url
    remote_filename = detect_filename('', response.info(), real_url)

    # get filesize of url
    filesize = int(size)

    # detect full filename from out parameter
    filename = out if os.path.isfile(out) else os.path.join(out, remote_filename)

    if skip and exists_at_path(filename, filesize):
        logger.info("file %s already exists, skipping", filename)

        return filename

    # add numeric ' (x)' suffix if filename already exists
    if os.path.exists(filename) and not replace:
        filename = filename_fix_existing(filename)
    filename = to_unicode(filename)
    logger.info('target local filename = [%s]' % filename)
    name, ext = os.path.splitext(filename)
    # create tmp file
    (fd, tmpfile) = tempfile.mkstemp(suffix='.tmp', prefix=filename, dir='.')
    tmpfile = to_unicode(tmpfile)
    os.close(fd)
    os.unlink(tmpfile)
    logger.info('target local tmpfile  = [%s]' % tmpfile)
    tmppath, tmpbase = ntpath.split(tmpfile)
    tmpname, tmpext = os.path.splitext(tmpbase)


    with open(tmpfile, 'wb') as f:
        meta = response.info()
        meta_func = meta.getheaders if hasattr(meta, 'getheaders') else meta.get_all
        meta_length = meta_func("Content-Length")
        file_size = None
        if meta_length:
            file_size = int(meta_length[0])
        logger.info("Downloading: [{0}] Bytes: [{1}]".format(url, file_size))
        print("Downloading: [{0}] Bytes: [{1}]".format(url, file_size))

        file_size_dl = 0
        block_sz = 8192
        while True:
            buffer = response.read(block_sz)
            if not buffer:
                break

            file_size_dl += len(buffer)
            f.write(buffer)

            status = "{0:16}".format(file_size_dl)
            if file_size:
                status += "   [{0:6.2f}%]".format(file_size_dl * 100 / file_size)
            status += chr(13)
            print(status, end="")
        print()

    shutil.move(tmpfile, filename)
    logger.info("File = [{0}] Saved".format(filename))

    return filename


def unitest():
    print("Testng wiht No URL")
    filename = download_file(url=None, replace=False, logfile="skr.log", verbosity="debug")
    log_filename = datetime.datetime.now().strftime("download_%Y-%m-%d_%H_%M_%S.log")
    #print("Testing with 10MB file")
    #url = "http://download.thinkbroadband.com/10MB.zip"
    #filename = download_file(url=url, replace=False, logfile="skr.log", verbosity="debug", quiet=True)
    print("Testing with splunk sdk-python")
    url = "http://dev.splunk.com/goto/sdk-python"
    filename = download_file(url=url, replace=False, logfile="skr.log", verbosity="info", quiet=False)
    print("Testing with iAU index")
    url = "http://iau.trendmicro.com/iau_server.dll/c22t2200v9.5.0l1p1r1o1"
    filename = download_file(url=url, replace=True, verbosity="debug", logfile=log_filename, quiet=True)
    print("Testing with iAU index")
    url = "http://iau.trendmicro.com/iau_server.dll/c22t2200v9.5.0l1p1r1o1"
    filename = download_file(url=url, replace=True, verbosity="info", logfile=log_filename, quiet=False)
    print("Testing with iAU index")
    url = "http://iau.trendmicro.com/iau_server.dll/c22t2200v9.5.0l1p1r1o1"
    filename = download_file(url=url, replace=True, verbosity="Debug", logfile=log_filename, quiet=False)


def main():
    """Command line application to download files."""
    filename = download_file(url=args.url, out=args.out, logfile=args.logfile, verbosity=args.verbosity, quiet=args.quiet, proxy=args.proxy, skip=args.skip, replace=args.replace, retry=args.retry)
    return filename


if __name__ == "__main__":  # Only run if this file is called directly
    #unitest()

    args = get_arguments()
    set_logger(logfile=args.logfile, verbosity=args.verbosity, quiet=args.quiet)

    sys.exit(main())


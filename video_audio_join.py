import sys
import os
import shutil
import subprocess
import ntpath
import logging
import argparse
import tempfile
import ffmpeg
import youtube_downloader


def get_best_audio_video_from_youtube(url):
    logger = logging.getLogger()

    youtube_downloader.display_streams(url=url)
    youtube_downloader.get_captions(url=url)

    video = audio = None
    try:
        itags = youtube_downloader.get_target_itags(url=url, quality='HIGH', mode='VIDEO')
        logger.info('Get Best Video itags = [%s]' % itags[0])
        video = youtube_downloader.download(url=url, itag=itags[0], replace=True, skip=True)
        video = youtube_downloader.to_unicode(video)
        #shutil.move(video, u'{}.video'.format(video))
        #video = u'{}.video'.format(video)
        #video = youtube_downloader.to_unicode(video)
        filesize = os.path.getsize(video)
        logger.info('Best Video = [%s] Size = [%s] Downloaded successfully' % (video, filesize))
    except:
        pass

    try:
        itags = youtube_downloader.get_target_itags(url=url, quality='HIGH', mode='AUDIO')
        logger.info('Get Best Audio itags = [%s]' % itags[0])
        audio = youtube_downloader.download(url=url, itag=itags[0], replace=True, skip=True)
        audio = youtube_downloader.to_unicode(audio)
        #shutil.move(audio, u'{}.audio'.format(audio))
        #audio = u'{}.audio'.format(audio)
        #audio = youtube_downloader.to_unicode(audio)
        filesize = os.path.getsize(audio)
        logger.info('Best Audio = [%s] Size = [%s] Downloaded successfully' % (audio, filesize))
    except:
        pass

    return audio, video


def audio_video_join(audio, video, out=None, keep=False, replace=True):
    logger = logging.getLogger()

    base = os.path.basename(video)
    filename, file_extension = os.path.splitext(base)

    if not out:
        out = base.rstrip('.video')
    if os.path.exists(out) and not replace:
        out = youtube_downloader.filename_fix_existing(out)
    out = youtube_downloader.to_unicode(out)
    logger.info('target local out = [%s]' % out)

    # create tmp file for audio
    (fd, tmpfileAudio) = tempfile.mkstemp(suffix='.audio', prefix='', dir='.')
    tmpfileAudio = youtube_downloader.to_unicode(tmpfileAudio)
    os.close(fd)
    os.unlink(tmpfileAudio)
    logger.info('target local audio tmpfile = [%s]' % tmpfileAudio)
    shutil.copyfile(audio, tmpfileAudio)
    in_audio = ffmpeg.input(tmpfileAudio)
    a1 = in_audio['a']

    # create tmp file for video
    (fd, tmpfileVideo) = tempfile.mkstemp(suffix='.video', prefix='', dir='.')
    tmpfileVideo = youtube_downloader.to_unicode(tmpfileVideo)
    os.close(fd)
    os.unlink(tmpfileVideo)
    logger.info('target local video tmpfile = [%s]' % tmpfileVideo)
    shutil.copyfile(video, tmpfileVideo)
    in_video = ffmpeg.input(tmpfileVideo)
    v1 = in_video['v']

    # create tmp file for out
    (fd, tmpfileOut) = tempfile.mkstemp(suffix='', prefix='', dir='.')
    tmpfileOut = youtube_downloader.to_unicode(tmpfileOut)
    os.close(fd)
    os.unlink(tmpfileOut)
    logger.info('target local out tmpfile = [%s]' % tmpfileOut)


    # take example from https://github.com/kkroening/ffmpeg-python/blob/master/examples/README.md
    (
        ffmpeg
        .output(a1, v1, filename=tmpfileOut, format='mp4')
        .overwrite_output()
        .run()
    )

    shutil.move(tmpfileOut, out)
    os.remove(tmpfileAudio)
    os.remove(tmpfileVideo)
    if not keep:
        os.remove(audio)
        if out != base:
            os.remove(base)

    return True


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
            "identify the file which stored The YouTube /watch url(s)"
        )
    )

    parser.add_argument(
        "-o", "--out", action="store", type=str, help=(
            "identify the destnation folder/filename to store the file"
        )
    )
    parser.add_argument(
        "-rp", "--replace", type=youtube_downloader.str2bool, nargs='?', const=True, help=(
            "replace the output file"
        )
    )
    parser.add_argument(
        "-kp", "--keep", type=youtube_downloader.str2bool, nargs='?', const=False, help=(
            "keep origional audio/video files"
        )
    )
    parser.add_argument(
        "-j", "--join", type=youtube_downloader.str2bool, nargs='?', const=True, help=(
            "keep origional audio/video files"
        )
    )
    parser.add_argument(
        "-r", "--retry",action="store", type=int, default=3, help=(
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
        "-q", "--quiet", type=youtube_downloader.str2bool, nargs='?', const=True, help=(
            "idenfify if enable the silent mode"
        )
    )

    parser.set_defaults(replace=True)
    parser.set_defaults(keep=False)
    parser.set_defaults(join=True)
    parser.set_defaults(quiet=False)

    args = parser.parse_args(sys.argv[1:])
    print(args)
    if not (args.url or os.path.exists(args.file)):
        parser.print_help()
        #sys.exit(1)
    return args


def set_logger():
    module = sys.modules['__main__'].__file__
    logger = logging.getLogger(module)

    LogLevel = youtube_downloader.loglevel_converter(args.verbosity)
    formatter = '%(asctime)s:[%(process)d]:[%(levelname)s]: %(message)s'

    logger.handlers = []
    logger.setLevel(LogLevel)

    logging.basicConfig(
                    level=LogLevel,
                    format=formatter,
                    datefmt='%a %b %d %H:%M:%S CST %Y'
                    )

    # new file handler
    if args.logfile:
        handler = logging.FileHandler(filename=args.logfile, mode='a+', encoding='utf-8', delay=True)
        handler.setLevel(LogLevel)
        # set logging format
        formatter = logging.Formatter(formatter)
        handler.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(handler)

    if args.quiet:
        logging.disable(logging.CRITICAL)
    else:
        logging.disable(logging.NOTSET)

    return logger


def unitest():
    url = 'https://www.youtube.com/watch?v=a_xayPjVec0'
    audio, video = get_best_audio_video_from_youtube(url=url)
    audio_video_join(audio=audio, video=video)


def main():
    """Command line application to download and join youtube HQ video and audio."""
    logger.debug('System out encoding = [%s]' % sys.stdout.encoding)

    if not (args.url or os.path.exists(args.file)):
        sys.exit(1)

    downloads = []
    if args.url:
        downloads.append(args.url)
 
    elif args.file:
        with open(args.file) as fp:
            for line in fp:
                downloads.append(line)

    if len(downloads) > 0:
        for url in downloads:
            logger.info("trying to download url = {0}".format(url))
            for i in range(1, args.retry+1):
                try:
                    audio, video = get_best_audio_video_from_youtube(url)
                    if all([audio, video, args.join]):
                        if audio_video_join(audio=audio, video=video, out=args.out, keep=args.keep, replace=args.replace):
                            break
                except:
                    logger.exception('Unable to download Youtube from url = {0}'.format(url))

    return True


if __name__ == "__main__":  # Only run if this file is called directly
    args = get_arguments()
    logger = set_logger()
    
    #unitest()
    main()               

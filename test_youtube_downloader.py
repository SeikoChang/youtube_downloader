# -*- coding: utf-8 -*-
import pytest
import os
import youtube_downloader


class TestGroup:

    def test_h_in_hello(self):
        assert 'h' in 'hello'

    def test_str_has_split_method(self):
        hasattr('str', 'split')

    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)
    args.file = '{name}.{ext}_unittest'.format(name=filename, ext='ini')

    #url = 'https://www.youtube.com/watch?v=F1fqet9V494'
    url = 'https://www.youtube.com/watch?v=xwsYvBYZcx4'
    playlist = 'https://www.youtube.com/playlist?list=PLteWjpkbvj7rUU5SFt2BlNVCQqkjulPZR'

    @pytest.mark.default
    def test_default():
        logger.info("Testing with download file from ini file")
        main()

    @pytest.mark.streams
    def test_streams_list():
        logger.info(
            "Testing with 'display_streams()' for url =  {0}".format(url))
        args.list = True
        main()

    @pytest.mark.report
    def test_report_generate():
        logger.info(
            "Testing with 'build_playback_report()' for url = {0}".format(url))
        args.build_playback_report = True
        main()

    @pytest.mark.captions
    def test_captions_download():
        logger.info(
            "Testing with 'get_captions(lang=zh-TW)' for url = {0}".format(url))
        args.caption = 'zh-TW'
        main()

    @pytest.mark.captions
    def test_captions_download_all():
        logger.info(
            "Testing with 'get_captions(lang=True)' for url = {0}".format(url))
        args.caption = True
        main()

    @pytest.mark.download
    def test_youtube_download_ini_url():
        logger.info("Testing with download all files from ini file")
        args.replace = True
        args.quality = 'All'
        args.mode = 'ALL'
        main()

    @pytest.mark.download
    def test_test_youtube_download_ini_playlist():
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
    fp = to_unicode(args.file)
    with open(fp, mode='w+') as fh:
        fh.write(url)
    test4()
    test5()

    test6()
    with open(fp, mode='w+') as fh:
        fh.write(playlist)
    test4()

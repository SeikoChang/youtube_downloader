import logging
import os

import pytest
from download_file import to_unicode

logger = logging.getLogger()


class TestGroup:

    def __init__(self, url=None):
        self.url = url

    def test_h_in_hello(self):
        assert "h" in "hello"

    def test_str_has_split_method(self):
        hasattr("str", "split")

    @pytest.mark.default
    def test_default(self):
        logger.info("Testing with download file from ini file")

    @pytest.mark.streams
    def test_streams_list(self):
        logger.info("Testing with 'display_streams()' for url =  {0}".format(url))
        args.list = True

    @pytest.mark.report
    def test_report_generate(self):
        logger.info("Testing with 'build_playback_report()' for url = {0}".format(url))
        args.build_playback_report = True

    @pytest.mark.captions
    def test_captions_download(self):
        logger.info("Testing with 'get_captions(lang=zh-TW)' for url = {0}".format(url))
        args.caption = "zh-TW"

    @pytest.mark.captions
    def test_captions_download_all(self):
        logger.info("Testing with 'get_captions(lang=True)' for url = {0}".format(url))
        args.caption = True

    @pytest.mark.download
    def test_youtube_download_ini_url(self):
        logger.info("Testing with download all files from ini file")
        args.replace = True
        args.quality = "All"
        args.mode = "ALL"

    @pytest.mark.download
    def test_test_youtube_download_ini_playlist(self):
        logger.info("Testing with downloading playlist from input")
        args.replace = False
        args.skip = True
        args.playlist = playlist


if __name__ == "__main__":
    base = os.path.basename(__file__)
    filename, file_extension = os.path.splitext(base)
    file = "{name}.{ext}_unittest".format(name=filename, ext="ini")
    # url = 'https://www.youtube.com/watch?v=F1fqet9V494'
    url = "https://www.youtube.com/watch?v=xwsYvBYZcx4"
    playlist = (
        "https://www.youtube.com/playlist?list=PLteWjpkbvj7rUU5SFt2BlNVCQqkjulPZR"
    )

    test = TestGroup()
    test.url = url
    test.test_default()
    test.test_streams_list()
    test.test_report_generate()
    test.url = None
    fp = to_unicode(file)
    with open(fp, mode="w+") as fh:
        fh.write(url)
    test.test_captions_download()
    test.test_captions_download_all()
    test.test_youtube_download_ini_url()
    with open(fp, mode="w+") as fh:
        fh.write(playlist)
    test.test_test_youtube_download_ini_playlist()

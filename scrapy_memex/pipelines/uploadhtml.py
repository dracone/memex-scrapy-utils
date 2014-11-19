from base64 import urlsafe_b64encode

from twisted.internet.defer import inlineCallbacks, returnValue

from scrapy_memex.pipelines.s3base import S3Pipeline


class UploadHtmlPipeline(S3Pipeline):
    def __init__(self, settings):
        self.uri = settings.get('S3_HTML_PATH')
        super(UploadHtmlPipeline, self).__init__(settings)

    @inlineCallbacks
    def process_item(self, item, spider):
        if 'html' not in item:
            returnValue(item)
        html_utf8 = item['html'].encode('utf-8')
        filename = urlsafe_b64encode(item['url']) + '.html'
        keyname = '%s/%s/%s/%s' % (
            self.root, spider.name, self.time_str, filename
        )
        url = yield self.store(keyname, html_utf8)
        del item['html']
        item['html_url'] = url
        returnValue(item)

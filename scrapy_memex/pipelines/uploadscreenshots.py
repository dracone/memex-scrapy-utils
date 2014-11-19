from base64 import urlsafe_b64encode

from twisted.internet.defer import inlineCallbacks, returnValue

from scrapy_memex.pipelines.s3base import S3Pipeline


class UploadScreenshotsPipeline(S3Pipeline):

    def __init__(self, settings):
        self.uri = settings.get('S3_SCREENSHOTS_PATH')
        super(UploadScreenshotsPipeline, self).__init__(settings)

    @inlineCallbacks
    def process_item(self, item, spider):
        png = item.get('png')
        if png is None:
            returnValue(item)

        keyname = '%s/%s/%s/%s' % (
            self.root, spider.name, self.time_str,
            urlsafe_b64encode(item['url']) + '.png'
        )
        url = yield self.store(keyname, png)
        del item['png']
        item['screenshot_url'] = url
        returnValue(item)

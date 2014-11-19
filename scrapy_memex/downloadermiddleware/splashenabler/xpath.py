import scrapy

from . import splash_request, rule_directive


class SplashEnablerXpathMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        cls.SPLASH_ENABLE_XPATHS = crawler.settings.getlist(
            'SPLASH_ENABLE_XPATHS', []
        )
        return cls()

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            return response
        sel = scrapy.Selector(response)
        for xpath, directive in map(rule_directive,
                                    self.SPLASH_ENABLE_XPATHS):
            if sel.xpath(xpath):
                return splash_request(request, directive, True)
        return response

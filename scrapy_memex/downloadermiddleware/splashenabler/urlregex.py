import re

from . import splash_request, rule_directive


class SplashEnablerUrlRegexMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        cls.SPLASH_ENABLE_URL_REGEXES = crawler.settings.getlist(
            'SPLASH_ENABLE_URL_REGEXES', []
        )
        return cls()

    def process_request(self, request, spider):
        for regex, directive in map(rule_directive,
                                    self.SPLASH_ENABLE_URL_REGEXES):
            if re.search(regex, request.url):
                return splash_request(request, directive)

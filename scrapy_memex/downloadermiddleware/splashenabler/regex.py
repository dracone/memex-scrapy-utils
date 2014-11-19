import re

from . import splash_request, rule_directive


class SplashEnablerRegexMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        cls.SPLASH_ENABLE_REGEXES = crawler.settings.getlist(
            'SPLASH_ENABLE_REGEXES', []
        )
        return cls()

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            return response
        for regex, directive in map(rule_directive,
                                    self.SPLASH_ENABLE_REGEXES):
            if re.search(regex, response.body):
                return splash_request(request, directive, True)
        return response

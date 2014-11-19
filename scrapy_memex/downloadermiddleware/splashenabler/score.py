from . import splash_request


class SplashEnablerScoreMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        cls.SPLASH_ENABLE_MIN_SCORE = crawler.settings.getfloat(
            'SPLASH_ENABLE_MIN_SCORE', 1
        )
        return cls()

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            return response
        if request.meta.get('score', 0) >= self.SPLASH_ENABLE_MIN_SCORE:
            return splash_request(request, dont_filter=True)
        return response

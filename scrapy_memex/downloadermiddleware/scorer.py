class ScorerMiddleware(object):
    """This class is meant to provide website scoring feature, but now it's
    only dumb implemetation"""

    def process_response(self, request, response, spider):
        if 'google.' in request.url:
            score = 0.99
        else:
            score = 0.5
        request.meta['score'] = score
        return response

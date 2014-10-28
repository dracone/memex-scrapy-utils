import copy
from scrapy.http import Request
from scrapy.exceptions import NotConfigured


class RefererChainMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('REFERER_CHAIN_ENABLED'):
            raise NotConfigured
        return cls()

    def process_response(self, request, response, spider):
        referers = copy.deepcopy(response.meta.get('referers', []))
        referers.append(response.url)
        response.meta['referers'] = referers
        return response

import copy
from scrapy.http import Request
from scrapy.exceptions import NotConfigured


class RefererChainMiddleware(object):

    @classmethod
    def from_crawler(cls, crawler):
        if not crawler.settings.getbool('REFERER_CHAIN_ENABLED'):
            raise NotConfigured
        return cls()

    def process_spider_output(self, response, result, spider):
        def _append_referer(r):
            #print response
            if isinstance(r, Request):
                # print '    ', r, r.meta
                # return r
                referers = copy.deepcopy(response.meta.get('referers', []))
                referers.append(response.url)
                r.meta['referers'] = referers
            return r
        return (_append_referer(r) for r in result or ())
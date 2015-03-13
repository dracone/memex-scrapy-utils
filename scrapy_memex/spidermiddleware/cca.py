from scrapy_memex_api.convert import response2cca
from scrapy.item import DictItem, Field
from scrapy.exceptions import NotConfigured


class CcaMiddleware(object):

    _item_class = None  # Cached dynamic CcaItem class

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.get('CCA_ENABLED', True)
        if not enabled:
            raise NotConfigured

    def process_spider_output(self, response, result, spider):
        for r in result:
            yield r
        cca = response2cca(response, base64=True)
        item = self.create_item(cca)
        yield item

    @classmethod
    def create_item(cls, values):
        if cls._item_class is None:
            fields = {field_name: Field()
                      for field_name in values.iterkeys()}
            cls._item_class = type('CcaItem', (DictItem,), {'fields': fields})
        item = cls._item_class(**values)
        return item

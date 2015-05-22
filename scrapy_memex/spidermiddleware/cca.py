from scrapy_memex_api.convert import response2cca
from scrapy.item import Item, DictItem, Field
from scrapy.exceptions import NotConfigured
from scrapy.contrib.exporter import JsonLinesItemExporter
from scrapy.utils.project import data_path


class CcaMiddleware(object):

    def __init__(self):
        self.item_class = None  # Cached dynamic CcaItem class
        self.exporters_by_path = {}

    @classmethod
    def from_crawler(cls, crawler):
        enabled = crawler.settings.getbool('CCA_ENABLED', True)
        if not enabled:
            raise NotConfigured
        return cls()

    def process_spider_output(self, response, result, spider):
        items = []
        for r in result:
            if isinstance(r, Item):
                items.append(r)
            yield r
        cca = response2cca(response, base64=True)
        cca['features'] = {'items': items}
        cca_item = self.create_item(cca)
        cca_path = self.get_cca_path(spider)
        if cca_path is None:
            yield cca_item
        else:
            exporter = self.exporters_by_path.get(cca_path)
            if exporter is None:
                exporter = JsonLinesItemExporter(open(cca_path, 'a+'))
                self.exporters_by_path[cca_path] = exporter
            exporter.export_item(cca_item)

    def create_item(self, values):
        if self.item_class is None:
            fields = {field_name: Field()
                      for field_name in values.iterkeys()}
            self.item_class = type('CcaItem', (DictItem,), {'fields': fields})
        item = self.item_class(**values)
        return item

    def get_cca_path(self, spider):
        return getattr(spider, 'cca_path', None)

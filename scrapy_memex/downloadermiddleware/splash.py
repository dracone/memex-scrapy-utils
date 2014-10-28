# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging
import base64
import copy
import json
import os
from hashlib import md5
from urlparse import urljoin
from urllib import urlencode
from scrapy import log
from scrapy.utils.misc import arg_to_iter

from scrapy_memex.utils.project import project_root


class SplashMiddleware(object):
    """
    Scrapy downloader middleware that passes requests through Splash_
    when 'splash' Request.meta key is set.

    To enable the middleware add it to settings::

        DOWNLOADER_MIDDLEWARES = {
            'splash_mw.SplashMiddleware': 950,
        }

    and then use ``splash`` meta key to pass options::

        yield Request(url, self.parse_result, meta={'splash': {
            # use render.json options here
            'html': 1,
            'png': 1,
        }}

    The response

    .. _Splash: https://github.com/scrapinghub/splash

    """
    SPLASH_DEFAULT_URL = 'http://127.0.0.1:8050'
    SPLASH_DEFAULT_PNG_DIR = 'screenshots'  # relative to <project dir>
    SPLASH_EXTRA_TIMEOUT = 30
    SPLASH_DEFAULT_OPTIONS = {
        'wait': '2.0',
        'width': '1024',
        'height': '768',
        'timeout': '60',
    }
    SPLASH_RENDER_HTML_OPTIONS = {
        'html': '1',
    }
    SPLASH_STORE_PNG_OPTIONS = {
        'png': '1'
    }
    RESPECT_SLOTS = True

    def __init__(self, crawler, splash_url, png_dir):
        self.crawler = crawler
        self._splash_url = splash_url
        self._png_dir = self.real_png_dir(png_dir)

    @classmethod
    def from_crawler(cls, crawler):
        url = crawler.settings.get('SPLASH_URL', cls.SPLASH_DEFAULT_URL)
        png_dir = crawler.settings.get('SPLASH_PNG_DIR',
                                       cls.SPLASH_DEFAULT_PNG_DIR)
        return cls(crawler, url, png_dir)

    def splash_url(self, query, url, endpoint='render.json'):
        query = query.copy()
        query['url'] = url
        return urljoin(self._splash_url, endpoint) + '?' + urlencode(query)

    def real_png_dir(self, png_dir):
        root = project_root()
        return os.path.join(root, png_dir)

    def store_png(self, png_base64):
        png = base64.b64decode(png_base64)
        if not os.path.exists(self._png_dir):
            os.makedirs(self._png_dir)

        fn = os.path.join(self._png_dir, md5(png).hexdigest() + '.png')
        with open(fn, 'wb') as fp:
            fp.write(png)
        return fn

    def process_request(self, request, spider):
        if request.meta.get('_splash'):
            return
        # The most common usage is render HTML only, so lets accept this option
        # and set most common options for the user.
        # Callback will be called with rendered HTML, not with Splash JSON data
        render_html = request.meta.get('splash_render_html')
        # Store screenshots automatically in specified directory
        store_png = request.meta.get('splash_store_png')
        custom_splash_options = request.meta.get('splash', {})
        splash_options = copy.deepcopy(self.SPLASH_DEFAULT_OPTIONS)

        if store_png:
            # Can't store png only, because some response must be returned
            render_html = True
            splash_options.update(self.SPLASH_STORE_PNG_OPTIONS)
            splash_options.update(custom_splash_options)

        if render_html:
            splash_options.update(self.SPLASH_RENDER_HTML_OPTIONS)
            splash_options.update(custom_splash_options)

        if not store_png and not render_html:
            if custom_splash_options:
                splash_options = custom_splash_options
            else:
                return

        if request.method != 'GET':
            log.msg("Only GET requests are supported by SplashMiddleware; "
                    "'%s' will be handled without Splash" %
                    request, logging.WARNING)
            return request

        for key, value in splash_options.items():
            if key.lower() == 'timeout':
                request.meta['download_timeout'] = max(
                    request.meta.get('download_timeout', 1e6),
                    float(value) + self.SPLASH_EXTRA_TIMEOUT
                )

        meta = request.meta.copy()
        meta.pop('splash', None)
        meta['_splash'] = True
        meta['splash_target_url'] = request.url

        if self.RESPECT_SLOTS:
            # Use the same download slot to (sort of) respect download
            # delays and concurrency options.
            meta['download_slot'] = self._get_slot_key(request)

        self.crawler.stats.inc_value('splash/request_count')

        req_rep = request.replace(
            url=self.splash_url(splash_options, request.url),
            meta=meta,
            # FIXME: original HTTP headers are not respected.
            # To respect them changes to Splash are needed.
            headers={},
        )
        return req_rep

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            self.crawler.stats.inc_value('splash/response_count/%s' %
                                         response.status)
            if response.status != 200:
                return response
            if request.meta.get('splash_render_html') and request.meta.get('splash_store_png'):
                data = json.loads(response.body)
                png_filename = self.store_png(data['png'])
                response = response.replace(
                    body=data['html'].encode('utf-8'),
                    encoding='utf-8',
                    url=request.meta.pop('splash_target_url'),
                )
                request.meta['png_filename'] = png_filename
            elif request.meta.get('splash_render_html'):
                response = response.replace(url=request.url)
            
        return response

    def _get_slot_key(self, request_or_response):
        return self.crawler.engine.downloader._get_slot_key(
            request_or_response, None
        )

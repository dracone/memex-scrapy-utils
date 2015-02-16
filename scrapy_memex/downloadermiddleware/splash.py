# -*- coding: utf-8 -*-
from __future__ import absolute_import

import base64
import json
import logging
import os

from urlparse import urljoin
from urllib import urlencode

from scrapy import log
from scrapy.http import HtmlResponse
from scrapy.utils.conf import closest_scrapy_cfg


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
    SPLASH_DEFAULT_DIRECTIVES_DIR = 'directives'
    SPLASH_EXTRA_TIMEOUT = 30
    RESPECT_SLOTS = True

    def __init__(self, crawler, splash_url, directives_dir):
        self.crawler = crawler
        self.splash_url = splash_url
        self.directives_dir = directives_dir
        self._lua_cache = {}

    @classmethod
    def from_crawler(cls, crawler):
        url = crawler.settings.get('SPLASH_URL', cls.SPLASH_DEFAULT_URL)
        directives_dir = crawler.settings.get('SPLASH_DIRECTIVES_DIR',
                                              cls.SPLASH_DEFAULT_DIRECTIVES_DIR)
        project_root = os.path.dirname(closest_scrapy_cfg())
        directives_dir = os.path.join(project_root, directives_dir)
        return cls(crawler, url, directives_dir)

    def process_request(self, request, spider):
        # Avoid recursion
        if request.meta.get('_splash'):
            return

        splash_options = request.meta.get('splash')
        directive = request.meta.get('splash_directive', [])

        if directive or splash_options:
            if not self._is_request_type_supported(request):
                return request
            self._increase_stats()
            # Decide which endpoint we'll use
            if directive:
                return self._lua_request(request, splash_options, directive)
            elif splash_options:
                return self._json_request(request, splash_options)

    def _json_request(self, request, splash_options):
        splash_url = urljoin(self.splash_url, 'render.json')
        meta = self._prepare_meta(request, splash_options)
        splash_options = self._prepare_splash_options(request, splash_options)
        new_request = request.replace(
            url=splash_url,
            method='POST',
            body=json.dumps(splash_options),
            meta=meta,
            headers={'Content-Type': 'application/json'},
        )
        return new_request

    def _lua_request(self, request, splash_options, directive):
        splash_url = urljoin(self.splash_url, 'execute')
        lua_source = self._load_lua_source(directive)
        js_source = self._load_js_source(directive)
        meta = self._prepare_meta(request, splash_options)
        splash_options['url'] = request.url
        new_request = request.replace(
            url=splash_url + '?' + urlencode(splash_options),
            method='POST',
            body=json.dumps({'lua_source': lua_source, 'js_source': js_source}),
            meta=meta,
            headers={'Content-Type': 'application/json'},
        )
        return new_request

    def _load_lua_source(self, directive):
        cache_name = 'lua_' + directive
        cached = self._lua_cache.get(cache_name)
        if cached:
            return cached
        path = os.path.join(self.directives_dir, directive + '.lua')
        with open(path) as f:
            source = f.read()
            self._lua_cache[cache_name] = source
            return source

    def _load_js_source(self, directive):
        cache_name = 'js_' + directive
        cached = self._lua_cache.get(cache_name)
        if cached:
            return cached
        path = os.path.join(self.directives_dir, directive + '.js')
        with open(path) as f:
            source = f.read()
            self._lua_cache[cache_name] = source
            return source

    def _is_request_type_supported(self, request):
        if request.method != 'GET':
            log.msg("Only GET requests are supported by SplashMiddleware; "
                    "'%s' will be handled without Splash" %
                    request, logging.WARNING)
            return False
        return True

    def _increase_stats(self):
        self.crawler.stats.inc_value('splash/request_count')

    def _prepare_meta(self, request, splash_options):
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

        return meta

    def _prepare_splash_options(self, request, splash_options):
        splash_options['url'] = request.url
        splash_options['headers'] = request.headers
        return splash_options

    def process_response(self, request, response, spider):
        if '_splash' in request.meta:
            self.crawler.stats.inc_value('splash/response_count/%s' %
                                         response.status)
            if response.status != 200:
                return response
            data = json.loads(response.body)
            response = HtmlResponse(
                url=request.meta.pop('splash_target_url'),
                body=data.get('html', u'').encode('utf-8'),
                encoding='utf-8',
            )
            if 'png' in data:
                request.meta['png'] = base64.b64decode(data['png'])

        return response

    def _get_slot_key(self, request_or_response):
        return self.crawler.engine.downloader._get_slot_key(
            request_or_response, None
        )

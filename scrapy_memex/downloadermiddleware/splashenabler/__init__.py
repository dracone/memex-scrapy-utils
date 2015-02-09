def splash_request(request, directive=None, dont_filter=None):
    """Transform request to run with SplashMiddleware"""
    request.meta.update({
        'splash': {
            'debug': True,
            'return_html': True,
            'return_png': True,
            'timeout': 60,
        },
        'splash_directive': directive
    })
    if dont_filter is not None:
        request.dont_filter = dont_filter
    return request


def rule_directive(value):
    if isinstance(value, (list, tuple)):
        return value[0], value[1]
    return value, None

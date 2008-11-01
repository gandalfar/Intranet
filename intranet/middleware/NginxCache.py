from django.core.cache import cache
import settings
import re

class NginxMemCacheMiddleWare:
    def process_response(self, request, response):
        try:
            cacheIt = False
            theUrl = request.get_full_path()

            for exp in settings.CACHE_INCLUDE_REGEXPS:
                if re.match(exp,theUrl):
                    cacheIt = True

            # if it's a GET then store it in the cache:
            if request.method != 'GET':
                cacheIt = False

            if cacheIt:
                key = '%s-%s' % (settings.CACHE_KEY_PREFIX,theUrl)
                cache.set(key,response.content)     
        except AttributeError:
            return response

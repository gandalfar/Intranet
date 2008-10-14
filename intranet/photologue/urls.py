from django.conf import settings
from django.conf.urls.defaults import *
from models import *

# Number of random images from the gallery to display.
SAMPLE_SIZE = ":%s" % getattr(settings, 'GALLERY_SAMPLE_SIZE', 5)

top = Gallery.objects.filter(parent__isnull=True)

def recurse(gallery):
    result = []
    result += [gallery]
    for i in Gallery.objects.filter(parent=gallery):
        if Gallery.objects.filter(parent=i):
            result += recurse(i)
        else:
            result += [i]
    return result

ordered = []
for g in top:
    ordered += recurse(g)

urlpatterns = patterns('django.views.generic.list_detail',
    url(r'^$', 'object_list', {
        'queryset': Gallery.objects.filter(parent__isnull = True), 
        'allow_empty': True, 
        'extra_context': {'top': top},}, 
        name='pl-gallery-list'),
    url(r'^(?P<slug>[-\w\d]+)/$', 'object_detail', {
        'slug_field': 'title_slug', 
        'queryset': Gallery.objects.all(),
        'extra_context': {'top': top, 'ordered': ordered,},}, 
        name='pl-gallery-detail'),
)


from django.conf.urls.defaults import *

urlpatterns = patterns('pipa.mercenaries.views',
	(r'^(?P<year>\d+)?/?(?P<month>\d+)?/?$', 'index'),
	(r'^(?P<year>\d+)?/?(?P<month>\d+)?/?(?P<id>\d+|napotnice|redni)/$', 'export_xls'),
)

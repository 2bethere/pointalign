from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'tag.views.current_datetime', name='current_datetime'),
    url(r'^match/$', 'tag.views.match', name='match'),
    url(r'^visualmatch/$', 'tag.views.visualmatch', name='visualmatch'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
)

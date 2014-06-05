from django.conf.urls import include, patterns, url
from django.contrib import admin

from odie import views

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^data/lectures$', views.lectures),
    url(r'^data/lectures/(.+)/documents$', views.documents_of_lecture),
    url(r'^data/carts$', views.carts),
    url(r'^data/carts/(.+)$', views.create_cart),
)

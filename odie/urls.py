from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
    url(r'^data/lectures$', views.lectures),
    url(r'^data/lectures/(.+)/documents$', views.documents_of_lecture),
    url(r'^data/carts$', views.carts),
    url(r'^data/carts/(.+)$', views.create_cart),
)

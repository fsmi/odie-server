from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
    url(r'^data/lectures$', views.lectures),
    url(r'^data/lectures/(.+)/documents$', views.documents_of_lecture)
)

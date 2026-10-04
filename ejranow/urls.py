"""
URL configuration for ejranow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from ejranow.document_views import superuser_document, superuser_documents
from ejranow.views import (
    about,
    artist_detail,
    artist_list,
    home,
    me_matches,
    me_profile,
    opportunity_detail,
    opportunity_list,
    project_detail,
    project_list,
    search,
    service_worker,
)

urlpatterns = [
    path("", home, name="home"),
    path("about-us/", about, name="about"),
    path("artists/", artist_list, name="artists"),
    path("artists/<slug:slug>/", artist_detail, name="artist"),
    path("opportunities/", opportunity_list, name="opportunities"),
    path("opportunities/<slug:slug>/", opportunity_detail, name="opportunity"),
    path("projects/", project_list, name="projects"),
    path("projects/<slug:slug>/", project_detail, name="project"),
    path("search/", search, name="search"),
    path("me/profile/", me_profile, name="me-profile"),
    path("me/matches/", me_matches, name="me-matches"),
    path("sw.js", service_worker, name="service-worker"),
    path("admin/documents/", admin.site.admin_view(superuser_documents), name="admin-documents"),
    path(
        "admin/documents/<slug:slug>/",
        admin.site.admin_view(superuser_document),
        name="admin-document",
    ),
    path("admin/", admin.site.urls),
]

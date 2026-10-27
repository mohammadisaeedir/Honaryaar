"""
URL configuration for honaryaar project.

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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from honaryaar.admin_language import switch_admin_language
from honaryaar.data_source import switch_data_source
from honaryaar.document_views import superuser_document, superuser_documents
from honaryaar.media_views import media_upload_complete, media_upload_start
from honaryaar.auth_views import login_code, login_phone, logout_view, me_profile
from honaryaar.studio_views import (
    application_detail,
    application_status,
    apply,
    collaboration_detail,
    invite_detail,
    my_applications,
    my_collaborations,
    my_invites,
    my_matches,
    my_projects,
    project_manage,
    project_new,
)
from honaryaar.notification_views import (
    my_notifications,
    notification_open,
    notifications_read_all,
    push_config,
    push_devices,
)
from honaryaar.support_views import contact, my_ticket, my_tickets, report_artist, report_opportunity, report_project
from honaryaar.views import (
    about,
    artist_detail,
    apply_many,
    artist_invite,
    bookmark_artist,
    bookmark_artists,
    bookmark_opportunities,
    bookmark_opportunity,
    bookmark_project,
    bookmark_remove,
    guide,
    artist_list,
    home,
    landing,
    opportunity_detail,
    opportunity_list,
    project_detail,
    project_list,
    search,
    sitemap_page,
    sitemap_xml,
    robots_txt,
    service_worker,
    web_manifest,
)

urlpatterns = [
    path("", home, name="home"),
    path("landing/", landing, name="landing"),
    path("about-us/", about, name="about"),
    path("magazine/", guide, name="magazine"),
    path("terms/", guide, name="terms"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap_xml, name="sitemap-xml"),
    path("sitemap/", sitemap_page, name="sitemap"),
    path("contact/", contact, name="contact"),
    path("artists/", artist_list, name="artists"),
    path("artists/invite/", artist_invite, name="artist-invite"),
    path("artists/bookmark/", bookmark_artists, name="bookmark-artists"),
    path("artists/<slug:slug>/bookmark/", bookmark_artist, name="bookmark-artist"),
    path("artists/<slug:slug>/report/", report_artist, name="report-artist"),
    path("artists/<slug:slug>/", artist_detail, name="artist"),
    path("opportunities/", opportunity_list, name="opportunities"),
    path("opportunities/bookmark/", bookmark_opportunities, name="bookmark-opportunities"),
    path("opportunities/apply/", apply_many, name="apply-many"),
    path("opportunities/<slug:slug>/bookmark/", bookmark_opportunity, name="bookmark-opportunity"),
    path("opportunities/<slug:slug>/report/", report_opportunity, name="report-opportunity"),
    path("opportunities/<slug:slug>/", opportunity_detail, name="opportunity"),
    path("opportunities/<slug:slug>/apply/", apply, name="apply"),
    path("projects/", project_list, name="projects"),
    path("projects/<slug:slug>/bookmark/", bookmark_project, name="bookmark-project"),
    path("projects/<slug:slug>/report/", report_project, name="report-project"),
    path("projects/<slug:slug>/", project_detail, name="project"),
    path("search/", search, name="search"),
    path("login/", login_phone, name="login"),
    path("login/code/", login_code, name="login-code"),
    path("logout/", logout_view, name="logout"),
    path("me/profile/", me_profile, name="me-profile"),
    path("me/media/uploads/", media_upload_start, name="media-upload-start"),
    path("me/media/uploads/<uuid:upload_id>/complete/", media_upload_complete, name="media-upload-complete"),
    path("me/notifications/", my_notifications, name="me-notifications"),
    path("me/notifications/read-all/", notifications_read_all, name="me-notifications-read-all"),
    path("me/notifications/<int:pk>/open/", notification_open, name="me-notification-open"),
    path("me/push/config/", push_config, name="push-config"),
    path("me/push/devices/", push_devices, name="push-devices"),
    path("me/tickets/", my_tickets, name="me-tickets"),
    path("me/tickets/<int:pk>/", my_ticket, name="me-ticket"),
    path("me/projects/new/", project_new, name="me-project-new"),
    # Lifecycle board (must stay above me/projects/<slug>/ so new-board is not captured)
    path("", include("honaryaar.board_urls")),
    path("me/projects/<slug:slug>/", project_manage, name="me-project"),
    path("me/projects/", my_projects, name="me-projects"),
    path("me/applications/", my_applications, name="me-applications"),
    path("me/applications/<int:pk>/", application_detail, name="me-application"),
    path("me/applications/<int:pk>/status/", application_status, name="application-status"),
    path("me/invites/", my_invites, name="me-invites"),
    path("me/invites/<int:pk>/", invite_detail, name="me-invite"),
    path("me/bookmarks/<int:pk>/", bookmark_remove, name="bookmark-remove"),
    path("me/collaborations/", my_collaborations, name="me-collaborations"),
    path("me/collaborations/<int:pk>/", collaboration_detail, name="me-collaboration"),
    path("me/matches/", my_matches, name="me-matches"),
    path("manifest.webmanifest", web_manifest, name="manifest"),
    path("sw.js", service_worker, name="service-worker"),
    path("admin/data-source/", admin.site.admin_view(switch_data_source), name="admin-data-source"),
    path("admin/language/", admin.site.admin_view(switch_admin_language), name="admin-language"),
    path("admin/documents/", admin.site.admin_view(superuser_documents), name="admin-documents"),
    path(
        "admin/documents/<slug:slug>/",
        admin.site.admin_view(superuser_document),
        name="admin-document",
    ),
    path("admin/", admin.site.urls),
]

from honaryaar.storage import parspack_configured

if settings.DEBUG and not parspack_configured():
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

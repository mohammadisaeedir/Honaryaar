from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.urls import reverse

from honaryaar.documents import DOCUMENTS, document_added, document_path


def superuser_documents(request):
    if not request.user.is_superuser:
        raise PermissionDenied
    documents = [
        {
            "title": item["title"],
            "url": reverse("admin-document", args=[item["slug"]]),
            "added": document_added(item),
        }
        for item in DOCUMENTS
    ]
    return render(
        request,
        "admin/documents.html",
        {
            **admin.site.each_context(request),
            "title": "Documents",
            "documents": documents,
        },
    )


def superuser_document(request, slug):
    if not request.user.is_superuser:
        raise PermissionDenied
    item = next((entry for entry in DOCUMENTS if entry["slug"] == slug), None)
    if item and item.get("live"):
        from honaryaar.erd import render_erd

        return HttpResponse(render_erd(), content_type="text/html; charset=utf-8")
    path = document_path(slug)
    if path is None:
        raise Http404
    return HttpResponse(path.read_text(encoding="utf-8"), content_type="text/html; charset=utf-8")

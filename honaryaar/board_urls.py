from django.urls import path

from honaryaar import board

urlpatterns = [
    path("me/my-tasks/", board.my_tasks_dashboard, name="my_tasks_dashboard"),
    path("me/board/", board.board_overview, name="board_overview"),
    path("me/projects/new-board/", board.board_project_new, name="board_project_new"),
    path("me/projects/<slug:slug>/board/", board.board_view, name="board_view"),
    path(
        "me/projects/<slug:slug>/board/status/",
        board.board_status_update,
        name="board_status_update",
    ),
    path("me/projects/<slug:slug>/board/tasks/reorder/", board.board_tasks_reorder, name="board_tasks_reorder"),
    path("me/projects/<slug:slug>/board/tasks/", board.board_tasks, name="board_tasks"),
    path("me/projects/<slug:slug>/board/tasks/<int:pk>/", board.board_task_detail, name="board_task_detail"),
    path(
        "me/projects/<slug:slug>/board/tasks/<int:pk>/assignees/",
        board.board_task_assignees,
        name="board_task_assignees",
    ),
    path(
        "me/projects/<slug:slug>/board/tasks/<int:pk>/assignees/<int:profile_id>/",
        board.board_task_assignee_remove,
        name="board_task_assignee_remove",
    ),
    path(
        "me/projects/<slug:slug>/board/tasks/<int:pk>/comments/",
        board.board_task_comments,
        name="board_task_comments",
    ),
    path(
        "me/projects/<slug:slug>/board/tasks/<int:pk>/attachments/",
        board.board_task_attachments,
        name="board_task_attachments",
    ),
    path(
        "me/projects/<slug:slug>/board/tasks/<int:pk>/attachments/<int:att_id>/",
        board.board_task_attachment_delete,
        name="board_task_attachment_delete",
    ),
    path("me/projects/<slug:slug>/board/events/", board.board_events, name="board_events"),
    path(
        "me/projects/<slug:slug>/board/events/<int:pk>/",
        board.board_event_detail,
        name="board_event_detail",
    ),
    path(
        "me/projects/<slug:slug>/board/events/<int:pk>/attendance/",
        board.board_event_attendance,
        name="board_event_attendance",
    ),
    path("me/projects/<slug:slug>/board/members/", board.board_members, name="board_members"),
    path(
        "me/projects/<slug:slug>/board/members/invite/",
        board.board_member_invite,
        name="board_member_invite",
    ),
    path(
        "me/projects/<slug:slug>/board/members/<int:pk>/",
        board.board_member_detail,
        name="board_member_detail",
    ),
    path("me/project-invites/", board.project_invites_list, name="project_invites_list"),
    path("me/project-invites/<int:pk>/accept/", board.project_invite_accept, name="project_invite_accept"),
    path("me/project-invites/<int:pk>/reject/", board.project_invite_reject, name="project_invite_reject"),
]

(function () {
    "use strict";

    var WEEKDAYS = ["شنبه", "یکشنبه", "دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه"];
    var MONTHS = [
        "فروردین",
        "اردیبهشت",
        "خرداد",
        "تیر",
        "مرداد",
        "شهریور",
        "مهر",
        "آبان",
        "آذر",
        "دی",
        "بهمن",
        "اسفند",
    ];
    var PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";

    function csrf() {
        var input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input) return input.value;
        var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function boot(id) {
        var node = document.getElementById(id || "board-bootstrap");
        if (!node) return {};
        try {
            return JSON.parse(node.textContent);
        } catch (err) {
            return {};
        }
    }

    function faNum(value) {
        return String(value == null ? "" : value).replace(/\d/g, function (d) {
            return PERSIAN_DIGITS[d];
        });
    }

    function pad2(n) {
        return String(n).padStart(2, "0");
    }

    function hasJalaali() {
        return typeof window.jalaali !== "undefined";
    }

    function gToJ(gy, gm, gd) {
        if (!hasJalaali()) return { jy: gy, jm: gm, jd: gd };
        return window.jalaali.toJalaali(gy, gm, gd);
    }

    function jToG(jy, jm, jd) {
        if (!hasJalaali()) return { gy: jy, gm: jm, gd: jd };
        return window.jalaali.toGregorian(jy, jm, jd);
    }

    function monthLength(jy, jm) {
        if (hasJalaali() && typeof window.jalaali.jalaaliMonthLength === "function") {
            return window.jalaali.jalaaliMonthLength(jy, jm);
        }
        if (jm <= 6) return 31;
        if (jm <= 11) return 30;
        return 29;
    }

    function todayJ() {
        var now = new Date();
        return gToJ(now.getFullYear(), now.getMonth() + 1, now.getDate());
    }

    function isoFromJ(jy, jm, jd) {
        var g = jToG(jy, jm, jd);
        return g.gy + "-" + pad2(g.gm) + "-" + pad2(g.gd);
    }

    function jFromIso(iso) {
        if (!iso) return null;
        var parts = String(iso).slice(0, 10).split("-");
        if (parts.length !== 3) return null;
        return gToJ(Number(parts[0]), Number(parts[1]), Number(parts[2]));
    }

    function formatShamsiDate(iso) {
        var j = jFromIso(iso);
        if (!j) return "";
        return faNum(j.jy) + "/" + faNum(pad2(j.jm)) + "/" + faNum(pad2(j.jd));
    }

    function formatShamsiLong(iso) {
        var j = jFromIso(iso);
        if (!j) return "";
        return faNum(j.jd) + " " + MONTHS[j.jm - 1] + " " + faNum(j.jy);
    }

    function formatShamsiWhen(iso) {
        if (!iso) return "";
        var datePart = formatShamsiLong(iso);
        var time = "";
        try {
            var d = new Date(iso);
            if (!isNaN(d.getTime())) {
                time = faNum(pad2(d.getHours()) + ":" + pad2(d.getMinutes()));
            }
        } catch (err) {}
        return time ? datePart + " · " + time : datePart;
    }

    function weekdayIndexFromGregorian(gy, gm, gd) {
        // Saturday = 0 … Friday = 6
        var d = new Date(gy, gm - 1, gd);
        return (d.getDay() + 1) % 7;
    }

    function addDaysIso(iso, delta) {
        var parts = iso.split("-").map(Number);
        var d = new Date(parts[0], parts[1] - 1, parts[2]);
        d.setDate(d.getDate() + delta);
        return d.getFullYear() + "-" + pad2(d.getMonth() + 1) + "-" + pad2(d.getDate());
    }

    function startOfPersianWeekIso(iso) {
        var parts = iso.split("-").map(Number);
        var idx = weekdayIndexFromGregorian(parts[0], parts[1], parts[2]);
        return addDaysIso(iso, -idx);
    }

    function todayIso() {
        var now = new Date();
        return now.getFullYear() + "-" + pad2(now.getMonth() + 1) + "-" + pad2(now.getDate());
    }

    async function apiCall(url, options, busySetter) {
        options = options || {};
        var headers = Object.assign(
            { "X-CSRFToken": csrf(), "X-Requested-With": "fetch" },
            options.headers || {}
        );
        if (options.json) {
            headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(options.json);
        }
        if (busySetter) busySetter(true);
        try {
            var response = await fetch(url, {
                method: options.method || "GET",
                credentials: "same-origin",
                headers: headers,
                body: options.body,
            });
            var payload = {};
            try {
                payload = await response.json();
            } catch (err) {
                payload = {};
            }
            if (!response.ok) {
                throw new Error(payload.error || "انجام نشد.");
            }
            return payload;
        } finally {
            if (busySetter) busySetter(false);
        }
    }

    function flashItem(item) {
        if (!item) return;
        item.justUpdated = true;
        setTimeout(function () {
            item.justUpdated = false;
        }, 500);
    }

    document.addEventListener("alpine:init", function () {
        Alpine.data("shamsiPicker", function (initial) {
            initial = initial || {};
            var start = jFromIso(initial.value || "") || todayJ();
            return {
                open: false,
                fieldName: initial.name || "",
                gregorianValue: initial.value || "",
                viewJy: start.jy,
                viewJm: start.jm,
                weekdays: WEEKDAYS,
                months: MONTHS,

                get displayValue() {
                    return this.gregorianValue ? formatShamsiDate(this.gregorianValue) : "";
                },

                init() {
                    var self = this;
                    this.$watch("gregorianValue", function (val) {
                        if (typeof initial.onChange === "function") initial.onChange(val);
                        self.$dispatch("shamsi-change", { value: val, name: self.fieldName });
                    });
                },

                faNum: faNum,

                monthTitle() {
                    return this.months[this.viewJm - 1] + " " + faNum(this.viewJy);
                },

                prevMonth() {
                    if (this.viewJm === 1) {
                        this.viewJm = 12;
                        this.viewJy -= 1;
                    } else {
                        this.viewJm -= 1;
                    }
                },

                nextMonth() {
                    if (this.viewJm === 12) {
                        this.viewJm = 1;
                        this.viewJy += 1;
                    } else {
                        this.viewJm += 1;
                    }
                },

                cells() {
                    var len = monthLength(this.viewJy, this.viewJm);
                    var gFirst = jToG(this.viewJy, this.viewJm, 1);
                    var start = weekdayIndexFromGregorian(gFirst.gy, gFirst.gm, gFirst.gd);
                    var rows = [];
                    var day = 1 - start;
                    for (var r = 0; r < 6; r++) {
                        var week = [];
                        for (var c = 0; c < 7; c++) {
                            if (day < 1 || day > len) {
                                week.push(null);
                            } else {
                                var iso = isoFromJ(this.viewJy, this.viewJm, day);
                                week.push({ day: day, iso: iso });
                            }
                            day += 1;
                        }
                        rows.push(week);
                        if (day > len) break;
                    }
                    return rows;
                },

                pick(iso) {
                    this.gregorianValue = iso;
                    this.open = false;
                },

                clear() {
                    this.gregorianValue = "";
                    this.open = false;
                },

                goToday() {
                    var t = todayJ();
                    this.viewJy = t.jy;
                    this.viewJm = t.jm;
                    this.pick(todayIso());
                },

                isSelected(iso) {
                    return iso && iso === this.gregorianValue;
                },

                isToday(iso) {
                    return iso && iso === todayIso();
                },
            };
        });

        Alpine.directive("sortable-projects", function (el, { expression }, { cleanup }) {
            if (typeof Sortable === "undefined") return;
            var sortable = Sortable.create(el, {
                group: "project-board",
                animation: 150,
                draggable: ".lb-pcard",
                ghostClass: "lb-pcard--ghost",
                chosenClass: "lb-pcard--chosen",
                dragClass: "lb-pcard--dragging",
                filter: ".lb-pcard--locked",
                preventOnFilter: true,
                onMove: function (evt) {
                    return evt.dragged.getAttribute("data-can-drag") === "1";
                },
                onEnd: function (evt) {
                    var root = el.closest("[x-data]");
                    var board = root && Alpine.$data(root);
                    if (!board) return;
                    var name = expression || "onProjectDrop";
                    if (typeof board[name] === "function") board[name](evt);
                },
            });
            cleanup(function () {
                sortable.destroy();
            });
        });

        Alpine.data("boardOverview", function () {
            var data = boot("board-overview-bootstrap");
            return {
                busy: false,
                actionError: "",
                columns: (data.columns || []).map(function (col) {
                    return {
                        value: col.value,
                        label: col.label,
                        projects: (col.projects || []).slice(),
                    };
                }),
                newUrl: data.new_url || "",
                faNum: faNum,

                findProject(slug) {
                    for (var i = 0; i < this.columns.length; i++) {
                        var hit = this.columns[i].projects.find(function (row) {
                            return row.slug === slug;
                        });
                        if (hit) return { project: hit, column: this.columns[i] };
                    }
                    return null;
                },

                async onProjectDrop(evt) {
                    this.actionError = "";
                    if (evt.from === evt.to && evt.oldIndex === evt.newIndex) return;
                    var item = evt.item;
                    var slug = item.getAttribute("data-slug");
                    var newStatus = evt.to.getAttribute("data-status");
                    var oldStatus = evt.from.getAttribute("data-status");
                    var found = this.findProject(slug);
                    if (!found || !found.project.can_drag) {
                        if (evt.from !== evt.to) {
                            var ref = evt.from.children[evt.oldIndex] || null;
                            evt.from.insertBefore(item, ref);
                        }
                        this.actionError = "فقط مالک یا مدیر می‌تواند جابه‌جا کند.";
                        return;
                    }
                    if (newStatus === oldStatus) return;

                    var project = found.project;
                    var fromCol = this.columns.find(function (col) {
                        return col.value === oldStatus;
                    });
                    var toCol = this.columns.find(function (col) {
                        return col.value === newStatus;
                    });
                    if (fromCol && toCol) {
                        fromCol.projects = fromCol.projects.filter(function (row) {
                            return row.slug !== slug;
                        });
                        project.status = newStatus;
                        toCol.projects.splice(evt.newIndex, 0, project);
                        flashItem(project);
                    }

                    try {
                        await apiCall(
                            "/me/projects/" + slug + "/board/status/",
                            { method: "PATCH", json: { status: newStatus } },
                            function (v) {
                                this.busy = v;
                            }.bind(this)
                        );
                    } catch (err) {
                        this.actionError = err.message || "جابه‌جایی ذخیره نشد.";
                        window.location.reload();
                    }
                },
            };
        });

        Alpine.data("projectBoard", function () {
            var data = boot("board-bootstrap");
            var statusOrder = ["todo", "in_progress", "blocked", "done"];
            var today = todayJ();
            return {
                tab: "tasks",
                busy: false,
                actionError: "",
                permission: data.permission || "member",
                viewerId: data.viewer_profile_id || null,
                isLifecycle: !!data.is_lifecycle,
                lifecycleStatuses: data.lifecycle_statuses || [],
                project: data.project || {},
                taskStatuses: data.task_statuses || [],
                tasks: (data.tasks || []).map(function (t) {
                    t.justUpdated = false;
                    t.removing = false;
                    return t;
                }),
                events: (data.events || []).map(function (e) {
                    e.justUpdated = false;
                    e.removing = false;
                    e.changeAttendance = false;
                    return e;
                }),
                members: data.members || [],
                roles: data.roles || [],
                urls: data.urls || {},
                slug: data.slug || "",

                filterStatus: "",
                filterAssignee: "",
                filterQuery: "",

                calendarView: "month",
                calJy: today.jy,
                calJm: today.jm,
                weekStartIso: startOfPersianWeekIso(todayIso()),
                selectedDayIso: todayIso(),
                dayPanelOpen: false,

                taskOpen: false,
                activeTaskId: null,
                taskDraft: {},
                comments: [],
                attachments: [],
                commentBody: "",
                assigneePick: "",
                showCreateTask: false,
                datePickerNonce: 0,
                newTask: { title: "", description: "", assignee_ids: [], due_date: "", status: "todo" },
                createTaskError: "",

                inviteOpen: false,
                invitePhone: "",
                inviteRoleId: "",
                inviteError: "",
                inviteOk: "",

                eventOpen: false,
                eventDraft: {
                    title: "",
                    date: "",
                    time: "10:00",
                    end_date: "",
                    end_time: "",
                    location: "",
                    audience_type: "all_team",
                    invitee_ids: [],
                },
                eventError: "",
                eventDetailId: null,

                confirmModal: {
                    show: false,
                    title: "",
                    message: "",
                    confirmText: "حذف",
                    onConfirm: function () {},
                },

                weekdays: WEEKDAYS,
                months: MONTHS,
                faNum: faNum,
                formatShamsiDate: formatShamsiDate,
                formatShamsiLong: formatShamsiLong,
                formatShamsiWhen: formatShamsiWhen,

                isManager() {
                    return this.permission === "owner" || this.permission === "admin";
                },

                canEditStatus(task) {
                    if (this.isManager()) return true;
                    return (task.assignees || []).some(
                        function (row) {
                            return row.profile_id === this.viewerId;
                        }.bind(this)
                    );
                },

                showConfirm(title, message, onConfirm, confirmText) {
                    this.confirmModal = {
                        show: true,
                        title: title,
                        message: message,
                        confirmText: confirmText || "حذف",
                        onConfirm: onConfirm || function () {},
                    };
                },

                closeConfirm() {
                    this.confirmModal.show = false;
                },

                runConfirm() {
                    var fn = this.confirmModal.onConfirm;
                    this.confirmModal.show = false;
                    if (typeof fn === "function") fn();
                },

                async adoptLifecycle(status) {
                    if (!this.isManager()) return;
                    this.actionError = "";
                    try {
                        var result = await this.api(this.urls.status, {
                            method: "PATCH",
                            json: { status: status },
                        });
                        this.project.status = result.status;
                        var row = this.lifecycleStatuses.find(function (item) {
                            return item.value === result.status;
                        });
                        this.project.status_label = row ? row.label : result.status;
                        this.isLifecycle = true;
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                statusLabel(value) {
                    var row = this.taskStatuses.find(function (item) {
                        return item.value === value;
                    });
                    return row ? row.label : value;
                },

                assigneeLabel(task) {
                    var names = (task.assignees || []).map(function (row) {
                        return row.name;
                    });
                    return names.length ? names.join("، ") : "بدون مسئول";
                },

                permissionLabel(value) {
                    return { owner: "مالک", admin: "مدیر", member: "عضو" }[value] || value;
                },

                inviteLabel(value) {
                    return { invited: "دعوت‌شده", accepted: "پذیرفته‌شده", removed: "حذف‌شده" }[value] || value;
                },

                attendanceLabel(value) {
                    return { pending: "در انتظار", confirmed: "تأیید", rejected: "رد" }[value] || value;
                },

                formatWhen(iso) {
                    return formatShamsiWhen(iso);
                },

                attendanceSummary(event) {
                    var counts = { confirmed: 0, rejected: 0, pending: 0 };
                    (event.invitees || []).forEach(function (row) {
                        counts[row.attendance] = (counts[row.attendance] || 0) + 1;
                    });
                    return (
                        faNum(counts.confirmed) +
                        " تأیید / " +
                        faNum(counts.rejected) +
                        " رد / " +
                        faNum(counts.pending) +
                        " در انتظار"
                    );
                },

                myInvite(event) {
                    return (event.invitees || []).find(
                        function (row) {
                            return row.profile_id === this.viewerId;
                        }.bind(this)
                    );
                },

                activeTask() {
                    var id = this.activeTaskId;
                    return (
                        this.tasks.find(function (task) {
                            return task.id === id;
                        }) || null
                    );
                },

                activeEvent() {
                    var id = this.eventDetailId;
                    return (
                        this.events.find(function (event) {
                            return event.id === id;
                        }) || null
                    );
                },

                taskUrl(id, suffix) {
                    return "/me/projects/" + this.slug + "/board/tasks/" + id + "/" + (suffix || "");
                },

                eventUrl(id, suffix) {
                    return "/me/projects/" + this.slug + "/board/events/" + id + "/" + (suffix || "");
                },

                memberUrl(id) {
                    return "/me/projects/" + this.slug + "/board/members/" + id + "/";
                },

                async api(url, options) {
                    return apiCall(
                        url,
                        options,
                        function (v) {
                            this.busy = v;
                        }.bind(this)
                    );
                },

                filteredTasks() {
                    var status = this.filterStatus;
                    var assignee = this.filterAssignee;
                    var query = (this.filterQuery || "").trim().toLowerCase();
                    return this.tasks
                        .filter(function (task) {
                            if (task.removing) return false;
                            if (status && task.status !== status) return false;
                            if (assignee === "none") {
                                if ((task.assignees || []).length) return false;
                            } else if (assignee) {
                                var aid = Number(assignee);
                                if (
                                    !(task.assignees || []).some(function (row) {
                                        return row.profile_id === aid;
                                    })
                                ) {
                                    return false;
                                }
                            }
                            if (query && !(task.title || "").toLowerCase().includes(query)) return false;
                            return true;
                        })
                        .slice()
                        .sort(function (a, b) {
                            return a.sort_order - b.sort_order;
                        });
                },

                itemsForDay(iso) {
                    var items = [];
                    this.tasks.forEach(function (task) {
                        if (task.due_date === iso && !task.removing) {
                            items.push({
                                key: "t-" + task.id,
                                kind: "task",
                                id: task.id,
                                title: task.title,
                                status: task.status,
                                time: "",
                                justUpdated: !!task.justUpdated,
                            });
                        }
                    });
                    this.events.forEach(function (event) {
                        if (!event.starts_at || event.removing) return;
                        if (event.starts_at.slice(0, 10) !== iso) return;
                        var time = "";
                        try {
                            var d = new Date(event.starts_at);
                            time = faNum(pad2(d.getHours()) + ":" + pad2(d.getMinutes()));
                        } catch (err) {}
                        items.push({
                            key: "e-" + event.id,
                            kind: "event",
                            id: event.id,
                            title: event.title,
                            status: "",
                            time: time,
                            justUpdated: !!event.justUpdated,
                        });
                    });
                    return items;
                },

                monthTitle() {
                    return this.months[this.calJm - 1] + " " + faNum(this.calJy);
                },

                weekTitle() {
                    var start = this.weekStartIso;
                    var end = addDaysIso(start, 6);
                    return formatShamsiLong(start) + " — " + formatShamsiLong(end);
                },

                prevPeriod() {
                    if (this.calendarView === "month") {
                        if (this.calJm === 1) {
                            this.calJm = 12;
                            this.calJy -= 1;
                        } else {
                            this.calJm -= 1;
                        }
                    } else {
                        this.weekStartIso = addDaysIso(this.weekStartIso, -7);
                    }
                },

                nextPeriod() {
                    if (this.calendarView === "month") {
                        if (this.calJm === 12) {
                            this.calJm = 1;
                            this.calJy += 1;
                        } else {
                            this.calJm += 1;
                        }
                    } else {
                        this.weekStartIso = addDaysIso(this.weekStartIso, 7);
                    }
                },

                goToday() {
                    var t = todayJ();
                    this.calJy = t.jy;
                    this.calJm = t.jm;
                    this.weekStartIso = startOfPersianWeekIso(todayIso());
                    this.selectedDayIso = todayIso();
                },

                monthCells() {
                    var len = monthLength(this.calJy, this.calJm);
                    var gFirst = jToG(this.calJy, this.calJm, 1);
                    var start = weekdayIndexFromGregorian(gFirst.gy, gFirst.gm, gFirst.gd);
                    var cells = [];
                    var day = 1 - start;
                    for (var i = 0; i < 42; i++) {
                        if (day < 1 || day > len) {
                            cells.push({ empty: true });
                        } else {
                            var iso = isoFromJ(this.calJy, this.calJm, day);
                            cells.push({
                                empty: false,
                                day: day,
                                iso: iso,
                                isToday: iso === todayIso(),
                                isSelected: iso === this.selectedDayIso,
                                items: this.itemsForDay(iso),
                            });
                        }
                        day += 1;
                    }
                    return cells;
                },

                weekDays() {
                    var days = [];
                    for (var i = 0; i < 7; i++) {
                        var iso = addDaysIso(this.weekStartIso, i);
                        var j = jFromIso(iso);
                        days.push({
                            iso: iso,
                            weekday: WEEKDAYS[i],
                            day: j ? j.jd : "",
                            monthLabel: j ? MONTHS[j.jm - 1] : "",
                            isToday: iso === todayIso(),
                            items: this.itemsForDay(iso),
                        });
                    }
                    return days;
                },

                selectDay(iso) {
                    this.selectedDayIso = iso;
                    this.dayPanelOpen = true;
                },

                openAgendaItem(item) {
                    if (item.kind === "task") {
                        var task = this.tasks.find(function (row) {
                            return row.id === item.id;
                        });
                        if (task) this.openTask(task);
                    } else {
                        this.tab = "events";
                        this.eventDetailId = item.id;
                    }
                },

                openCreateTask(prefillDue) {
                    if (!this.isManager()) return;
                    this.newTask = {
                        title: "",
                        description: "",
                        assignee_ids: [],
                        due_date: prefillDue || "",
                        status: "todo",
                    };
                    this.createTaskError = "";
                    this.datePickerNonce += 1;
                    this.showCreateTask = true;
                },

                closeCreateTask() {
                    this.showCreateTask = false;
                    this.createTaskError = "";
                },

                setNewTaskDue(iso) {
                    this.newTask.due_date = iso || "";
                },

                setTaskDraftDue(iso) {
                    this.taskDraft.due_date = iso || "";
                },

                setEventDraftDate(iso) {
                    this.eventDraft.date = iso || "";
                },

                toggleNewAssignee(profileId) {
                    var id = Number(profileId);
                    var list = this.newTask.assignee_ids || [];
                    if (list.indexOf(id) >= 0) {
                        this.newTask.assignee_ids = list.filter(function (row) {
                            return row !== id;
                        });
                    } else {
                        this.newTask.assignee_ids = list.concat([id]);
                    }
                },

                async submitCreateTask() {
                    if (!this.isManager()) return;
                    var title = (this.newTask.title || "").trim();
                    if (!title) {
                        this.createTaskError = "عنوان تسک لازم است.";
                        return;
                    }
                    this.createTaskError = "";
                    try {
                        var created = await this.api(this.urls.tasks, {
                            method: "POST",
                            json: {
                                title: title,
                                description: (this.newTask.description || "").trim(),
                                status: this.newTask.status || "todo",
                                assignee_ids: this.newTask.assignee_ids || [],
                                due_date: this.newTask.due_date || null,
                            },
                        });
                        created.justUpdated = false;
                        created.removing = false;
                        this.tasks.push(created);
                        flashItem(created);
                        this.closeCreateTask();
                    } catch (err) {
                        this.createTaskError = err.message;
                    }
                },

                openTask(task) {
                    this.activeTaskId = task.id;
                    this.taskDraft = {
                        title: task.title,
                        description: task.description || "",
                        status: task.status,
                        due_date: task.due_date || "",
                    };
                    this.datePickerNonce += 1;
                    this.taskOpen = true;
                    this.commentBody = "";
                    this.loadComments();
                    this.attachments = [];
                },

                closeTask() {
                    this.taskOpen = false;
                    this.activeTaskId = null;
                },

                async saveTask() {
                    var task = this.activeTask();
                    if (!task) return;
                    this.actionError = "";
                    var payload = {};
                    if (this.isManager()) {
                        payload = {
                            title: this.taskDraft.title,
                            description: this.taskDraft.description,
                            status: this.taskDraft.status,
                            due_date: this.taskDraft.due_date || null,
                        };
                    } else {
                        payload = { status: this.taskDraft.status };
                    }
                    try {
                        var updated = await this.api(this.taskUrl(task.id), {
                            method: "PATCH",
                            json: payload,
                        });
                        this.replaceTask(updated);
                        flashItem(this.tasks.find(function (row) {
                            return row.id === updated.id;
                        }));
                        this.taskDraft.status = updated.status;
                        this.taskDraft.due_date = updated.due_date || "";
                        this.closeTask();
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                replaceTask(updated) {
                    var index = this.tasks.findIndex(function (row) {
                        return row.id === updated.id;
                    });
                    if (index >= 0) {
                        updated.justUpdated = this.tasks[index].justUpdated;
                        updated.removing = false;
                        this.tasks.splice(index, 1, updated);
                    }
                },

                async cycleStatus(task) {
                    if (!this.canEditStatus(task)) return;
                    this.actionError = "";
                    var idx = statusOrder.indexOf(task.status);
                    var next = statusOrder[(idx + 1) % statusOrder.length];
                    try {
                        var updated = await this.api(this.taskUrl(task.id), {
                            method: "PATCH",
                            json: { status: next },
                        });
                        this.replaceTask(updated);
                        var current = this.tasks.find(function (row) {
                            return row.id === updated.id;
                        });
                        flashItem(current);
                        if (this.activeTaskId === task.id) this.taskDraft.status = updated.status;
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                deleteTask() {
                    var task = this.activeTask();
                    if (!task || !this.isManager()) return;
                    var self = this;
                    this.showConfirm("حذف تسک", "آیا مطمئنید این تسک حذف شود؟", function () {
                        self.doDeleteTask(task.id);
                    });
                },

                async doDeleteTask(taskId) {
                    this.actionError = "";
                    try {
                        await this.api(this.taskUrl(taskId), { method: "DELETE" });
                        var task = this.tasks.find(function (row) {
                            return row.id === taskId;
                        });
                        if (task) {
                            task.removing = true;
                            var self = this;
                            setTimeout(function () {
                                self.tasks = self.tasks.filter(function (row) {
                                    return row.id !== taskId;
                                });
                            }, 280);
                        }
                        this.closeTask();
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                dueClass(due) {
                    if (!due) return "";
                    var todayStr = todayIso();
                    if (due < todayStr) return "is-overdue";
                    if (due === todayStr) return "is-today";
                    return "";
                },

                async loadComments() {
                    var task = this.activeTask();
                    if (!task) return;
                    try {
                        this.comments = await this.api(this.taskUrl(task.id, "comments/"));
                    } catch (err) {
                        this.comments = [];
                    }
                },

                async addComment() {
                    var task = this.activeTask();
                    var body = (this.commentBody || "").trim();
                    if (!task || !body) return;
                    this.actionError = "";
                    try {
                        var comment = await this.api(this.taskUrl(task.id, "comments/"), {
                            method: "POST",
                            json: { body: body },
                        });
                        this.comments.push(comment);
                        this.commentBody = "";
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async addAssignee() {
                    var task = this.activeTask();
                    if (!task || !this.isManager() || !this.assigneePick) return;
                    this.actionError = "";
                    try {
                        await this.api(this.taskUrl(task.id, "assignees/"), {
                            method: "POST",
                            json: { profile_id: Number(this.assigneePick) },
                        });
                        var member = this.members.find(
                            function (row) {
                                return row.profile_id === Number(this.assigneePick);
                            }.bind(this)
                        );
                        if (
                            member &&
                            !(task.assignees || []).some(function (row) {
                                return row.profile_id === member.profile_id;
                            })
                        ) {
                            task.assignees = (task.assignees || []).concat([
                                { profile_id: member.profile_id, name: member.name },
                            ]);
                        }
                        this.assigneePick = "";
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async removeAssignee(profileId) {
                    var task = this.activeTask();
                    if (!task || !this.isManager()) return;
                    this.actionError = "";
                    try {
                        await this.api(this.taskUrl(task.id, "assignees/" + profileId + "/"), {
                            method: "DELETE",
                        });
                        task.assignees = (task.assignees || []).filter(function (row) {
                            return row.profile_id !== profileId;
                        });
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async uploadAttachment(event) {
                    var task = this.activeTask();
                    var file = event.target.files && event.target.files[0];
                    if (!task || !file || !this.isManager()) return;
                    var body = new FormData();
                    body.append("file", file);
                    body.append("label", file.name);
                    this.actionError = "";
                    try {
                        var row = await this.api(this.taskUrl(task.id, "attachments/"), {
                            method: "POST",
                            body: body,
                        });
                        this.attachments.push(row);
                        event.target.value = "";
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async deleteAttachment(attId) {
                    var task = this.activeTask();
                    if (!task || !this.isManager()) return;
                    this.actionError = "";
                    try {
                        await this.api(this.taskUrl(task.id, "attachments/" + attId + "/"), {
                            method: "DELETE",
                        });
                        this.attachments = this.attachments.filter(function (row) {
                            return row.id !== attId;
                        });
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async inviteMember() {
                    if (!this.isManager()) return;
                    this.inviteError = "";
                    this.inviteOk = "";
                    try {
                        var payload = { phone: this.invitePhone };
                        if (this.inviteRoleId) payload.role_id = Number(this.inviteRoleId);
                        var row = await this.api(this.urls.members_invite, {
                            method: "POST",
                            json: payload,
                        });
                        var existing = this.members.findIndex(function (member) {
                            return member.id === row.id;
                        });
                        if (existing >= 0) this.members.splice(existing, 1, row);
                        else this.members.push(row);
                        this.invitePhone = "";
                        this.inviteRoleId = "";
                        this.inviteOk = "دعوت فرستاده شد.";
                    } catch (err) {
                        this.inviteError = err.message;
                    }
                },

                async setPermission(member, permission) {
                    if (!this.isManager()) return;
                    this.actionError = "";
                    try {
                        var updated = await this.api(this.memberUrl(member.id), {
                            method: "PATCH",
                            json: { permission: permission },
                        });
                        var index = this.members.findIndex(function (row) {
                            return row.id === updated.id;
                        });
                        if (index >= 0) this.members.splice(index, 1, updated);
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                removeMember(member) {
                    if (!this.isManager()) return;
                    var self = this;
                    this.showConfirm("حذف عضو", "آیا مطمئنید این عضو از پروژه حذف شود؟", function () {
                        self.doRemoveMember(member.id);
                    });
                },

                async doRemoveMember(memberId) {
                    this.actionError = "";
                    try {
                        await this.api(this.memberUrl(memberId), { method: "DELETE" });
                        this.members = this.members.filter(function (row) {
                            return row.id !== memberId;
                        });
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                openEventForm() {
                    this.eventError = "";
                    this.eventDraft = {
                        title: "",
                        date: todayIso(),
                        time: "10:00",
                        end_date: "",
                        end_time: "",
                        location: "",
                        audience_type: "all_team",
                        invitee_ids: [],
                    };
                    this.datePickerNonce += 1;
                    this.eventOpen = true;
                },

                closeEventForm() {
                    this.eventOpen = false;
                    this.eventError = "";
                },

                async createEvent() {
                    if (!this.isManager()) return;
                    var draft = this.eventDraft;
                    if (!draft.title || !draft.date || !draft.time) {
                        this.eventError = "عنوان، تاریخ و ساعت شروع لازم است.";
                        return;
                    }
                    var starts = draft.date + "T" + draft.time + ":00";
                    var ends = null;
                    if (draft.end_date && draft.end_time) {
                        ends = draft.end_date + "T" + draft.end_time + ":00";
                    }
                    this.eventError = "";
                    try {
                        var created = await this.api(this.urls.events, {
                            method: "POST",
                            json: {
                                title: draft.title,
                                starts_at: starts,
                                ends_at: ends,
                                location: draft.location,
                                audience_type: draft.audience_type,
                                invitee_ids: draft.invitee_ids,
                            },
                        });
                        created.justUpdated = false;
                        created.removing = false;
                        created.changeAttendance = false;
                        this.events.push(created);
                        flashItem(created);
                        this.closeEventForm();
                    } catch (err) {
                        this.eventError = err.message;
                    }
                },

                deleteEvent(event) {
                    if (!this.isManager()) return;
                    var self = this;
                    this.showConfirm("حذف رویداد", "آیا مطمئنید این رویداد حذف شود؟", function () {
                        self.doDeleteEvent(event.id);
                    });
                },

                async doDeleteEvent(eventId) {
                    this.actionError = "";
                    try {
                        await this.api(this.eventUrl(eventId), { method: "DELETE" });
                        var event = this.events.find(function (row) {
                            return row.id === eventId;
                        });
                        if (event) {
                            event.removing = true;
                            var self = this;
                            setTimeout(function () {
                                self.events = self.events.filter(function (row) {
                                    return row.id !== eventId;
                                });
                            }, 280);
                        }
                        if (this.eventDetailId === eventId) this.eventDetailId = null;
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                async setAttendance(event, status) {
                    this.actionError = "";
                    try {
                        await this.api(this.eventUrl(event.id, "attendance/"), {
                            method: "POST",
                            json: { status: status },
                        });
                        var index = this.events.findIndex(function (row) {
                            return row.id === event.id;
                        });
                        if (index < 0) return;
                        var copy = Object.assign({}, this.events[index]);
                        copy.invitees = (copy.invitees || []).map(
                            function (row) {
                                if (row.profile_id === this.viewerId) {
                                    return Object.assign({}, row, { attendance: status });
                                }
                                return row;
                            }.bind(this)
                        );
                        copy.changeAttendance = false;
                        this.events.splice(index, 1, copy);
                        flashItem(this.events[index]);
                    } catch (err) {
                        this.actionError = err.message;
                    }
                },

                acceptedMembers() {
                    return this.members.filter(function (row) {
                        return row.invite_status === "accepted";
                    });
                },
            };
        });
    });
})();

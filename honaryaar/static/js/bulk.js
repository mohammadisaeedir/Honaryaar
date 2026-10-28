(function () {
    var bar = document.querySelector("[data-bulk-bar]");
    var toggle = document.querySelector("[data-bulk-toggle]");
    var layout = bar && bar.closest(".catalog-layout");
    if (!bar || !toggle || !layout || layout.dataset.bulkReady) return;
    layout.dataset.bulkReady = "1";
    var all = bar.querySelector("[data-pick-all]");
    var count = bar.querySelector("[data-pick-count]");

    function fa(value) {
        return String(value).replace(/\d/g, function (digit) { return "۰۱۲۳۴۵۶۷۸۹"[digit]; });
    }

    function boxes() {
        return layout.querySelectorAll("[data-pick]");
    }

    function chosen() {
        return Array.prototype.filter.call(boxes(), function (box) { return box.checked; });
    }

    var ignore = 0;

    function paint() {
        ignore += 1;
        var picked = chosen();
        var total = boxes().length;
        var label = picked.length && picked.length === total
            ? "همه " + fa(picked.length) + " انتخاب"
            : fa(picked.length) + " انتخاب";
        if (count.textContent !== label) count.textContent = label;
        all.checked = total > 0 && picked.length === total;
        all.indeterminate = picked.length > 0 && picked.length < total;
        bar.querySelectorAll("[data-bulk-go]").forEach(function (button) {
            button.disabled = picked.length === 0;
        });
        queueMicrotask(function () { ignore -= 1; });
    }

    function setPicking(on) {
        layout.classList.toggle("is-picking", on);
        document.body.classList.toggle("is-picking", on);
        toggle.classList.toggle("is-on", on);
        toggle.setAttribute("aria-pressed", on ? "true" : "false");
        bar.hidden = !on;
        if (!on) {
            boxes().forEach(function (box) { box.checked = false; });
            all.checked = false;
            all.indeterminate = false;
        }
        paint();
    }

    toggle.addEventListener("click", function () {
        setPicking(!layout.classList.contains("is-picking"));
    });

    var closeBtn = bar.querySelector("[data-bulk-close]");
    if (closeBtn) {
        closeBtn.addEventListener("click", function () {
            setPicking(false);
        });
    }

    layout.addEventListener("change", function (event) {
        if (event.target.matches("[data-pick]")) paint();
    });

    layout.addEventListener("click", function (event) {
        if (!layout.classList.contains("is-picking")) return;
        if (event.target.closest("a, button, input, label, .pick-box")) return;
        var summary = event.target.closest(".pick-summary");
        if (!summary) return;
        var box = summary.parentElement && summary.parentElement.querySelector("[data-pick]");
        if (!box) return;
        box.checked = !box.checked;
        paint();
    });

    all.addEventListener("change", function () {
        var on = all.checked;
        boxes().forEach(function (box) { box.checked = on; });
        paint();
    });

    new MutationObserver(function () {
        if (ignore || bar.hidden) return;
        paint();
    }).observe(layout, { childList: true, subtree: true });

    function csrf() {
        var input = document.querySelector("[name=csrfmiddlewaretoken]");
        if (input) return input.value;
        var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function slugs() {
        return chosen().map(function (box) { return box.value; });
    }

    function signedIn() {
        if (bar.dataset.auth === "1") return true;
        if (typeof window.openHonarLogin === "function") {
            try {
                var next = "";
                var href = bar.dataset.login || "";
                var match = href.match(/[?&]next=([^&]+)/);
                if (match) next = decodeURIComponent(match[1]);
                window.openHonarLogin(next, "phone");
            } catch (error) {
                window.location = bar.dataset.login;
            }
            return false;
        }
        window.location = bar.dataset.login;
        return false;
    }

    function post(url, values) {
        var body = new FormData();
        values.forEach(function (slug) { body.append("slug", slug); });
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "X-CSRFToken": csrf(), "X-Requested-With": "fetch" },
            body: body
        }).then(function (response) {
            return response.json().catch(function () { return {}; }).then(function (payload) {
                if (!response.ok) throw new Error(payload.error || "انجام نشد.");
                return payload;
            });
        });
    }

    var bookmark = bar.querySelector("[data-bulk-bookmark]");
    if (bookmark) {
        bookmark.addEventListener("click", function () {
            var values = slugs();
            if (!values.length || !signedIn()) return;
            bookmark.disabled = true;
            post(bar.dataset.bookmark, values).then(function (payload) {
                values.forEach(function (slug) {
                    var box = layout.querySelector('[data-pick][value="' + CSS.escape(slug) + '"]');
                    var mark = box && box.closest("article") && box.closest("article").querySelector(".card-mark__btn");
                    if (!mark) return;
                    mark.classList.add("is-on");
                    mark.setAttribute("aria-pressed", "true");
                    mark.setAttribute("aria-label", "حذف از نشان‌شده‌ها");
                });
                window.showToast(payload.message);
            }).catch(function (error) {
                window.showToast(error.message);
            }).finally(function () { paint(); });
        });
    }

    var apply = bar.querySelector("[data-bulk-apply]");
    if (apply) {
        apply.addEventListener("click", function () {
            var values = slugs();
            if (!values.length || !signedIn()) return;
            apply.disabled = true;
            post(bar.dataset.apply, values).then(function (payload) {
                window.showToast(payload.message);
            }).catch(function (error) {
                window.showToast(error.message);
            }).finally(function () { paint(); });
        });
    }

    var invite = bar.querySelector("[data-bulk-invite]");
    if (invite) {
        invite.addEventListener("click", function () {
            var values = slugs();
            if (!values.length || !signedIn() || !window.Alpine) return;
            var state = Alpine.$data(layout);
            var first = layout.querySelector('[data-pick][value="' + CSS.escape(values[0]) + '"]');
            var card = first && first.closest("article");
            var opener = card && card.querySelector("[data-invite-open]");
            state.inviteSlugs = values;
            state.inviteSlug = values[0];
            state.inviteName = values.length > 1 ? fa(values.length) + " هنرمند" : (opener ? opener.getAttribute("data-invite-name") : "");
            state.inviteRoles = values.length === 1 && opener ? (opener.getAttribute("data-invite-roles") || "").split("||").filter(Boolean) : [];
            state.inviteProject = "";
            state.notice = "";
            state.inviteOpen = true;
        });
    }

    var mobileApply = document.querySelector("[data-mobile-apply]");
    if (mobileApply && apply) {
        function syncMobileApply() {
            var picked = chosen().length;
            if (!layout.classList.contains("is-picking")) {
                mobileApply.textContent = "ارسال درخواست";
                return;
            }
            mobileApply.textContent = picked
                ? "ارسال درخواست (" + fa(picked) + ")"
                : "ارسال درخواست";
        }
        mobileApply.addEventListener("click", function () {
            if (!layout.classList.contains("is-picking")) {
                toggle.click();
                if (window.showToast) window.showToast("فراخوان‌ها را انتخاب کنید، بعد دوباره بزنید.");
                syncMobileApply();
                return;
            }
            if (!chosen().length) {
                if (window.showToast) window.showToast("حداقل یک فراخوان را انتخاب کنید.");
                return;
            }
            apply.click();
        });
        layout.addEventListener("change", syncMobileApply);
        toggle.addEventListener("click", function () {
            queueMicrotask(syncMobileApply);
        });
        syncMobileApply();
    }
})();

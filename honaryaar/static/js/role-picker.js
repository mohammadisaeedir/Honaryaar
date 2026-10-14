(function () {
    function fold(value) {
        return String(value || "")
            .trim()
            .replace(/ي/g, "ی")
            .replace(/ك/g, "ک")
            .replace(/[۰-۹]/g, function (digit) {
                return String("۰۱۲۳۴۵۶۷۸۹".indexOf(digit));
            })
            .toLowerCase();
    }

    function mount(root) {
        if (root.dataset.roleReady === "1") return;
        root.dataset.roleReady = "1";
        var scripts = root.querySelectorAll("script[type='application/json']");
        if (scripts.length < 2) return;
        var catalog;
        var chosen;
        try {
            catalog = JSON.parse(scripts[0].textContent);
            chosen = JSON.parse(scripts[1].textContent);
        } catch (error) {
            return;
        }
        var state = { chosen: chosen, query: "", category: "", draftId: null, notice: "", open: false, editId: null, pick: null };
        var mobileQuery = window.matchMedia("(max-width: 767.98px)");

        function iconButton(label, name) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "me-icon-btn" + (name === "trash" ? " is-danger" : "") + (name === "pencil" && label === "اصلی" ? " is-on" : "");
            button.setAttribute("aria-label", label);
            var source = root.querySelector("template[data-icon='" + name + "']");
            if (source) button.append(source.content.cloneNode(true));
            return button;
        }
        var list = root.querySelector("[data-role-chosen-list]");
        var empty = root.querySelector("[data-role-empty]");
        var inputs = root.querySelector("[data-role-inputs]");
        var modal = root.querySelector("[data-role-modal]");
        var search = root.querySelector("[data-role-search]");
        var results = root.querySelector("[data-role-results]");
        var bar = root.querySelector("[data-role-bar]");
        var barName = root.querySelector("[data-role-bar-name]");
        var panel = root.querySelector(".skill-modal__panel");
        var title = modal.querySelector("#role-modal-title");

        function taken() {
            var ids = {};
            state.chosen.forEach(function (item) {
                if (item.id !== state.editId) ids[item.id] = true;
            });
            return ids;
        }

        function roleById(id) {
            var role = null;
            catalog.forEach(function (item) {
                if (item.id === id) role = item;
            });
            return role;
        }

        function ensurePrimary() {
            if (!state.chosen.length) return;
            if (state.chosen.some(function (item) { return item.primary; })) return;
            state.chosen[0].primary = true;
        }

        function renderChosen() {
            ensurePrimary();
            list.replaceChildren();
            inputs.replaceChildren();
            empty.hidden = state.chosen.length > 0;
            state.chosen.forEach(function (item) {
                if (root.dataset.layout === "table") {
                    var tr = document.createElement("tr");
                    var nameCell = document.createElement("td");
                    nameCell.textContent = item.title;
                    if (item.primary) {
                        var badge = document.createElement("span");
                        badge.className = "me-badge";
                        badge.textContent = "اصلی";
                        nameCell.append(badge);
                    }
                    var categoryCell = document.createElement("td");
                    categoryCell.textContent = item.category;
                    var actions = document.createElement("td");
                    actions.className = "me-sheet__actions";
                    var edit = iconButton("ویرایش", "pencil");
                    edit.addEventListener("click", function () {
                        state.editId = item.id;
                        state.category = item.category || "";
                        state.draftId = item.id;
                        state.query = "";
                        state.notice = "";
                        search.value = "";
                        state.pick = null;
                        open();
                    });
                    var remove = iconButton("حذف", "trash");
                    remove.addEventListener("click", function () {
                        var drop = function () {
                            state.chosen = state.chosen.filter(function (rowItem) {
                                return rowItem.id !== item.id;
                            });
                            renderChosen();
                            if (state.open) renderResults();
                            persist();
                        };
                        if (window.honarAskRemove) window.honarAskRemove(drop, "حذف نقش", "این نقش حذف شود؟");
                        else drop();
                    });
                    actions.append(edit, remove);
                    tr.append(nameCell, categoryCell, actions);
                    list.append(tr);
                    var input = document.createElement("input");
                    input.type = "hidden";
                    input.name = "role-" + item.id;
                    input.value = "1";
                    inputs.append(input);
                    if (item.primary) {
                        var primaryInput = document.createElement("input");
                        primaryInput.type = "hidden";
                        primaryInput.name = "role_primary";
                        primaryInput.value = String(item.id);
                        inputs.append(primaryInput);
                    }
                    return;
                }
                var row = document.createElement("div");
                row.className = "skill-picker__row";
                var text = document.createElement("div");
                text.className = "skill-picker__text";
                var title = document.createElement("p");
                title.className = "skill-picker__name";
                title.textContent = item.title;
                var category = document.createElement("p");
                category.className = "skill-picker__meta";
                category.textContent = item.category;
                text.append(title, category);
                var primary = document.createElement("button");
                primary.type = "button";
                primary.className = "skill-picker__primary" + (item.primary ? " is-on" : "");
                primary.textContent = "اصلی";
                primary.setAttribute("aria-pressed", item.primary ? "true" : "false");
                primary.addEventListener("click", function () {
                    state.chosen.forEach(function (rowItem) {
                        rowItem.primary = rowItem.id === item.id;
                    });
                    renderChosen();
                });
                var remove = document.createElement("button");
                remove.type = "button";
                remove.className = "skill-picker__remove";
                remove.textContent = "حذف";
                remove.addEventListener("click", function () {
                    state.chosen = state.chosen.filter(function (rowItem) {
                        return rowItem.id !== item.id;
                    });
                    renderChosen();
                    if (state.open) renderResults();
                });
                row.append(text, primary, remove);
                list.append(row);
                var input = document.createElement("input");
                input.type = "hidden";
                input.name = "role-" + item.id;
                input.value = "1";
                inputs.append(input);
                if (item.primary) {
                    var primaryInput = document.createElement("input");
                    primaryInput.type = "hidden";
                    primaryInput.name = "role_primary";
                    primaryInput.value = String(item.id);
                    inputs.append(primaryInput);
                }
            });
        }

        function available(role) {
            if (state.pick) return true;
            return !taken()[role.id];
        }

        function finishPick(role) {
            var done = state.pick;
            state.pick = null;
            close();
            if (done && role) done(role);
        }

        function categories() {
            var seen = {};
            var names = [];
            catalog.forEach(function (role) {
                if (!available(role) || !role.category || seen[role.category]) return;
                seen[role.category] = true;
                names.push(role.category);
            });
            return names;
        }

        function filtered() {
            var query = fold(state.query);
            return catalog.filter(function (role) {
                if (!available(role)) return false;
                if (query) return fold(role.title).indexOf(query) !== -1 || fold(role.category).indexOf(query) !== -1;
                return !state.category || role.category === state.category;
            });
        }

        function syncBar() {
            var role = null;
            catalog.forEach(function (item) {
                if (item.id === state.draftId && available(item)) role = item;
            });
            if (!role) state.draftId = null;
            var show = mobileQuery.matches && !!role;
            bar.hidden = !show;
            barName.textContent = role ? (role.category ? role.category + " | " + role.title : role.title) : "";
            var confirm = bar.querySelector("[data-role-confirm]");
            if (confirm) confirm.textContent = state.pick ? "انتخاب" : (state.editId ? "ذخیره" : "افزودن");
        }

        function saveEdit() {
            var role = roleById(state.draftId);
            if (!role || taken()[role.id]) return;
            if (role.id === state.editId) {
                close();
                return;
            }
            state.chosen = state.chosen.map(function (item) {
                if (item.id !== state.editId) return item;
                return { id: role.id, title: role.title, category: role.category, primary: item.primary };
            });
            close();
            renderChosen();
            persist();
        }

        function addDraft() {
            var role = roleById(state.draftId);
            if (!role || taken()[role.id]) return;
            state.chosen.push({
                id: role.id,
                title: role.title,
                category: role.category,
                primary: state.chosen.length === 0,
            });
            state.draftId = null;
            state.notice = "اضافه شد. نقش بعدی را انتخاب کنید.";
            renderChosen();
            renderResults();
            if (persist()) return;
            search.focus();
        }

        function persist() {
            var form = root.closest("form");
            if (!form || form.getAttribute("data-autosave") !== "1") return false;
            window.setTimeout(function () { form.requestSubmit(); }, 0);
            return true;
        }

        function emptyNote(text) {
            var note = document.createElement("p");
            note.className = "skill-modal__empty";
            note.textContent = text;
            results.append(note);
        }

        function roleRow(role, label) {
            var row = document.createElement("div");
            row.className = "role-pick__row" + (state.draftId === role.id ? " is-on" : "");
            var button = document.createElement("button");
            button.type = "button";
            button.className = "role-pick__item";
            button.textContent = label;
            button.addEventListener("click", function () {
                if (!mobileQuery.matches) return;
                state.draftId = state.draftId === role.id ? null : role.id;
                renderResults();
            });
            var add = document.createElement("button");
            add.type = "button";
            add.className = "role-pick__add";
            add.textContent = state.pick ? "انتخاب" : (state.editId ? "ذخیره" : "افزودن");
            add.addEventListener("click", function () {
                state.draftId = role.id;
                if (state.pick) finishPick(role);
                else if (state.editId) saveEdit();
                else addDraft();
            });
            row.append(button, add);
            return row;
        }

        function renderResults() {
            var query = fold(state.query);
            var scroll = results.scrollTop;
            results.replaceChildren();
            if (!query && !state.category) {
                var names = categories();
                if (!names.length) emptyNote("نقش دیگری برای افزودن نمانده.");
                names.forEach(function (name) {
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "role-pick__category";
                    var text = document.createElement("span");
                    text.textContent = name;
                    button.append(text);
                    var source = root.querySelector("template[data-icon='chevron']");
                    if (source) button.append(source.content.cloneNode(true));
                    button.addEventListener("click", function () {
                        state.category = name;
                        state.draftId = null;
                        renderResults();
                    });
                    results.append(button);
                });
                syncBar();
                return;
            }
            if (!query && state.category) {
                var back = document.createElement("button");
                back.type = "button";
                back.className = "role-pick__back";
                back.textContent = state.category;
                var source = root.querySelector("template[data-icon='chevron']");
                if (source) back.prepend(source.content.cloneNode(true));
                back.addEventListener("click", function () {
                    state.category = "";
                    state.draftId = null;
                    renderResults();
                });
                results.append(back);
            }
            var rows = filtered();
            if (!rows.length) emptyNote(query ? "نقشی پیدا نشد." : "نقش دیگری در این دسته نمانده.");
            rows.forEach(function (role) {
                var label = query && role.category ? role.category + " | " + role.title : role.title;
                results.append(roleRow(role, label));
            });
            syncBar();
            results.scrollTop = scroll;
        }

        function open() {
            if (modal.parentElement !== document.body) document.body.append(modal);
            state.open = true;
            if (!state.editId) {
                state.category = "";
                state.draftId = null;
                state.query = "";
                search.value = "";
            }
            if (title) title.textContent = state.editId ? "ویرایش نقش" : "انتخاب نقش";
            modal.hidden = false;
            document.body.classList.add("skill-modal-open");
            renderResults();
            search.focus();
        }

        function close() {
            state.open = false;
            state.editId = null;
            state.category = "";
            state.pick = null;
            state.draftId = null;
            state.notice = "";
            modal.hidden = true;
            if (bar) bar.hidden = true;
            document.body.classList.remove("skill-modal-open");
        }

        root.querySelector("[data-role-open]").addEventListener("click", function () {
            state.editId = null;
            state.pick = null;
            open();
        });
        window.honarPickRole = function (done) {
            state.pick = done;
            state.editId = null;
            open();
        };
        root.querySelector("[data-role-close]").addEventListener("click", close);
        root.querySelector("[data-role-backdrop]").addEventListener("click", close);
        search.addEventListener("input", function () {
            state.query = search.value;
            state.draftId = null;
            renderResults();
        });
        root.querySelector("[data-role-confirm]").addEventListener("click", function () {
            if (state.pick) finishPick(roleById(state.draftId));
            else if (state.editId) saveEdit();
            else addDraft();
        });
        panel.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            event.preventDefault();
            if (!state.draftId) return;
            if (state.pick) finishPick(roleById(state.draftId));
            else if (state.editId) saveEdit();
            else addDraft();
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && state.open) close();
        });
        renderChosen();
    }

    function boot() {
        document.querySelectorAll("[data-role-picker]").forEach(mount);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();

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
        var state = { chosen: chosen, query: "", draftId: null, notice: "", open: false };
        var list = root.querySelector("[data-role-chosen-list]");
        var empty = root.querySelector("[data-role-empty]");
        var inputs = root.querySelector("[data-role-inputs]");
        var modal = root.querySelector("[data-role-modal]");
        var search = root.querySelector("[data-role-search]");
        var results = root.querySelector("[data-role-results]");
        var draft = root.querySelector("[data-role-draft]");
        var panel = root.querySelector(".skill-modal__panel");

        function taken() {
            var ids = {};
            state.chosen.forEach(function (item) {
                ids[item.id] = true;
            });
            return ids;
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

        function filtered() {
            var query = fold(state.query);
            if (!query) return [];
            var used = taken();
            return catalog.filter(function (role) {
                if (used[role.id]) return false;
                return fold(role.title).indexOf(query) !== -1 || fold(role.category).indexOf(query) !== -1;
            });
        }

        function renderDraft() {
            draft.replaceChildren();
            var role = null;
            catalog.forEach(function (item) {
                if (item.id === state.draftId) role = item;
            });
            if (!role || taken()[role.id]) {
                state.draftId = null;
                var hint = document.createElement("p");
                hint.className = "skill-modal__hint";
                hint.textContent = state.notice || "نام نقش یا دسته را بنویسید.";
                draft.append(hint);
                return;
            }
            var box = document.createElement("div");
            box.className = "skill-modal__pick";
            var label = document.createElement("p");
            label.className = "skill-modal__pick-name";
            label.textContent = role.title;
            var caption = document.createElement("p");
            caption.className = "skill-modal__pick-meta";
            caption.textContent = role.category;
            var add = document.createElement("button");
            add.type = "button";
            add.className = "skill-modal__confirm";
            add.textContent = "افزودن";
            add.addEventListener("click", addDraft);
            box.append(label, caption, add);
            draft.append(box);
        }

        function addDraft() {
            var role = null;
            catalog.forEach(function (item) {
                if (item.id === state.draftId) role = item;
            });
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
            search.focus();
        }

        function renderResults() {
            var query = fold(state.query);
            var scroll = results.scrollTop;
            results.replaceChildren();
            if (!query) {
                var hint = document.createElement("p");
                hint.className = "skill-modal__empty";
                hint.textContent = "نام نقش یا دسته را بنویسید.";
                results.append(hint);
                renderDraft();
                return;
            }
            var rows = filtered();
            if (!rows.length) {
                var note = document.createElement("p");
                note.className = "skill-modal__empty";
                note.textContent = "نقشی پیدا نشد.";
                results.append(note);
                renderDraft();
                results.scrollTop = scroll;
                return;
            }
            var last = "";
            rows.forEach(function (role) {
                if (role.category !== last) {
                    last = role.category;
                    var heading = document.createElement("p");
                    heading.className = "skill-modal__group";
                    heading.textContent = role.category;
                    results.append(heading);
                }
                var button = document.createElement("button");
                button.type = "button";
                button.className = "skill-modal__skill" + (state.draftId === role.id ? " is-on" : "");
                var name = document.createElement("span");
                name.className = "skill-modal__skill-name";
                name.textContent = role.title;
                button.append(name);
                button.addEventListener("click", function () {
                    if (state.draftId !== role.id) {
                        state.draftId = role.id;
                        state.notice = "";
                    }
                    renderResults();
                });
                results.append(button);
            });
            renderDraft();
            results.scrollTop = scroll;
        }

        function open() {
            if (modal.parentElement !== document.body) document.body.append(modal);
            state.open = true;
            modal.hidden = false;
            document.body.classList.add("skill-modal-open");
            renderResults();
            search.focus();
        }

        function close() {
            state.open = false;
            state.draftId = null;
            state.notice = "";
            modal.hidden = true;
            document.body.classList.remove("skill-modal-open");
        }

        root.querySelector("[data-role-open]").addEventListener("click", open);
        root.querySelector("[data-role-close]").addEventListener("click", close);
        root.querySelector("[data-role-backdrop]").addEventListener("click", close);
        search.addEventListener("input", function () {
            state.query = search.value;
            renderResults();
        });
        panel.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            event.preventDefault();
            if (state.draftId) addDraft();
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

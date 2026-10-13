(function () {
    var LEVELS = ["۱", "۲", "۳", "۴", "۵"];

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

    function dots(level, onPick) {
        var wrap = document.createElement("span");
        wrap.className = "skill-picker__rate";
        wrap.dir = "ltr";
        for (var n = 5; n >= 1; n -= 1) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "skill-picker__dot" + (n <= level ? " is-on" : "");
            button.setAttribute("aria-label", "سطح " + LEVELS[n - 1]);
            button.setAttribute("aria-pressed", n <= level ? "true" : "false");
            button.addEventListener("click", onPick.bind(null, n));
            wrap.append(button);
        }
        return wrap;
    }

    function mount(root) {
        if (root.dataset.skillReady === "1") return;
        root.dataset.skillReady = "1";
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
        var state = { chosen: chosen, query: "", draftId: null, draftLevel: 0, notice: "", open: false };
        var list = root.querySelector("[data-skill-chosen-list]");
        var empty = root.querySelector("[data-skill-empty]");
        var inputs = root.querySelector("[data-skill-inputs]");
        var modal = root.querySelector("[data-skill-modal]");
        var search = root.querySelector("[data-skill-search]");
        var results = root.querySelector("[data-skill-results]");
        var draft = root.querySelector("[data-skill-draft]");
        var panel = root.querySelector(".skill-modal__panel");

        function taken() {
            var ids = {};
            state.chosen.forEach(function (item) {
                ids[item.id] = true;
            });
            return ids;
        }

        function renderChosen() {
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
                var rate = dots(item.level, function (level) {
                    item.level = level;
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
                row.append(text, rate, remove);
                list.append(row);
                var input = document.createElement("input");
                input.type = "hidden";
                input.name = "skill-" + item.id;
                input.value = String(item.level);
                inputs.append(input);
            });
        }

        function filtered() {
            var query = fold(state.query);
            var used = taken();
            return catalog.filter(function (skill) {
                if (used[skill.id]) return false;
                if (!query) return true;
                return fold(skill.title).indexOf(query) !== -1 || fold(skill.category).indexOf(query) !== -1;
            });
        }

        function renderDraft() {
            draft.replaceChildren();
            var skill = null;
            catalog.forEach(function (item) {
                if (item.id === state.draftId) skill = item;
            });
            if (!skill || taken()[skill.id]) {
                state.draftId = null;
                state.draftLevel = 0;
                var hint = document.createElement("p");
                hint.className = "skill-modal__hint";
                hint.textContent = state.notice || "از فهرست یک مهارت را انتخاب کنید.";
                draft.append(hint);
                return;
            }
            var box = document.createElement("div");
            box.className = "skill-modal__pick";
            var label = document.createElement("p");
            label.className = "skill-modal__pick-name";
            label.textContent = skill.title;
            var caption = document.createElement("p");
            caption.className = "skill-modal__pick-meta";
            caption.textContent = skill.category + " · سطح را از ۱ تا ۵ انتخاب کنید";
            var rate = dots(state.draftLevel, function (level) {
                state.draftLevel = level;
                renderDraft();
            });
            var add = document.createElement("button");
            add.type = "button";
            add.className = "skill-modal__confirm";
            add.textContent = "افزودن";
            add.disabled = !state.draftLevel;
            add.addEventListener("click", addDraft);
            box.append(label, caption, rate, add);
            draft.append(box);
        }

        function addDraft() {
            var skill = null;
            catalog.forEach(function (item) {
                if (item.id === state.draftId) skill = item;
            });
            if (!skill || !state.draftLevel || taken()[skill.id]) return;
            state.chosen.push({
                id: skill.id,
                title: skill.title,
                category: skill.category,
                level: state.draftLevel,
            });
            state.draftId = null;
            state.draftLevel = 0;
            state.notice = "اضافه شد. مهارت بعدی را انتخاب کنید.";
            renderChosen();
            renderResults();
            search.focus();
        }

        function renderResults() {
            var rows = filtered();
            var scroll = results.scrollTop;
            results.replaceChildren();
            if (!rows.length) {
                var note = document.createElement("p");
                note.className = "skill-modal__empty";
                note.textContent = state.query.trim() ? "مهارتی پیدا نشد." : "مهارت دیگری برای افزودن نمانده.";
                results.append(note);
                renderDraft();
                results.scrollTop = scroll;
                return;
            }
            var last = "";
            rows.forEach(function (skill) {
                if (skill.category !== last) {
                    last = skill.category;
                    var heading = document.createElement("p");
                    heading.className = "skill-modal__group";
                    heading.textContent = skill.category;
                    results.append(heading);
                }
                var button = document.createElement("button");
                button.type = "button";
                button.className = "skill-modal__skill" + (state.draftId === skill.id ? " is-on" : "");
                var name = document.createElement("span");
                name.className = "skill-modal__skill-name";
                name.textContent = skill.title;
                button.append(name);
                button.addEventListener("click", function () {
                    if (state.draftId !== skill.id) {
                        state.draftId = skill.id;
                        state.draftLevel = 0;
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
            state.draftLevel = 0;
            state.notice = "";
            modal.hidden = true;
            document.body.classList.remove("skill-modal-open");
        }

        root.querySelector("[data-skill-open]").addEventListener("click", open);
        root.querySelector("[data-skill-close]").addEventListener("click", close);
        root.querySelector("[data-skill-backdrop]").addEventListener("click", close);
        search.addEventListener("input", function () {
            state.query = search.value;
            renderResults();
        });
        panel.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            event.preventDefault();
            if (state.draftLevel) addDraft();
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && state.open) close();
        });
        renderChosen();
    }

    function boot() {
        document.querySelectorAll("[data-skill-picker]").forEach(mount);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();

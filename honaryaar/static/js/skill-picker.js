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

    function staticDots(level) {
        var wrap = document.createElement("span");
        wrap.className = "skill-picker__rate is-static";
        wrap.dir = "ltr";
        wrap.setAttribute("aria-label", "سطح " + LEVELS[level - 1]);
        for (var n = 5; n >= 1; n -= 1) {
            var mark = document.createElement("span");
            mark.className = "skill-picker__dot" + (n <= level ? " is-on" : "");
            wrap.append(mark);
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
        var state = { chosen: chosen, query: "", category: "", draftId: null, draftLevel: 0, notice: "", open: false, editId: null };
        var mobileQuery = window.matchMedia("(max-width: 767.98px)");

        function iconButton(label, name) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "me-icon-btn" + (name === "trash" ? " is-danger" : "");
            button.setAttribute("aria-label", label);
            var source = root.querySelector("template[data-icon='" + name + "']");
            if (source) button.append(source.content.cloneNode(true));
            return button;
        }
        var list = root.querySelector("[data-skill-chosen-list]");
        var empty = root.querySelector("[data-skill-empty]");
        var inputs = root.querySelector("[data-skill-inputs]");
        var modal = root.querySelector("[data-skill-modal]");
        var search = root.querySelector("[data-skill-search]");
        var results = root.querySelector("[data-skill-results]");
        var panel = root.querySelector(".skill-modal__panel");
        var title = modal.querySelector("#skill-modal-title");

        function taken() {
            var ids = {};
            state.chosen.forEach(function (item) {
                if (item.id !== state.editId) ids[item.id] = true;
            });
            return ids;
        }

        function skillById(id) {
            var skill = null;
            catalog.forEach(function (item) {
                if (item.id === id) skill = item;
            });
            return skill;
        }

        function renderChosen() {
            list.replaceChildren();
            inputs.replaceChildren();
            empty.hidden = state.chosen.length > 0;
            state.chosen.forEach(function (item) {
                if (root.dataset.layout === "table") {
                    var tr = document.createElement("tr");
                    var nameCell = document.createElement("td");
                    nameCell.textContent = item.title;
                    var categoryCell = document.createElement("td");
                    categoryCell.textContent = item.category;
                    var levelCell = document.createElement("td");
                    levelCell.append(staticDots(item.level));
                    var actions = document.createElement("td");
                    actions.className = "me-sheet__actions";
                    var edit = iconButton("ویرایش", "pencil");
                    edit.addEventListener("click", function () {
                        state.editId = item.id;
                        state.category = item.category || "";
                        state.draftId = item.id;
                        state.draftLevel = item.level;
                        state.query = "";
                        state.notice = "";
                        search.value = "";
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
                        if (window.honarAskRemove) window.honarAskRemove(drop, "حذف مهارت", "این مهارت حذف شود؟");
                        else drop();
                    });
                    actions.append(edit, remove);
                    tr.append(nameCell, categoryCell, levelCell, actions);
                    list.append(tr);
                    var input = document.createElement("input");
                    input.type = "hidden";
                    input.name = "skill-" + item.id;
                    input.value = String(item.level);
                    inputs.append(input);
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
                if (query) return fold(skill.title).indexOf(query) !== -1 || fold(skill.category).indexOf(query) !== -1;
                return skill.category === state.category;
            });
        }

        function categories() {
            var seen = {};
            var names = [];
            catalog.forEach(function (skill) {
                if (taken()[skill.id] || !skill.category || seen[skill.category]) return;
                seen[skill.category] = true;
                names.push(skill.category);
            });
            return names;
        }

        function skillRow(skill, label) {
            var selected = state.draftId === skill.id;
            var row = document.createElement("div");
            row.className = "role-pick__row skill-pick__row" + (selected ? " is-on" : "");
            var button = document.createElement("button");
            button.type = "button";
            button.className = "role-pick__item";
            button.textContent = label;
            button.addEventListener("click", function () {
                if (!mobileQuery.matches) return;
                if (state.draftId === skill.id) {
                    state.draftId = null;
                    if (!state.editId) state.draftLevel = 0;
                } else {
                    state.draftId = skill.id;
                    if (!state.editId) state.draftLevel = 0;
                }
                renderResults();
            });
            var tools = document.createElement("span");
            tools.className = "skill-pick__tools";
            tools.append(dots(selected ? state.draftLevel : 0, function (level) {
                state.draftId = skill.id;
                state.draftLevel = level;
                renderResults();
            }));
            var add = document.createElement("button");
            add.type = "button";
            add.className = "role-pick__add";
            add.textContent = state.editId ? "ذخیره" : "افزودن";
            add.disabled = !selected || !state.draftLevel;
            add.addEventListener("click", function () {
                state.draftId = skill.id;
                if (!state.draftLevel) return;
                if (state.editId) saveEdit();
                else addDraft();
            });
            tools.append(add);
            row.append(button, tools);
            return row;
        }

        function saveEdit() {
            var skill = skillById(state.draftId);
            if (!skill || !state.draftLevel || taken()[skill.id]) return;
            state.chosen = state.chosen.map(function (item) {
                if (item.id !== state.editId) return item;
                return { id: skill.id, title: skill.title, category: skill.category, level: state.draftLevel };
            });
            close();
            renderChosen();
            persist();
        }

        function addDraft() {
            var skill = skillById(state.draftId);
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

        function renderResults() {
            var query = fold(state.query);
            var scroll = results.scrollTop;
            results.replaceChildren();
            if (!query && !state.category) {
                var names = categories();
                if (!names.length) emptyNote("مهارت دیگری برای افزودن نمانده.");
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
                        if (!state.editId) state.draftLevel = 0;
                        renderResults();
                    });
                    results.append(button);
                });
                results.scrollTop = scroll;
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
                    if (!state.editId) state.draftLevel = 0;
                    renderResults();
                });
                results.append(back);
            }
            var rows = filtered();
            if (!rows.length) emptyNote(query ? "مهارتی پیدا نشد." : "مهارت دیگری در این دسته نمانده.");
            rows.forEach(function (skill) {
                var label = query && skill.category ? skill.category + " | " + skill.title : skill.title;
                results.append(skillRow(skill, label));
            });
            results.scrollTop = scroll;
        }

        function open() {
            if (modal.parentElement !== document.body) document.body.append(modal);
            state.open = true;
            if (!state.editId) {
                state.category = "";
                state.draftId = null;
                state.draftLevel = 0;
                state.query = "";
                search.value = "";
            }
            if (title) title.textContent = state.editId ? "ویرایش مهارت" : "انتخاب مهارت";
            modal.hidden = false;
            document.body.classList.add("skill-modal-open");
            renderResults();
            search.focus();
        }

        function close() {
            state.open = false;
            state.editId = null;
            state.category = "";
            state.draftId = null;
            state.draftLevel = 0;
            state.notice = "";
            modal.hidden = true;
            document.body.classList.remove("skill-modal-open");
        }

        root.querySelector("[data-skill-open]").addEventListener("click", function () {
            state.editId = null;
            state.category = "";
            state.draftId = null;
            state.draftLevel = 0;
            state.query = "";
            state.notice = "";
            search.value = "";
            open();
        });
        root.querySelector("[data-skill-close]").addEventListener("click", close);
        root.querySelector("[data-skill-backdrop]").addEventListener("click", close);
        search.addEventListener("input", function () {
            state.query = search.value;
            state.draftId = null;
            if (!state.editId) state.draftLevel = 0;
            renderResults();
        });
        panel.addEventListener("keydown", function (event) {
            if (event.key !== "Enter") return;
            event.preventDefault();
            if (!state.draftLevel) return;
            if (state.editId) saveEdit();
            else addDraft();
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

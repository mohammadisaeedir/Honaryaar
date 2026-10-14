(function () {
    function mount(root) {
        if (root.dataset.contactReady === "1") return;
        root.dataset.contactReady = "1";
        var scripts = root.querySelectorAll("script[type='application/json']");
        if (scripts.length < 2) return;
        var kinds;
        var chosen;
        try {
            kinds = JSON.parse(scripts[0].textContent);
            chosen = JSON.parse(scripts[1].textContent);
        } catch (error) {
            return;
        }
        var state = { chosen: chosen, edit: null };
        var list = root.querySelector("[data-contact-list]");
        var empty = root.querySelector("[data-contact-empty]");
        var inputs = root.querySelector("[data-contact-inputs]");
        var editor = root.querySelector("[data-contact-editor]");
        var kindField = root.querySelector("[data-contact-kind]");
        var valueField = root.querySelector("[data-contact-value]");
        var publicField = root.querySelector("[data-contact-public]");
        var error = root.querySelector("[data-contact-error]");

        kinds.forEach(function (kind) {
            var option = document.createElement("option");
            option.value = kind.id;
            option.textContent = kind.title;
            kindField.append(option);
        });

        function iconButton(label, name) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "me-icon-btn" + (name === "trash" ? " is-danger" : "");
            button.setAttribute("aria-label", label);
            var source = root.querySelector("template[data-icon='" + name + "']");
            if (source) button.append(source.content.cloneNode(true));
            return button;
        }

        function labelFor(kind) {
            var title = kind;
            kinds.forEach(function (item) {
                if (item.id === kind) title = item.title;
            });
            return title;
        }

        function persist() {
            var form = root.closest("form");
            if (!form || form.getAttribute("data-autosave") !== "1") return false;
            window.setTimeout(function () { form.requestSubmit(); }, 0);
            return true;
        }

        function showError(message) {
            error.hidden = !message;
            error.textContent = message || "";
        }

        function setPublic(on) {
            publicField.classList.toggle("is-on", on);
            publicField.setAttribute("aria-pressed", on ? "true" : "false");
        }

        function publicOn() {
            return publicField.getAttribute("aria-pressed") === "true";
        }

        publicField.addEventListener("click", function () {
            setPublic(!publicOn());
        });

        function openEditor(index) {
            state.edit = index;
            var item = index === null ? null : state.chosen[index];
            kindField.value = item ? item.kind : (kinds[0] ? kinds[0].id : "");
            valueField.value = item ? item.value : "";
            setPublic(item ? !!item.public : true);
            editor.hidden = false;
            showError("");
            valueField.focus();
        }

        function render() {
            list.replaceChildren();
            inputs.replaceChildren();
            empty.hidden = state.chosen.length > 0;
            state.chosen.forEach(function (item, index) {
                var tr = document.createElement("tr");
                var kindCell = document.createElement("td");
                kindCell.textContent = item.label || labelFor(item.kind);
                var valueCell = document.createElement("td");
                valueCell.dir = "ltr";
                valueCell.textContent = item.value;
                var publicCell = document.createElement("td");
                var toggle = document.createElement("button");
                toggle.type = "button";
                toggle.className = "me-switch" + (item.public ? " is-on" : "");
                toggle.setAttribute("aria-pressed", item.public ? "true" : "false");
                toggle.setAttribute("aria-label", "عمومی");
                toggle.innerHTML = "<span></span>";
                toggle.addEventListener("click", function () {
                    item.public = !item.public;
                    render();
                    persist();
                });
                publicCell.append(toggle);
                var actions = document.createElement("td");
                actions.className = "me-sheet__actions";
                var edit = iconButton("ویرایش", "pencil");
                edit.addEventListener("click", function () { openEditor(index); });
                var remove = iconButton("حذف", "trash");
                remove.addEventListener("click", function () {
                    var drop = function () {
                        state.chosen.splice(index, 1);
                        if (state.edit === index) editor.hidden = true;
                        render();
                        persist();
                    };
                    if (window.honarAskRemove) window.honarAskRemove(drop, "حذف راه تماس", "این راه تماس حذف شود؟");
                    else drop();
                });
                actions.append(edit, remove);
                tr.append(kindCell, valueCell, publicCell, actions);
                list.append(tr);
                ["kind", "value", "public"].forEach(function (part) {
                    var input = document.createElement("input");
                    input.type = "hidden";
                    input.name = "contact-" + index + "-" + part;
                    input.value = part === "public" ? (item.public ? "1" : "0") : item[part];
                    inputs.append(input);
                });
            });
        }

        function saveEditor() {
            var kind = kindField.value;
            var value = valueField.value.trim();
            if (!kind || !value) {
                showError("نوع و مقدار را وارد کنید.");
                return;
            }
            var next = { kind: kind, label: labelFor(kind), value: value, public: publicOn() };
            var duplicate = state.chosen.some(function (item, index) {
                return index !== state.edit && item.kind === kind && item.value === value;
            });
            if (duplicate) {
                showError("این راه تماس تکرار شده است.");
                return;
            }
            if (state.edit === null) state.chosen.push(next);
            else state.chosen[state.edit] = next;
            editor.hidden = true;
            state.edit = null;
            render();
            persist();
        }

        root.querySelectorAll("[data-contact-open], [data-contact-add]").forEach(function (button) {
            button.addEventListener("click", function () { openEditor(null); });
        });
        root.querySelector("[data-contact-save]").addEventListener("click", saveEditor);
        render();
    }

    document.querySelectorAll("[data-contact-picker]").forEach(mount);
})();

(function () {
    var BLANK = /^(?:|[-—]+|select value|unknown)$/i;

    function boot(root) {
        if (root.dataset.modalReady) return;
        var openBtn = root.querySelector("[data-modal-open]");
        var modal = root.querySelector("[data-modal]");
        var table = root.querySelector("table.formset");
        if (!openBtn || !modal || !table) return;
        root.dataset.modalReady = "1";

        var options = JSON.parse(table.dataset.inlineFormset).options;
        var slot = modal.querySelector("[data-modal-slot] table");
        var error = modal.querySelector("[data-modal-error]");
        var title = modal.querySelector("[data-modal-title]");
        var addBtn = modal.querySelector("[data-modal-add]");
        var addLabel = title.textContent;
        var draft = null;
        var editing = null;
        var activeRow = null;
        var snapshot = null;

        var head = table.querySelector("thead");
        if (head) head.classList.remove("hidden");

        function totalInput() {
            return root.querySelector("input[name='" + options.prefix + "-TOTAL_FORMS']");
        }

        function maxInput() {
            return root.querySelector("input[name='" + options.prefix + "-MAX_NUM_FORMS']");
        }

        function groups() {
            return table.querySelectorAll(":scope > .form-group:not(.empty-form)");
        }

        function canAdd() {
            var max = maxInput();
            if (!max || max.value === "") return true;
            return parseInt(totalInput().value, 10) < parseInt(max.value, 10);
        }

        function syncButton() {
            openBtn.hidden = !canAdd();
        }

        function formRow(group) {
            return group.querySelector(":scope > .form-row");
        }

        function fieldText(cell) {
            var boxes = cell.querySelectorAll("input[type=checkbox]");
            if (boxes.length) {
                var picked = [];
                boxes.forEach(function (box) {
                    if (!box.checked) return;
                    var label = box.closest("label");
                    var text = label ? label.textContent.replace(/\s+/g, " ").trim() : "Yes";
                    if (text) picked.push(text);
                });
                return picked.join(", ");
            }
            var select = cell.querySelector("select");
            if (select) {
                var names = [];
                Array.prototype.forEach.call(select.selectedOptions, function (option) {
                    var text = option.textContent.replace(/\s+/g, " ").trim();
                    if (text && !BLANK.test(text)) names.push(text);
                });
                return names.join(", ");
            }
            var input = cell.querySelector("textarea, input:not([type=hidden])");
            if (input) return input.value.replace(/\s+/g, " ").trim();
            var clone = cell.cloneNode(true);
            clone.querySelectorAll(".inline-add__label, .help, .errorlist").forEach(function (node) {
                node.remove();
            });
            return clone.textContent.replace(/\s+/g, " ").trim();
        }

        function paint(group) {
            var row = formRow(group);
            if (!row) return;
            var previous = group.querySelector(":scope > .inline-summary");
            if (previous) previous.remove();
            var summary = document.createElement("tr");
            summary.className = "inline-summary";
            summary.addEventListener("click", function () {
                openEditor(group);
            });
            group.appendChild(summary);
            row.querySelectorAll(":scope > td").forEach(function (cell) {
                var td = document.createElement("td");
                if (cell.classList.contains("delete")) {
                    td.className = "inline-summary__actions";
                    var button = document.createElement("button");
                    button.type = "button";
                    button.className = "inline-summary__delete";
                    button.setAttribute("aria-label", "Remove");
                    button.innerHTML = '<span class="material-symbols-outlined" aria-hidden="true">delete</span>';
                    button.addEventListener("click", function (event) {
                        event.preventDefault();
                        event.stopPropagation();
                        remove(group);
                    });
                    td.appendChild(button);
                } else {
                    var text = fieldText(cell);
                    td.textContent = text || "—";
                    if (cell.querySelector(".errors, .errorlist")) td.classList.add("is-error");
                }
                summary.appendChild(td);
            });
            var deleted = group.querySelector("input[name$='-DELETE']");
            summary.classList.toggle("is-removed", !!(deleted && deleted.checked));
        }

        function labelCells(row) {
            var heads = table.querySelectorAll("thead th");
            var seen = 0;
            row.querySelectorAll(":scope > td").forEach(function (cell) {
                if (cell.classList.contains("delete") || cell.classList.contains("hidden!")) return;
                if (cell.querySelector(".inline-add__label")) {
                    seen += 1;
                    return;
                }
                var headCell = heads[seen];
                seen += 1;
                if (!headCell) return;
                var source = headCell.querySelector("span span") || headCell;
                var text = source.textContent.replace("*", "").trim();
                if (!text) return;
                var label = document.createElement("span");
                label.className = "inline-add__label";
                label.textContent = text;
                cell.prepend(label);
            });
        }

        function placeDropdown(row, parent) {
            if (!window.django || !django.jQuery) return;
            var $ = django.jQuery;
            $(row).find("select.admin-autocomplete, select.unfold-admin-autocomplete").each(function () {
                var $el = $(this);
                if ($el.hasClass("select2-hidden-accessible")) {
                    try {
                        $el.select2("destroy");
                    } catch (err) {
                        $el.removeClass("select2-hidden-accessible");
                    }
                }
                var ajax = $el.hasClass("admin-autocomplete")
                    ? {
                        data: function (params) {
                            return {
                                term: params.term,
                                page: params.page,
                                app_label: this.dataset.appLabel,
                                model_name: this.dataset.modelName,
                                field_name: this.dataset.fieldName,
                            };
                        }.bind(this),
                    }
                    : undefined;
                $el.select2({ dropdownParent: $(parent), width: "100%", ajax: ajax });
            });
        }

        function remember(row) {
            return Array.prototype.map.call(row.querySelectorAll("input, select, textarea"), function (field) {
                if (field.type === "checkbox" || field.type === "radio") return field.checked;
                return field.value;
            });
        }

        function restore(row, values) {
            if (!values) return;
            row.querySelectorAll("input, select, textarea").forEach(function (field, index) {
                if (field.type === "checkbox" || field.type === "radio") field.checked = values[index];
                else field.value = values[index];
                field.dispatchEvent(new Event("change", { bubbles: true }));
            });
        }

        function showModal(isNew) {
            error.hidden = true;
            title.textContent = isNew ? addLabel : addLabel.replace(/^Add\b/, "Edit");
            addBtn.textContent = isNew ? "Add" : "Save";
            modal.classList.add("is-open");
            var first = slot.querySelector("input:not([type=hidden]), select, textarea");
            if (first) first.focus();
        }

        function closeModal() {
            modal.classList.remove("is-open");
        }

        function park(row, group) {
            var anchor = group.querySelector(":scope > .inline-summary");
            if (anchor) group.insertBefore(row, anchor);
            else group.appendChild(row);
        }

        function createDraft() {
            var template = table.querySelector(":scope > .empty-form");
            var row = template.cloneNode(true);
            row.classList.remove("empty-form");
            slot.appendChild(row);
            var index = parseInt(totalInput().value, 10);
            totalInput().value = String(index + 1);
            row.dispatchEvent(new CustomEvent("formsetGroup:added", {
                bubbles: true,
                detail: { formsetName: options.prefix, row: row, index: index },
            }));
            var fields = formRow(row);
            labelCells(fields);
            placeDropdown(fields, modal.querySelector(".inline-add__panel"));
            return row;
        }

        function openModal() {
            if (!canAdd() || editing) return;
            if (!draft) draft = createDraft();
            showModal(true);
        }

        function openEditor(group) {
            if (draft || editing) return;
            var row = formRow(group);
            if (!row) return;
            editing = group;
            activeRow = row;
            snapshot = remember(row);
            slot.appendChild(row);
            labelCells(row);
            placeDropdown(row, modal.querySelector(".inline-add__panel"));
            showModal(false);
        }

        function discard() {
            if (!draft) return;
            draft.remove();
            totalInput().value = String(Math.max(0, parseInt(totalInput().value, 10) - 1));
            draft = null;
        }

        function fieldReady(field) {
            if (!field || field.disabled || field.type === "hidden" || field.type === "checkbox") return true;
            if (field.closest(".delete")) return true;
            return field.checkValidity();
        }

        function confirmAdd() {
            var row = draft ? formRow(draft) : activeRow;
            var fields = row.querySelectorAll("input, select, textarea");
            for (var i = 0; i < fields.length; i += 1) {
                if (!fieldReady(fields[i])) {
                    error.hidden = false;
                    fields[i].reportValidity();
                    return;
                }
            }
            if (draft) {
                var template = table.querySelector(":scope > .empty-form");
                placeDropdown(formRow(draft), document.body);
                table.insertBefore(draft, template);
                paint(draft);
                draft = null;
            } else {
                placeDropdown(activeRow, document.body);
                park(activeRow, editing);
                paint(editing);
                editing = null;
                activeRow = null;
                snapshot = null;
            }
            closeModal();
            syncButton();
        }

        function cancel() {
            if (draft) discard();
            if (editing) {
                restore(activeRow, snapshot);
                park(activeRow, editing);
                paint(editing);
                editing = null;
                activeRow = null;
                snapshot = null;
            }
            closeModal();
            syncButton();
        }

        function replaceIndex(group, from, to) {
            var pattern = new RegExp(options.prefix + "-" + from + "(?!\\d)", "g");
            var next = options.prefix + "-" + to;
            group.querySelectorAll("[name], [id], [for], [data-id]").forEach(function (el) {
                ["name", "id", "for", "data-id"].forEach(function (attr) {
                    var value = el.getAttribute(attr);
                    if (value && pattern.test(value)) {
                        pattern.lastIndex = 0;
                        el.setAttribute(attr, value.replace(pattern, next));
                    }
                    pattern.lastIndex = 0;
                });
            });
        }

        function remove(group) {
            var box = group.querySelector("input[name$='-DELETE']");
            if (box) {
                box.checked = !box.checked;
                paint(group);
                return;
            }
            var list = Array.prototype.slice.call(groups());
            var index = list.indexOf(group);
            if (index < 0) return;
            group.remove();
            list.slice(index + 1).forEach(function (later, offset) {
                replaceIndex(later, index + 1 + offset, index + offset);
            });
            totalInput().value = String(Math.max(0, list.length - 1));
            syncButton();
        }

        openBtn.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            openModal();
        });

        addBtn.addEventListener("click", confirmAdd);

        modal.querySelectorAll("[data-modal-cancel]").forEach(function (button) {
            button.addEventListener("click", function () {
                cancel();
            });
        });

        modal.addEventListener("keydown", function (event) {
            if (event.key === "Escape") {
                if (modal.querySelector(".select2-container--open")) return;
                event.preventDefault();
                event.stopPropagation();
                cancel();
            }
            if (event.key === "Enter" && event.target.tagName !== "TEXTAREA" && !event.target.classList.contains("select2-search__field")) {
                event.preventDefault();
                addBtn.click();
            }
        });

        groups().forEach(paint);
        var invalid = table.querySelector(":scope > .form-group:not(.empty-form) .errors, :scope > .form-group:not(.empty-form) .errorlist");
        if (invalid) openEditor(invalid.closest(".form-group"));
        syncButton();
    }

    document.querySelectorAll("[data-inline-modal]").forEach(boot);
})();

(function () {
    function optionsFor(kindSelect) {
        try {
            return JSON.parse(kindSelect.getAttribute("data-kind-reasons") || "{}");
        } catch (error) {
            return {};
        }
    }

    function fill(kindSelect) {
        var reasonSelect = document.getElementById("id_kind_reason");
        if (!reasonSelect) return;
        var current = reasonSelect.value;
        var choices = optionsFor(kindSelect)[kindSelect.value] || [];
        var stillThere = false;
        reasonSelect.replaceChildren();
        choices.forEach(function (pair) {
            var option = document.createElement("option");
            option.value = pair[0];
            option.textContent = pair[1];
            if (pair[0] === current) {
                option.selected = true;
                stillThere = true;
            }
            reasonSelect.appendChild(option);
        });
        if (!stillThere && choices.length) reasonSelect.selectedIndex = 0;
        reasonSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }

    function boot() {
        var kindSelect = document.getElementById("id_kind");
        if (!kindSelect || !kindSelect.hasAttribute("data-kind-reasons")) return;
        fill(kindSelect);
        kindSelect.addEventListener("change", function () {
            fill(kindSelect);
        });
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();

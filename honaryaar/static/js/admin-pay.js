(function () {
    function row(field) {
        if (!field) return null;
        return field.closest(".form-row") || field.closest("[class*='field-']") || field.parentElement;
    }

    function paint(root) {
        var paid = root.querySelector("[name$='paid']");
        var payType = root.querySelector("[name$='pay_type']");
        var payAmount = root.querySelector("[name$='pay_amount']");
        if (!paid || !payType || !payAmount) return;
        var typeRow = row(payType);
        var amountRow = row(payAmount);
        var showType = paid.checked;
        var showAmount = showType && payType.value === "fixed";
        if (typeRow) typeRow.hidden = !showType;
        if (amountRow) amountRow.hidden = !showAmount;
    }

    function boot(root) {
        var paid = root.querySelector("[name$='paid']");
        var payType = root.querySelector("[name$='pay_type']");
        if (!paid || !payType || paid.dataset.payBound) return;
        paid.dataset.payBound = "1";
        paid.addEventListener("change", function () { paint(root); });
        payType.addEventListener("change", function () { paint(root); });
        paint(root);
    }

    function start() {
        document.querySelectorAll("form").forEach(boot);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
    else start();
})();

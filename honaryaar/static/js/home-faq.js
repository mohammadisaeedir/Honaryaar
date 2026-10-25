(function () {
    var DURATION = 280;

    function reducedMotion() {
        return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    }

    function panelOf(item) {
        return item.querySelector(".new-home-faq__panel");
    }

    function clearTransition(panel) {
        panel.style.transition = "";
        panel.style.height = "";
        panel.style.overflow = "";
    }

    function animateHeight(panel, from, to, done) {
        panel.style.overflow = "hidden";
        panel.style.height = from + "px";
        panel.getBoundingClientRect();
        panel.style.transition = "height " + DURATION + "ms ease";
        panel.style.height = to + "px";
        var finished = false;
        function finish() {
            if (finished) return;
            finished = true;
            panel.removeEventListener("transitionend", onEnd);
            window.clearTimeout(fallback);
            if (done) done();
        }
        function onEnd(event) {
            if (event.target !== panel || event.propertyName !== "height") return;
            finish();
        }
        panel.addEventListener("transitionend", onEnd);
        var fallback = window.setTimeout(finish, DURATION + 80);
    }

    function openItem(item, instant) {
        var panel = panelOf(item);
        if (!panel) {
            item.open = true;
            return;
        }
        if (item.open && !item.classList.contains("is-animating")) return;
        item.classList.add("is-animating");
        item.open = true;
        if (instant || reducedMotion()) {
            clearTransition(panel);
            item.classList.remove("is-animating");
            return;
        }
        var target = panel.scrollHeight;
        animateHeight(panel, 0, target, function () {
            clearTransition(panel);
            item.classList.remove("is-animating");
        });
    }

    function closeItem(item, instant) {
        var panel = panelOf(item);
        if (!panel || !item.open) return;
        item.classList.add("is-animating");
        if (instant || reducedMotion()) {
            item.open = false;
            clearTransition(panel);
            item.classList.remove("is-animating");
            return;
        }
        var start = panel.scrollHeight;
        animateHeight(panel, start, 0, function () {
            item.open = false;
            clearTransition(panel);
            item.classList.remove("is-animating");
        });
    }

    function bind(root) {
        if (!root || root.dataset.faqBound === "1") return;
        root.dataset.faqBound = "1";
        var items = Array.prototype.slice.call(root.querySelectorAll("details.new-home-faq__item"));
        items.forEach(function (item) {
            var summary = item.querySelector("summary");
            var panel = panelOf(item);
            if (!summary || !panel) return;
            if (!item.open) {
                panel.style.height = "0px";
                panel.style.overflow = "hidden";
            }
            summary.addEventListener("click", function (event) {
                event.preventDefault();
                if (item.classList.contains("is-animating")) return;
                if (item.open) {
                    closeItem(item, false);
                    return;
                }
                items.forEach(function (other) {
                    if (other !== item && other.open) closeItem(other, false);
                });
                openItem(item, false);
            });
        });
    }

    function boot(scope) {
        (scope || document).querySelectorAll("[data-home-faq]").forEach(bind);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { boot(); });
    } else {
        boot();
    }
    window.bindHomeFaq = boot;
})();

(function () {
    function setup(root) {
        if (root.dataset.ready) return;
        root.dataset.ready = "1";

        var track = root.querySelector("[data-home-carousel-track]");
        var cards = track
            ? Array.prototype.filter.call(track.children, function (el) {
                  return !el.classList.contains("carousel-more");
              })
            : [];
        var prev = root.querySelector("[data-dir='-1']");
        var next = root.querySelector("[data-dir='1']");
        if (!track || !prev || !next || !cards.length) return;

        var index = 0;
        var perViewAttr = Number(root.getAttribute("data-per-view") || "3");

        function isNativeScroll() {
            return window.innerWidth < 768;
        }

        function perView() {
            if (isNativeScroll()) return 1;
            return Math.max(1, perViewAttr);
        }

        function step() {
            if (!cards.length) return 0;
            var gap = parseFloat(getComputedStyle(track).columnGap || getComputedStyle(track).gap) || 0;
            return cards[0].getBoundingClientRect().width + gap;
        }

        function go(value) {
            if (isNativeScroll()) {
                track.style.transform = "";
                return;
            }
            var max = Math.max(0, cards.length - perView());
            index = Math.max(0, Math.min(max, value));
            track.style.transform = "translateX(" + index * step() + "px)";
            prev.disabled = index === 0;
            next.disabled = index === max;
        }

        root.querySelectorAll("[data-dir]").forEach(function (button) {
            button.addEventListener("click", function () {
                go(index + Number(button.getAttribute("data-dir")));
            });
        });

        window.addEventListener("resize", function () {
            go(index);
        });
        go(0);
    }

    document.querySelectorAll("[data-home-carousel]").forEach(setup);
})();

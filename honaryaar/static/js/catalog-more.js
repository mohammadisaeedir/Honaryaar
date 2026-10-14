(function () {
    var grid = document.querySelector("[data-catalog-more]");
    if (!grid) return;
    var offset = Number(grid.getAttribute("data-offset")) || 0;
    var total = Number(grid.getAttribute("data-total")) || 0;
    if (offset >= total) return;

    var sentinel = document.createElement("div");
    sentinel.className = "catalog-more";
    sentinel.setAttribute("aria-hidden", "true");
    grid.after(sentinel);

    var busy = false;
    var armed = false;
    var watching = false;

    function columns() {
        var value = getComputedStyle(grid).gridTemplateColumns;
        if (!value || value === "none") return 1;
        var count = value.trim().split(/\s+/).length;
        return count > 0 ? count : 1;
    }

    function keepPlace(run) {
        var y = window.scrollY;
        run();
        if (window.scrollY !== y) window.scrollTo(0, y);
        window.requestAnimationFrame(function () {
            if (window.scrollY !== y) window.scrollTo(0, y);
        });
    }

    function cardHeight() {
        var cards = grid.querySelectorAll(":scope > article:not(.catalog-skel)");
        if (!cards.length) return 0;
        return Math.round(cards[cards.length - 1].getBoundingClientRect().height);
    }

    function skeletonRow(count) {
        var height = cardHeight();
        var artist = grid.classList.contains("artist-grid");
        var slots = [];
        keepPlace(function () {
            for (var i = 0; i < count; i += 1) {
                var card = document.createElement("article");
                card.className = artist ? "skel-card skel-card--tile catalog-skel" : "skel-card catalog-skel";
                card.setAttribute("aria-hidden", "true");
                if (height) card.style.height = height + "px";
                card.innerHTML = artist
                    ? '<span class="bone bone-photo"></span><span class="bone bone-md"></span><div class="skel-row"><span class="bone"></span><span class="bone"></span></div>'
                    : '<span class="bone bone-xs"></span><span class="bone bone-md"></span><span class="bone bone-line"></span><span class="bone bone-sm"></span>';
                grid.appendChild(card);
                slots.push(card);
            }
        });
        return slots;
    }

    function clearSlots(slots) {
        keepPlace(function () {
            slots.forEach(function (slot) { slot.remove(); });
        });
    }

    function load() {
        if (busy || offset >= total) return;
        busy = true;
        grid.setAttribute("aria-busy", "true");
        var count = columns();
        var slots = skeletonRow(count);
        var url = new URL(window.location.href);
        url.searchParams.set("offset", String(offset));
        url.searchParams.set("limit", String(count));
        fetch(url, { headers: { "X-Requested-With": "fetch" } })
            .then(function (response) {
                if (!response.ok) throw new Error("more");
                return response.text();
            })
            .then(function (html) {
                var fresh = [];
                if (html.trim()) {
                    var holder = document.createElement("template");
                    holder.innerHTML = html.trim();
                    fresh = Array.prototype.filter.call(holder.content.childNodes, function (node) {
                        return node.nodeType === 1;
                    });
                }
                keepPlace(function () {
                    slots.forEach(function (slot, index) {
                        if (fresh[index]) slot.replaceWith(fresh[index]);
                        else slot.remove();
                    });
                });
                offset += count;
                if (!fresh.length || offset >= total) {
                    offset = total;
                    sentinel.remove();
                }
            })
            .catch(function () {
                clearSlots(slots);
                offset = total;
                sentinel.remove();
            })
            .then(function () {
                busy = false;
                armed = false;
                grid.removeAttribute("aria-busy");
                if (offset < total) watch();
            });
    }

    var observer = new IntersectionObserver(function (entries) {
        observer.unobserve(sentinel);
        var reached = entries.some(function (entry) {
            if (entry.isIntersecting) return true;
            var top = entry.rootBounds ? entry.rootBounds.top : 0;
            return entry.boundingClientRect.bottom <= top;
        });
        if (reached) load();
        else {
            armed = false;
            watch();
        }
    }, { rootMargin: "0px 0px 280px 0px" });

    function arm() {
        if (armed || busy || offset >= total) return;
        watching = false;
        armed = true;
        window.removeEventListener("scroll", arm);
        window.removeEventListener("wheel", arm);
        window.removeEventListener("touchmove", arm);
        observer.observe(sentinel);
    }

    function watch() {
        if (watching || offset >= total) return;
        watching = true;
        window.addEventListener("scroll", arm, { passive: true });
        window.addEventListener("wheel", arm, { passive: true });
        window.addEventListener("touchmove", arm, { passive: true });
    }

    watch();
})();

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

    function load() {
        if (busy || offset >= total) return;
        busy = true;
        grid.setAttribute("aria-busy", "true");
        var count = columns();
        var url = new URL(window.location.href);
        url.searchParams.set("offset", String(offset));
        url.searchParams.set("limit", String(count));
        fetch(url, { headers: { "X-Requested-With": "fetch" } })
            .then(function (response) {
                if (!response.ok) throw new Error("more");
                return response.text();
            })
            .then(function (html) {
                if (html.trim()) grid.insertAdjacentHTML("beforeend", html);
                offset += count;
                if (!html.trim() || offset >= total) {
                    offset = total;
                    sentinel.remove();
                }
            })
            .catch(function () {
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
        if (entries.some(function (entry) { return entry.isIntersecting; })) load();
        else {
            armed = false;
            watch();
        }
    });

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

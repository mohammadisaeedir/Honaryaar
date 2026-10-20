(function () {
    function mount(el) {
        if (!el || el.dataset.lottieReady || !window.lottie) return null;
        el.dataset.lottieReady = "1";
        return window.lottie.loadAnimation({
            container: el,
            renderer: "svg",
            loop: true,
            autoplay: false,
            path: el.getAttribute("data-lottie"),
            rendererSettings: { preserveAspectRatio: "xMidYMid meet" },
        });
    }

    function whenIdle(fn) {
        if (typeof requestIdleCallback === "function") {
            requestIdleCallback(fn, { timeout: 1200 });
            return;
        }
        setTimeout(fn, 200);
    }

    function afterPaint(fn) {
        if (document.readyState === "complete") {
            whenIdle(fn);
            return;
        }
        window.addEventListener("load", function () {
            whenIdle(fn);
        });
    }

    function boot() {
        var talent = document.querySelector(".hero-lottie:not(.hero-lottie--hire)");
        var hire = document.querySelector(".hero-lottie--hire");
        var join = document.querySelector(".join-lottie");
        var talentAnim = null;
        var hireAnim = null;

        // Hero JSON is large — wait for load/idle so it does not fight the document.
        afterPaint(function () {
            talentAnim = mount(talent);
            if (talentAnim) talentAnim.play();
            if (hire && hire.classList.contains("is-on")) {
                hireAnim = mount(hire);
                if (hireAnim) {
                    if (talentAnim) talentAnim.pause();
                    hireAnim.play();
                }
            }
        });

        function showHire(on) {
            if (on && !hireAnim) hireAnim = mount(hire);
            if (on) {
                if (talentAnim) talentAnim.pause();
                if (hireAnim) hireAnim.play();
            } else {
                if (hireAnim) hireAnim.pause();
                if (talentAnim) talentAnim.play();
            }
        }

        if (hire) {
            new MutationObserver(function () {
                showHire(hire.classList.contains("is-on"));
            }).observe(hire, { attributes: true, attributeFilter: ["class"] });
        }

        if (!join) return;
        if (!("IntersectionObserver" in window)) {
            afterPaint(function () {
                var anim = mount(join);
                if (anim) anim.play();
            });
            return;
        }
        var observer = new IntersectionObserver(function (entries) {
            if (!entries.some(function (entry) { return entry.isIntersecting; })) return;
            var anim = mount(join);
            if (anim) anim.play();
            observer.disconnect();
        }, { rootMargin: "240px" });
        observer.observe(join);
    }

    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
    else boot();
})();

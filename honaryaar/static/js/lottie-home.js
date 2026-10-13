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

    function boot() {
        var talent = document.querySelector(".hero-lottie:not(.hero-lottie--hire)");
        var hire = document.querySelector(".hero-lottie--hire");
        var join = document.querySelector(".join-lottie");
        var talentAnim = mount(talent);
        var hireAnim = null;
        if (talentAnim) talentAnim.play();

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
            var anim = mount(join);
            if (anim) anim.play();
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

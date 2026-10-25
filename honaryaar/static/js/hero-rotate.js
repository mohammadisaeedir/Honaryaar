(function () {
    document.querySelectorAll(".hero-rotate").forEach(function (root) {
        var word = root.querySelector(".hero-word");
        var words = (root.getAttribute("data-words") || "").split("|").filter(Boolean);
        if (!word || words.length < 2) return;

        var index = 0;
        window.setInterval(function () {
            word.classList.add("is-changing");
            window.setTimeout(function () {
                index = (index + 1) % words.length;
                word.textContent = words[index];
                word.classList.remove("is-changing");
            }, 450);
        }, 2400);
    });
}());

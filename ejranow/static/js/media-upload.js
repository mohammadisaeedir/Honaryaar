(function () {
    var kinds = {
        photo: "image/jpeg,image/png,image/webp,image/gif",
        video: "video/mp4,video/webm,video/quicktime",
        audio: "audio/mpeg,audio/mp4,audio/wav,audio/ogg,audio/flac,audio/webm"
    };
    var labels = { photo: "عکس", video: "ویدیو", audio: "صوت" };

    function csrf(box) {
        var form = box.closest("form");
        var input = form && form.querySelector("[name=csrfmiddlewaretoken]");
        if (input) return input.value;
        var match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function kindOf(box) {
        if (box.dataset.fixedKind) return box.dataset.kind || "photo";
        var row = box.closest("tr");
        var select = row && row.querySelector("select");
        return (select && select.value) || box.dataset.kind || "photo";
    }

    function limitOf(box, kind) {
        return Number(box.dataset["max" + kind.charAt(0).toUpperCase() + kind.slice(1)] || box.dataset.maxPhoto || 0);
    }

    function showError(box, text) {
        var node = box.querySelector("[data-error]");
        node.hidden = !text;
        node.textContent = text || "";
    }

    function setBusy(box, busy) {
        if (busy) box.dataset.busy = "1";
        else delete box.dataset.busy;
    }

    function preview(box, kind, url) {
        var host = box.querySelector("[data-preview]");
        host.replaceChildren();
        if (!url) return;
        var node;
        if (kind === "video") {
            node = document.createElement("video");
            node.controls = true;
            node.playsInline = true;
            node.preload = "metadata";
            node.src = url;
        } else if (kind === "audio") {
            node = document.createElement("audio");
            node.controls = true;
            node.preload = "metadata";
            node.src = url;
        } else {
            node = document.createElement("img");
            node.alt = "";
            node.src = url;
        }
        host.appendChild(node);
    }

    function clearUpload(box) {
        box.querySelector("[data-upload-id]").value = "";
        delete box.dataset.uploadedKind;
    }

    async function requestJson(box, url, body) {
        var response = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf(box)
            },
            body: JSON.stringify(body || {})
        });
        var payload = {};
        try {
            payload = await response.json();
        } catch (error) {
            payload = {};
        }
        if (!response.ok) throw new Error(payload.error || "بارگذاری انجام نشد. دوباره تلاش کنید.");
        return payload;
    }

    function putFile(url, file, box) {
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open("PUT", url);
            xhr.setRequestHeader("Content-Type", "application/octet-stream");
            xhr.upload.onprogress = function (event) {
                if (!event.lengthComputable) return;
                var bar = box.querySelector("[data-bar]");
                var span = box.querySelector("[data-progress]");
                bar.hidden = false;
                span.style.width = Math.round((event.loaded / event.total) * 100) + "%";
            };
            xhr.onload = function () {
                if (xhr.status >= 200 && xhr.status < 300) resolve();
                else reject(new Error("بارگذاری انجام نشد. دوباره تلاش کنید."));
            };
            xhr.onerror = function () {
                reject(new Error("ارتباط با فضای ذخیره‌سازی قطع شد. دوباره تلاش کنید."));
            };
            xhr.send(file);
        });
    }

    async function upload(box, file) {
        var kind = kindOf(box);
        var limit = limitOf(box, kind);
        if (!file || !file.size) throw new Error("فایل خالی است.");
        if (limit && file.size > limit) throw new Error("حجم فایل بیش از حد مجاز است.");
        var ticket = await requestJson(box, box.dataset.start, {
            purpose: box.dataset.purpose,
            kind: kind,
            target_id: box.dataset.target ? Number(box.dataset.target) : null,
            size: file.size,
            replacing: box.dataset.replacing === "1"
        });
        await putFile(ticket.url, file, box);
        var done = await requestJson(box, box.dataset.start.replace(/\/$/, "") + "/" + ticket.id + "/complete/");
        box.querySelector("[data-upload-id]").value = done.id;
        box.dataset.uploadedKind = done.kind;
        preview(box, done.kind, done.thumb_url || done.preview_url);
        var row = box.closest("tr");
        var select = row && row.querySelector("select");
        if (select && done.kind) select.value = done.kind;
    }

    function bind(box) {
        if (box.dataset.ready) return;
        box.dataset.ready = "1";
        var input = box.querySelector("[data-file]");
        var select = box.closest("tr") && box.closest("tr").querySelector("select");
        function accept() {
            if (!box.dataset.fixedKind) input.accept = kinds[kindOf(box)] || "";
        }
        accept();
        if (select) {
            select.addEventListener("change", function () {
                accept();
                if (box.dataset.uploadedKind && box.dataset.uploadedKind !== kindOf(box)) {
                    clearUpload(box);
                    preview(box, "", "");
                    showError(box, "نوع عوض شد. فایل را دوباره انتخاب کنید.");
                }
            });
        }
        input.addEventListener("change", async function () {
            var file = input.files && input.files[0];
            input.value = "";
            if (!file) return;
            showError(box, "");
            setBusy(box, true);
            var last = "بارگذاری انجام نشد. دوباره تلاش کنید.";
            for (var attempt = 0; attempt < 2; attempt += 1) {
                try {
                    await upload(box, file);
                    last = "";
                    break;
                } catch (error) {
                    last = error.message || last;
                    clearUpload(box);
                }
            }
            setBusy(box, false);
            box.querySelector("[data-bar]").hidden = true;
            showError(box, last);
        });
    }

    function scan() {
        document.querySelectorAll("[data-media-upload]").forEach(bind);
    }

    document.addEventListener("DOMContentLoaded", scan);
    document.addEventListener("click", function () {
        window.setTimeout(scan, 0);
    });
    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form.querySelector) return;
        var busy = form.querySelector("[data-media-upload][data-busy]");
        if (busy) {
            event.preventDefault();
            showError(busy, "بارگذاری هنوز تمام نشده.");
            return;
        }
        var required = form.querySelector("[data-media-upload][data-require]");
        if (required && !required.querySelector("[data-upload-id]").value) {
            event.preventDefault();
            showError(required, "تصویر پروژه را بارگذاری کنید.");
        }
    }, true);
    scan();
})();

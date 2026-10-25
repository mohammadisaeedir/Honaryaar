(function () {
    var PERSIAN = "۰۱۲۳۴۵۶۷۸۹";
    var RESEND_SECONDS = 150;

    function toPersianDigits(value) {
        return String(value || "").replace(/\d/g, function (digit) {
            return PERSIAN[Number(digit)] || digit;
        });
    }

    function csrfToken() {
        var input = document.querySelector("#login-modal input[name=csrfmiddlewaretoken]");
        if (input && input.value) return input.value;
        var match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    function postForm(url, data) {
        var body = new FormData();
        Object.keys(data).forEach(function (key) {
            if (data[key] != null) body.append(key, data[key]);
        });
        return fetch(url, {
            method: "POST",
            body: body,
            credentials: "same-origin",
            headers: {
                "X-Requested-With": "fetch",
                "X-CSRFToken": csrfToken(),
                Accept: "application/json",
            },
        }).then(function (response) {
            return response.json().catch(function () {
                return {};
            }).then(function (payload) {
                payload._status = response.status;
                payload._ok = response.ok;
                return payload;
            });
        });
    }

    function loginUrl() {
        var form = document.querySelector('#login-modal form[action*="/login/"]');
        return form ? form.getAttribute("action") : "/login/";
    }

    function codeUrl() {
        var form = document.querySelector('#login-modal form[action*="code"]');
        return form ? form.getAttribute("action") : "/login/code/";
    }

    function loginModalData() {
        return {
            open: false,
            step: "phone",
            phone: "",
            phoneDisplay: "",
            next: "",
            error: "",
            busy: false,
            digits: ["", "", "", ""],
            timer: 0,
            timerId: null,
            openModal: function (detail) {
                detail = detail || {};
                this.open = true;
                this.error = "";
                this.busy = false;
                this.next = detail.next || this.next || "";
                if (detail.phone) {
                    this.phone = detail.phone;
                    this.phoneDisplay = detail.phoneDisplay || toPersianDigits(detail.phone);
                }
                this.step = detail.step === "otp" ? "otp" : "phone";
                if (this.step === "otp") {
                    this.digits = ["", "", "", ""];
                    this.startTimer();
                    var self = this;
                    this.$nextTick(function () {
                        var first = self.$root.querySelector("[data-otp-index='0']");
                        if (first) first.focus();
                    });
                } else {
                    this.stopTimer();
                    var selfPhone = this;
                    this.$nextTick(function () {
                        if (selfPhone.$refs.phoneInput) selfPhone.$refs.phoneInput.focus();
                    });
                }
            },
            closeModal: function () {
                this.open = false;
                this.error = "";
                this.busy = false;
                this.stopTimer();
            },
            backToPhone: function () {
                this.step = "phone";
                this.error = "";
                this.digits = ["", "", "", ""];
                this.stopTimer();
                var self = this;
                this.$nextTick(function () {
                    if (self.$refs.phoneInput) self.$refs.phoneInput.focus();
                });
            },
            codeValue: function () {
                return this.digits.join("");
            },
            codeReady: function () {
                return this.codeValue().length === 4;
            },
            timerLabel: function () {
                if (!this.timer) return "ارسال مجدد";
                var mins = Math.floor(this.timer / 60);
                var secs = this.timer % 60;
                var stamp = String(mins).padStart(2, "0") + ":" + String(secs).padStart(2, "0");
                return toPersianDigits(stamp) + " تا ارسال مجدد";
            },
            startTimer: function () {
                var self = this;
                this.stopTimer();
                this.timer = RESEND_SECONDS;
                this.timerId = window.setInterval(function () {
                    if (self.timer <= 1) {
                        self.timer = 0;
                        self.stopTimer();
                        return;
                    }
                    self.timer -= 1;
                }, 1000);
            },
            stopTimer: function () {
                if (this.timerId) {
                    window.clearInterval(this.timerId);
                    this.timerId = null;
                }
            },
            onDigitInput: function (event, index) {
                var raw = (event.target.value || "").replace(/\D/g, "");
                if (raw.length > 1) raw = raw.slice(-1);
                this.digits[index] = raw;
                event.target.value = raw;
                this.error = "";
                if (raw && index < 3) {
                    var next = this.$root.querySelector("[data-otp-index='" + (index + 1) + "']");
                    if (next) next.focus();
                }
            },
            onDigitKey: function (event, index) {
                if (event.key === "Backspace" && !event.target.value && index > 0) {
                    var prev = this.$root.querySelector("[data-otp-index='" + (index - 1) + "']");
                    if (prev) prev.focus();
                }
            },
            onDigitPaste: function (event) {
                var text = (event.clipboardData || window.clipboardData).getData("text") || "";
                var digits = text.replace(/\D/g, "").slice(0, 4).split("");
                for (var i = 0; i < 4; i += 1) this.digits[i] = digits[i] || "";
                var focusIndex = Math.min(digits.length, 3);
                var cell = this.$root.querySelector("[data-otp-index='" + focusIndex + "']");
                if (cell) cell.focus();
            },
            submitPhone: function () {
                var self = this;
                if (this.busy) return;
                this.busy = true;
                this.error = "";
                postForm(loginUrl(), { phone: this.phone, next: this.next }).then(function (payload) {
                    self.busy = false;
                    if (!payload._ok || !payload.ok) {
                        self.error = payload.error || "شماره موبایل را درست وارد کنید.";
                        return;
                    }
                    self.phone = payload.phone || self.phone;
                    self.phoneDisplay = payload.phone_display || toPersianDigits(self.phone);
                    self.digits = ["", "", "", ""];
                    self.step = "otp";
                    self.startTimer();
                    self.$nextTick(function () {
                        var first = self.$root.querySelector("[data-otp-index='0']");
                        if (first) first.focus();
                    });
                }).catch(function () {
                    self.busy = false;
                    self.error = "ارتباط برقرار نشد. دوباره تلاش کنید.";
                });
            },
            resendCode: function () {
                if (this.timer || this.busy) return;
                var self = this;
                this.busy = true;
                this.error = "";
                postForm(loginUrl(), { phone: this.phone, next: this.next }).then(function (payload) {
                    self.busy = false;
                    if (!payload._ok || !payload.ok) {
                        self.error = payload.error || "ارسال مجدد ممکن نشد.";
                        return;
                    }
                    self.phoneDisplay = payload.phone_display || toPersianDigits(self.phone);
                    self.digits = ["", "", "", ""];
                    self.startTimer();
                }).catch(function () {
                    self.busy = false;
                    self.error = "ارتباط برقرار نشد. دوباره تلاش کنید.";
                });
            },
            submitCode: function () {
                var self = this;
                if (this.busy || !this.codeReady()) return;
                this.busy = true;
                this.error = "";
                postForm(codeUrl(), { code: this.codeValue(), next: this.next }).then(function (payload) {
                    self.busy = false;
                    if (!payload._ok || !payload.ok) {
                        self.error = payload.error || "کد درست نیست.";
                        if (payload.step === "phone") self.backToPhone();
                        return;
                    }
                    self.closeModal();
                    window.location.assign(payload.redirect || self.next || "/");
                }).catch(function () {
                    self.busy = false;
                    self.error = "ارتباط برقرار نشد. دوباره تلاش کنید.";
                });
            },
        };
    }

    document.addEventListener("alpine:init", function () {
        Alpine.data("honarLoginModal", loginModalData);
    });

    function parseNextFromHref(href) {
        try {
            var url = new URL(href, location.origin);
            return url.searchParams.get("next") || "";
        } catch (error) {
            return "";
        }
    }

    var authQueryHandled = false;
    function openFromAuthQuery() {
        if (authQueryHandled) return;
        var params = new URLSearchParams(location.search);
        var auth = params.get("auth");
        if (!auth) return;
        authQueryHandled = true;
        var next = params.get("next") || "";
        var root = document.getElementById("login-modal");
        var phone = root ? root.getAttribute("data-session-phone") || "" : "";
        emitOpen({
            step: auth === "otp" ? "otp" : "phone",
            next: next,
            phone: phone,
            phoneDisplay: toPersianDigits(phone),
        });
        params.delete("auth");
        var clean = location.pathname + (params.toString() ? "?" + params.toString() : "") + location.hash;
        history.replaceState({}, "", clean);
    }

    function emitOpen(detail) {
        var event = new CustomEvent("honar-login-open", { detail: detail || {}, bubbles: true });
        window.dispatchEvent(event);
        // Fallback if Alpine window listener missed the first paint.
        var root = document.getElementById("login-modal");
        if (!root || !window.Alpine || typeof Alpine.$data !== "function") return;
        try {
            var data = Alpine.$data(root);
            if (data && typeof data.openModal === "function" && !data.open) {
                data.openModal(detail || {});
            }
        } catch (error) {}
    }

    document.addEventListener("click", function (event) {
        var link = event.target.closest && event.target.closest('a[href*="/login/"]');
        if (!link) return;
        var href = link.getAttribute("href") || "";
        if (/\/login\/code\/?/.test(href)) return;
        if (link.target === "_blank" || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        event.stopPropagation();
        emitOpen({ step: "phone", next: parseNextFromHref(link.href) });
    }, true);

    window.openHonarLogin = function (next, step) {
        emitOpen({ step: step || "phone", next: next || "" });
    };

    document.addEventListener("alpine:initialized", openFromAuthQuery);
})();

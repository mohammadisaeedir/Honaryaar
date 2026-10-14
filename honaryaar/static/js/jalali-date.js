(function () {
    if (window.__jalaliDate) return;
    window.__jalaliDate = true;

    var MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"];
    var WEEK = ["ش", "ی", "د", "س", "چ", "پ", "ج"];
    var PERSIAN = "۰۱۲۳۴۵۶۷۸۹";
    var active = null;
    var viewYear = 1400;
    var viewMonth = 1;
    var panel = null;

    function toPersian(number, width) {
        var text = String(number);
        while (text.length < width) text = "0" + text;
        return text.replace(/\d/g, function (digit) { return PERSIAN[digit]; });
    }

    function toAscii(text) {
        return String(text || "").replace(/[۰-۹٠-٩]/g, function (digit) {
            var persian = "۰۱۲۳۴۵۶۷۸۹".indexOf(digit);
            if (persian >= 0) return String(persian);
            return String("٠١٢٣٤٥٦٧٨٩".indexOf(digit));
        });
    }

    function toJalali(year, month, day) {
        var gregorianMonthLengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        var jalaliMonthLengths = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29];
        year -= 1600;
        month -= 1;
        day -= 1;
        var dayNumber = 365 * year + Math.floor((year + 3) / 4) - Math.floor((year + 99) / 100) + Math.floor((year + 399) / 400);
        for (var index = 0; index < month; index += 1) dayNumber += gregorianMonthLengths[index];
        var leap = (year + 1600) % 4 === 0 && ((year + 1600) % 100 !== 0 || (year + 1600) % 400 === 0);
        if (month > 1 && leap) dayNumber += 1;
        dayNumber += day - 79;
        var yearCycles = Math.floor(dayNumber / 12053);
        dayNumber %= 12053;
        var jalaliYear = 979 + 33 * yearCycles + 4 * Math.floor(dayNumber / 1461);
        dayNumber %= 1461;
        if (dayNumber >= 366) {
            jalaliYear += Math.floor((dayNumber - 1) / 365);
            dayNumber = (dayNumber - 1) % 365;
        }
        var lengths = jalaliMonthLengths.slice();
        if ([1, 5, 9, 13, 17, 22, 26, 30].indexOf(jalaliYear % 33) >= 0) lengths[11] = 30;
        for (var monthIndex = 0; monthIndex < lengths.length; monthIndex += 1) {
            if (dayNumber < lengths[monthIndex]) return { y: jalaliYear, m: monthIndex + 1, d: dayNumber + 1 };
            dayNumber -= lengths[monthIndex];
        }
        return { y: jalaliYear, m: 12, d: dayNumber + 1 };
    }

    function toGregorian(jalaliYear, jalaliMonth, jalaliDay) {
        var year = jalaliYear + 1595;
        var days = -355668 + (365 * year) + Math.floor(year / 33) * 8 + Math.floor(((year % 33) + 3) / 4) + jalaliDay;
        if (jalaliMonth < 7) days += (jalaliMonth - 1) * 31;
        else days += (jalaliMonth - 7) * 30 + 186;
        var gregorianYear = 400 * Math.floor(days / 146097);
        days %= 146097;
        if (days > 36524) {
            days -= 1;
            gregorianYear += 100 * Math.floor(days / 36524);
            days %= 36524;
            if (days >= 365) days += 1;
        }
        gregorianYear += 4 * Math.floor(days / 1461);
        days %= 1461;
        if (days > 365) {
            gregorianYear += Math.floor((days - 1) / 365);
            days = (days - 1) % 365;
        }
        var gregorianDay = days + 1;
        var leap = gregorianYear % 4 === 0 && (gregorianYear % 100 !== 0 || gregorianYear % 400 === 0);
        var monthLengths = [0, 31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
        var gregorianMonth = 1;
        while (gregorianMonth <= 12 && gregorianDay > monthLengths[gregorianMonth]) {
            gregorianDay -= monthLengths[gregorianMonth];
            gregorianMonth += 1;
        }
        return { y: gregorianYear, m: gregorianMonth, d: gregorianDay };
    }

    function monthLength(year, month) {
        if (month <= 6) return 31;
        if (month <= 11) return 30;
        var gregorian = toGregorian(year, 12, 30);
        var back = toJalali(gregorian.y, gregorian.m, gregorian.d);
        return back.y === year && back.m === 12 && back.d === 30 ? 30 : 29;
    }

    function display(parts) {
        return toPersian(parts.y, 4) + "/" + toPersian(parts.m, 2) + "/" + toPersian(parts.d, 2);
    }

    function iso(parts) {
        var gregorian = toGregorian(parts.y, parts.m, parts.d);
        var back = toJalali(gregorian.y, gregorian.m, gregorian.d);
        if (back.y !== parts.y || back.m !== parts.m || back.d !== parts.d) return "";
        return gregorian.y + "-" + String(gregorian.m).padStart(2, "0") + "-" + String(gregorian.d).padStart(2, "0");
    }

    function parse(text) {
        var parts = toAscii(text).trim().replace(/-/g, "/").replace(/\./g, "/").split("/").filter(Boolean);
        if (parts.length !== 3) return null;
        var year = Number(parts[0]);
        var month = Number(parts[1]);
        var day = Number(parts[2]);
        if (!year || month < 1 || month > 12 || day < 1 || day > 31) return null;
        if (year >= 1700) {
            var jalali = toJalali(year, month, day);
            return { y: jalali.y, m: jalali.m, d: jalali.d };
        }
        if (!iso({ y: year, m: month, d: day })) return null;
        return { y: year, m: month, d: day };
    }

    function sync(root) {
        var text = root.querySelector(".jalali-date__text");
        var hidden = root.querySelector("[data-jalali-value]");
        if (!text || !hidden) return;
        if (!text.value.trim()) {
            hidden.value = "";
            text.setCustomValidity("");
            return;
        }
        var parts = parse(text.value);
        if (!parts) {
            text.setCustomValidity("تاریخ را درست وارد کنید.");
            return;
        }
        text.setCustomValidity("");
        text.value = display(parts);
        hidden.value = iso(parts);
    }

    function ensurePanel() {
        if (panel) return panel;
        panel = document.createElement("div");
        panel.className = "jalali-panel";
        panel.hidden = true;
        panel.innerHTML = '<div class="jalali-panel__bar"><button class="jalali-panel__nav" type="button" data-nav="-1">›</button><div class="jalali-panel__title"></div><button class="jalali-panel__nav" type="button" data-nav="1">‹</button></div><div class="jalali-panel__week"></div><div class="jalali-panel__days"></div><div class="jalali-panel__foot"><button type="button" data-today>امروز</button><button type="button" data-clear>پاک کردن</button></div>';
        panel.querySelector(".jalali-panel__week").innerHTML = WEEK.map(function (day) { return "<span>" + day + "</span>"; }).join("");
        document.body.appendChild(panel);
        return panel;
    }

    function renderPanel() {
        var box = ensurePanel();
        var length = monthLength(viewYear, viewMonth);
        var first = toGregorian(viewYear, viewMonth, 1);
        var offset = (new Date(Date.UTC(first.y, first.m - 1, first.d)).getUTCDay() + 1) % 7;
        var selected = active ? parse(active.querySelector(".jalali-date__text").value) : null;
        box.querySelector(".jalali-panel__title").textContent = MONTHS[viewMonth - 1] + " " + toPersian(viewYear, 4);
        var html = "";
        for (var blank = 0; blank < offset; blank += 1) html += "<span></span>";
        for (var day = 1; day <= length; day += 1) {
            var on = selected && selected.y === viewYear && selected.m === viewMonth && selected.d === day;
            html += '<button type="button" data-day="' + day + '"' + (on ? ' class="is-on"' : "") + ">" + toPersian(day, 1) + "</button>";
        }
        box.querySelector(".jalali-panel__days").innerHTML = html;
    }

    function place(root) {
        var box = ensurePanel();
        var field = root.querySelector(".jalali-date__text");
        var rect = field.getBoundingClientRect();
        var width = 280;
        var left = rect.left;
        if (getComputedStyle(field).direction === "rtl") left = rect.right - width;
        left = Math.max(8, Math.min(left, window.innerWidth - width - 8));
        var top = rect.bottom + 6;
        if (top + 320 > window.innerHeight) top = Math.max(8, rect.top - 326);
        box.style.left = left + "px";
        box.style.top = top + "px";
    }

    function open(root) {
        active = root;
        var parts = parse(root.querySelector(".jalali-date__text").value);
        if (!parts) {
            var now = new Date();
            parts = toJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());
        }
        viewYear = parts.y;
        viewMonth = parts.m;
        ensurePanel().hidden = false;
        renderPanel();
        place(root);
    }

    function close() {
        if (panel) panel.hidden = true;
        active = null;
    }

    function choose(parts) {
        if (!active) return;
        active.querySelector(".jalali-date__text").value = display(parts);
        sync(active);
        close();
    }

    document.addEventListener("click", function (event) {
        var openButton = event.target.closest(".jalali-date__open");
        if (openButton) {
            event.preventDefault();
            var root = openButton.closest("[data-jalali-date]");
            if (active === root && panel && !panel.hidden) close();
            else open(root);
            return;
        }
        if (!panel || panel.hidden) return;
        if (event.target.closest(".jalali-panel")) return;
        if (!event.target.closest("[data-jalali-date]")) close();
    }, true);

    document.addEventListener("click", function (event) {
        if (!panel || panel.hidden || !event.target.closest(".jalali-panel")) return;
        var nav = event.target.closest("[data-nav]");
        if (nav) {
            viewMonth += Number(nav.getAttribute("data-nav"));
            if (viewMonth < 1) { viewMonth = 12; viewYear -= 1; }
            if (viewMonth > 12) { viewMonth = 1; viewYear += 1; }
            renderPanel();
            return;
        }
        var day = event.target.closest("[data-day]");
        if (day) {
            choose({ y: viewYear, m: viewMonth, d: Number(day.getAttribute("data-day")) });
            return;
        }
        if (event.target.closest("[data-today]")) {
            var now = new Date();
            choose(toJalali(now.getFullYear(), now.getMonth() + 1, now.getDate()));
            return;
        }
        if (event.target.closest("[data-clear]")) {
            if (!active) return;
            active.querySelector(".jalali-date__text").value = "";
            sync(active);
            close();
        }
    });

    document.addEventListener("change", function (event) {
        if (event.target.classList && event.target.classList.contains("jalali-date__text")) {
            sync(event.target.closest("[data-jalali-date]"));
        }
    });

    document.addEventListener("submit", function (event) {
        var form = event.target;
        if (!form.querySelectorAll) return;
        var invalid = false;
        form.querySelectorAll("[data-jalali-date]").forEach(function (root) {
            sync(root);
            var text = root.querySelector(".jalali-date__text");
            if (text && !text.checkValidity()) invalid = true;
        });
        if (invalid) {
            event.preventDefault();
            form.reportValidity();
        }
    }, true);

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") close();
    });
})();

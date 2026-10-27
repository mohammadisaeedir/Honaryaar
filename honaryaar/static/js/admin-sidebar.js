/**
 * Unfold treats width <= 1280 as "mobile sidebar", but Tailwind xl starts at
 * min-width: 1280px. At 1280 (common laptop width) the menu is forced closed
 * on load/resize while CSS already uses the desktop layout — so every click
 * that reloads or triggers a layout pass collapses the side menu.
 *
 * Align JS with Tailwind xl (>= 1280 = desktop) and only auto-close when the
 * viewport actually crosses down from desktop to overlay mode.
 */
(function () {
  var DESKTOP_MIN = 1280;

  function patch() {
    if (typeof window.theme !== "function" || window.theme._honaryaarSidebarPatch) {
      return typeof window.theme === "function";
    }

    var originalTheme = window.theme;

    function patchedTheme(defaultTheme) {
      var data = originalTheme(defaultTheme);
      var bindings = data.themeBindings || {};

      data._sidebarWasDesktop = window.innerWidth >= DESKTOP_MIN;

      data.sidebarOpen = function () {
        if (window.innerWidth < DESKTOP_MIN) {
          return false;
        }
        var stored = localStorage.getItem("sidebarOpen");
        if (stored === null) {
          return true;
        }
        return stored !== "0";
      };

      data.sidebarToggle = function () {
        this.sidebarOpen = !this.sidebarOpen;
        if (window.innerWidth >= DESKTOP_MIN) {
          localStorage.setItem("sidebarOpen", this.sidebarOpen ? "1" : "0");
        }
      };

      bindings["x-resize.window"] = function () {
        var desktop = window.innerWidth >= DESKTOP_MIN;
        if (desktop) {
          this.sidebarOpen =
            localStorage.getItem("sidebarOpen") === "0" ? false : true;
        } else if (this._sidebarWasDesktop) {
          // Crossed desktop → overlay: close once. Do not stomp while already
          // in overlay mode (layout shifts / ResizeObserver noise).
          this.sidebarOpen = false;
        }
        this._sidebarWasDesktop = desktop;
      };

      data.themeBindings = bindings;
      return data;
    }

    patchedTheme._honaryaarSidebarPatch = true;
    window.theme = patchedTheme;
    return true;
  }

  if (!patch()) {
    document.addEventListener("DOMContentLoaded", patch);
  }
})();

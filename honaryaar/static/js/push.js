(function () {
  var cfgRoot = window.HONARYAAR_PUSH || {};
  var cfg = cfgRoot.firebase || {};
  var endpoints = cfgRoot.endpoints || {};
  var csrf = cfgRoot.csrf || "";
  var lastToken = "";

  function isStandalone() {
    return (
      window.matchMedia("(display-mode: standalone)").matches ||
      window.navigator.standalone === true
    );
  }

  function supported() {
    return "Notification" in window && "serviceWorker" in navigator && "PushManager" in window;
  }

  function permission() {
    if (!("Notification" in window)) {
      return "unsupported";
    }
    return Notification.permission;
  }

  function getStatus() {
    return {
      mode: isStandalone() ? "pwa" : "browser",
      supported: supported(),
      permission: permission(),
      fcmConfigured: !!(cfgRoot.enabled && cfg.vapidKey && cfg.apiKey && cfg.projectId),
      tokenRegistered: !!lastToken,
    };
  }

  function postJson(url, body, method) {
    return fetch(url, {
      method: method || "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf,
      },
      body: JSON.stringify(body || {}),
    }).then(function (res) {
      return res.json().catch(function () {
        return { ok: false };
      });
    });
  }

  function loadFirebase() {
    if (window.firebase && window.firebase.messaging) {
      return Promise.resolve(window.firebase);
    }
    function inject(src) {
      return new Promise(function (resolve, reject) {
        var s = document.createElement("script");
        s.src = src;
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      });
    }
    return inject("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js").then(function () {
      return inject("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");
    }).then(function () {
      return window.firebase;
    });
  }

  function registerToken(token) {
    if (!token || !endpoints.devices) {
      return Promise.resolve({ ok: false });
    }
    lastToken = token;
    return postJson(endpoints.devices, { token: token, platform: isStandalone() ? "web" : "web" });
  }

  function boot() {
    if (!cfgRoot.enabled) {
      return Promise.reject(new Error("fcm_not_configured"));
    }
    if (!supported()) {
      return Promise.reject(new Error("unsupported"));
    }
    return loadFirebase()
      .then(function (firebase) {
        if (!firebase.apps.length) {
          firebase.initializeApp({
            apiKey: cfg.apiKey,
            authDomain: cfg.authDomain,
            projectId: cfg.projectId,
            messagingSenderId: cfg.messagingSenderId,
            appId: cfg.appId,
          });
        }
        return navigator.serviceWorker.ready.then(function (reg) {
          var messaging = firebase.messaging();
          return messaging
            .getToken({
              vapidKey: cfg.vapidKey,
              serviceWorkerRegistration: reg,
            })
            .then(function (token) {
              return registerToken(token).then(function () {
                return messaging;
              });
            });
        });
      })
      .then(function (messaging) {
        messaging.onMessage(function (payload) {
          var note = (payload && payload.notification) || {};
          var data = (payload && payload.data) || {};
          var title = note.title || data.title || "هنریار";
          var body = note.body || data.body || "";
          if (Notification.permission === "granted") {
            new Notification(title, { body: body, data: data });
          }
        });
        return getStatus();
      });
  }

  /**
   * Ask for permission (must run from a click/tap — browser + installed PWA).
   * Same Notification API covers desktop Chrome/Edge/Firefox and installed PWAs.
   * iOS only after Add to Home Screen (16.4+).
   */
  function enable() {
    if (!supported()) {
      return Promise.reject(new Error("unsupported"));
    }
    if (!cfgRoot.enabled) {
      return Promise.reject(new Error("fcm_not_configured"));
    }
    var ask =
      Notification.permission === "granted"
        ? Promise.resolve("granted")
        : Notification.requestPermission();
    return ask.then(function (state) {
      if (state !== "granted") {
        return getStatus();
      }
      return boot().catch(function () {
        return getStatus();
      });
    });
  }

  function syncIfGranted() {
    if (permission() === "granted" && cfgRoot.enabled) {
      return boot().catch(function () {
        return getStatus();
      });
    }
    return Promise.resolve(getStatus());
  }

  window.HonaryaarPush = {
    getStatus: getStatus,
    enable: enable,
    syncIfGranted: syncIfGranted,
    isStandalone: isStandalone,
  };

  // Never auto-prompt — browsers/PWA require a user gesture. Only refresh token if already allowed.
  function start() {
    syncIfGranted();
  }
  if (document.readyState === "complete") {
    setTimeout(start, 500);
  } else {
    window.addEventListener("load", function () {
      setTimeout(start, 500);
    });
  }
})();

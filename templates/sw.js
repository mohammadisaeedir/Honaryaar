/* Minimal PWA worker + optional FCM background handler. */
self.addEventListener("install", (event) => {
  event.waitUntil(self.skipWaiting());
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// Chrome installability requires a fetch listener. Do not call respondWith —
// the browser handles the network directly (no SW proxy delay).
self.addEventListener("fetch", () => {});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const data = event.notification.data || {};
  const target = data.deep_link || data.link || "/me/notifications/";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((list) => {
      for (const client of list) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(target);
      }
    })
  );
});

{% if fcm_enabled %}
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js");
firebase.initializeApp({
  apiKey: "{{ firebase.apiKey|escapejs }}",
  authDomain: "{{ firebase.authDomain|escapejs }}",
  projectId: "{{ firebase.projectId|escapejs }}",
  messagingSenderId: "{{ firebase.messagingSenderId|escapejs }}",
  appId: "{{ firebase.appId|escapejs }}",
});
firebase.messaging().onBackgroundMessage((payload) => {
  const note = (payload && payload.notification) || {};
  const data = (payload && payload.data) || {};
  const title = note.title || data.title || "هنریار";
  const options = {
    body: note.body || data.body || "",
    data: data,
  };
  return self.registration.showNotification(title, options);
});
{% endif %}

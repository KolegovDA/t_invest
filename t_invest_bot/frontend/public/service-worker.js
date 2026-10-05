// Service worker ESM Trade:
// принимает Web Push и показывает
// системные уведомления (в том
// числе на iOS 16.4+, когда PWA
// добавлена на главный экран).

self.addEventListener("install", () => {
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
    let payload = {
        title: "ESM Trade",
        body: "",
    };

    try {
        if (event.data) {
            payload = event.data.json();
        }
    } catch (error) {
        if (event.data) {
            payload.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(payload.title || "ESM Trade", {
            body: payload.body || "",
            icon: "/icons/icon-192.png",
            badge: "/icons/icon-192.png",
            tag: "esm-trade",
            renotify: true,
            data: {
                url: "/",
            },
        })
    );
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();

    event.waitUntil(
        self.clients
            .matchAll({
                type: "window",
                includeUncontrolled: true,
            })
            .then((clientList) => {
                for (const client of clientList) {
                    if ("focus" in client) {
                        return client.focus();
                    }
                }

                return self.clients.openWindow("/");
            })
    );
});

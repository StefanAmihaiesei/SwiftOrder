fetch("/settings").then(response => response.ok ? response.json() : Promise.reject())
    .then(settings => {
        document.querySelectorAll(".restaurant-brand h1").forEach(el => { el.textContent = settings.restaurant_name; });
        document.querySelectorAll(".restaurant-logo").forEach(el => { el.textContent = settings.restaurant_name.charAt(0).toUpperCase(); });
    }).catch(() => {});

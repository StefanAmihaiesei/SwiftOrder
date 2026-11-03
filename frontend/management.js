const managementSections = {
    tables: document.getElementById("tables-section"),
    staff: document.getElementById("staff-section")
};
const managementButtons = {
    tables: document.getElementById("show-tables"),
    staff: document.getElementById("show-staff")
};

function hideManagement() {
    for (const section of Object.values(managementSections)) section.hidden = true;
    for (const button of Object.values(managementButtons)) {
        button.classList.remove("selected");
        button.setAttribute("aria-pressed", "false");
    }
}
showOrdersButton.addEventListener("click", hideManagement);
showMenuButton.addEventListener("click", hideManagement);
for (const [name, button] of Object.entries(managementButtons)) {
    button.addEventListener("click", () => {
        if (currentStaff?.role !== "MANAGER" || leavingAdmin) return;
        hideManagement();
        ordersSection.hidden = true;
        menuManagementSection.hidden = true;
        for (const other of [showOrdersButton, showMenuButton]) {
            other.classList.remove("selected");
            other.setAttribute("aria-pressed", "false");
        }
        managementSections[name].hidden = false;
        button.classList.add("selected");
        button.setAttribute("aria-pressed", "true");
        loadManagement(name);
    });
}

async function managementRequest(url, options = {}) {
    const response = await fetch(url, options);
    if (response.status === 401) {
        redirectToLogin();
        throw new Error("Sesiunea a expirat.");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Verifică datele introduse.");
    return data;
}

async function loadManagement(name) {
    const list = document.getElementById("managed-" + name);
    const message = document.getElementById(name === "staff" ? "staff-message" : "tables-message");
    list.textContent = "Se încarcă...";
    try {
        const data = await managementRequest("/" + name);
        if (leavingAdmin) return;
        list.replaceChildren();
        if (!data.length) list.textContent = "Lista este goală.";
        for (const item of data) {
            const card = document.createElement("div");
            card.className = "product-card";
            const title = document.createElement("h3");
            title.textContent = name === "tables" ? "Masa " + item.number : item.username;
            card.append(title);
            if (name === "tables") {
                const preview = document.createElement("img");
                preview.src = "/tables/" + item.id + "/qr";
                preview.alt = "Cod QR pentru masa " + item.number;
                preview.width = 160;
                preview.height = 160;
                preview.className = "qr-preview";
                const link = document.createElement("a");
                link.href = item.menu_url;
                link.textContent = "Deschide meniul mesei";
                link.target = "_blank";
                link.rel = "noopener";
                const download = document.createElement("a");
                download.href = preview.src;
                download.download = "swiftorder-masa-" + item.number + ".svg";
                download.textContent = "Descarcă QR (SVG)";
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "danger-action";
                remove.textContent = "Șterge masa";
                remove.addEventListener("click", async () => {
                    if (!confirm("Ștergi masa " + item.number + "? QR-ul ei nu va mai funcționa.")) return;
                    remove.disabled = true;
                    try {
                        await managementRequest("/tables/" + item.id, {method: "DELETE"});
                        message.textContent = "Masa a fost ștearsă.";
                        await loadManagement(name);
                    } catch (error) { message.textContent = error.message; }
                    finally { remove.disabled = false; }
                });
                card.append(preview, link, download, remove);
            } else {
                const detail = document.createElement("p");
                detail.textContent = (item.role === "MANAGER" ? "Manager" : "Ospătar") + " · " + (item.is_active ? "Activ" : "Inactiv");
                card.append(detail);
                if (item.username !== currentStaff.username) {
                    const toggle = document.createElement("button");
                    toggle.type = "button";
                    toggle.textContent = item.is_active ? "Dezactivează contul" : "Reactivează contul";
                    toggle.addEventListener("click", async () => {
                        toggle.disabled = true;
                        try {
                            await managementRequest("/staff/" + item.id, {
                                method: "PATCH", headers: {"Content-Type": "application/json"},
                                body: JSON.stringify({is_active: !item.is_active})
                            });
                            message.textContent = "Contul a fost actualizat.";
                            await loadManagement(name);
                        } catch (error) { message.textContent = error.message; }
                        finally { toggle.disabled = false; }
                    });
                    card.append(toggle);
                }
            }
            list.append(card);
        }
    } catch (error) {
        list.textContent = "Lista nu a putut fi încărcată. Redeschide secțiunea pentru a reîncerca.";
        message.textContent = error.message;
    }
}

for (const name of ["table", "staff"]) {
    const form = document.getElementById(name + "-form");
    let saving = false;
    form.addEventListener("submit", async event => {
        event.preventDefault();
        if (saving || leavingAdmin || currentStaff?.role !== "MANAGER") return;
        const plural = name === "table" ? "tables" : "staff";
        const message = document.getElementById(plural + "-message");
        const data = name === "table" ? {number: Number(document.getElementById("table-number").value)} : {
            username: document.getElementById("staff-username").value.trim(),
            password: document.getElementById("staff-password").value,
            role: document.getElementById("staff-role").value
        };
        saving = true;
        const button = form.querySelector("button");
        button.disabled = true;
        try {
            await managementRequest("/" + plural, {
                method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(data)
            });
            form.reset();
            message.textContent = name === "table" ? "Masa a fost creată." : "Contul a fost creat.";
            await loadManagement(plural);
        } catch (error) { message.textContent = error.message; }
        finally { saving = false; button.disabled = false; }
    });
}

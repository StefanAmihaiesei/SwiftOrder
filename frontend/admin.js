const ordersContainer = document.getElementById("orders");
const historyCount = document.getElementById("history-count");
const loadMoreHistoryButton = document.getElementById("load-more-history");
const refreshStatus = document.getElementById("refresh-status");
const activeCount = document.getElementById("active-count");
const newCount = document.getElementById("new-count");
const preparingCount = document.getElementById("preparing-count");
const pendingStatusOrders = new Set();
const logoutButton = document.getElementById("logout-button");
const statusLabels = { NEW: "Nouă", PREPARING: "În preparare", DELIVERED: "Livrată" };
const priceFormatter = new Intl.NumberFormat("ro-RO", { style: "currency", currency: "RON" });
const historyPageSize = 10;
let historyLimit = historyPageSize;
let showHistory = false;
const staffInfo = document.getElementById("staff-info");
let currentStaff = null;
let latestRequestId = 0;
let leavingAdmin = false;
let isLoggingOut = false;
let refreshTimer;
const staffNavigation = document.getElementById("staff-navigation");
const ordersSection = document.getElementById("orders-section");
const menuManagementSection = document.getElementById("menu-management-section");
const showOrdersButton = document.getElementById("show-orders");
const showMenuButton = document.getElementById("show-menu-management");
const managedProducts = document.getElementById("managed-products");
const addProductButton = document.getElementById("add-product");
const menuMessage = document.getElementById("menu-message");
const productEditor = document.getElementById("product-editor");
const productForm = document.getElementById("product-form");
const productFields = document.getElementById("product-fields");
const productName = document.getElementById("product-name");
const productCategory = document.getElementById("product-category");
const productPrice = document.getElementById("product-price");
const productAvailable = document.getElementById("product-available");
const productEditorTitle = document.getElementById("product-editor-title");
const productDeleteWarning = document.getElementById("product-delete-warning");
const productFormMessage = document.getElementById("product-form-message");
const cancelProductButton = document.getElementById("cancel-product");
const saveProductButton = document.getElementById("save-product");
let productRequestId = 0;
let editedProductId = null;
let productEditorMode = "add";
let savingProduct = false;

function setProductMessage(element, message, isError = false) {
    element.textContent = message;
    element.hidden = !message;
    element.classList.toggle("message-error", isError);
}

function openProductEditor(product = null, mode = "edit") {
    if (currentStaff?.role !== "MANAGER" || leavingAdmin || isLoggingOut || savingProduct) {
        return;
    }
    productForm.reset();
    editedProductId = product?.id ?? null;
    productEditorMode = product ? mode : "add";
    const deleting = productEditorMode === "delete";
    productEditorTitle.textContent = deleting ? "Șterge produs" : product ? "Editează produs" : "Adaugă produs";
    productName.value = product?.name ?? "";
    const selectedCategory = product?.category ?? "Altele";
    if (![...productCategory.options].some(option => option.value === selectedCategory)) {
        const option = document.createElement("option");
        option.value = selectedCategory;
        option.textContent = selectedCategory;
        productCategory.append(option);
    }
    productCategory.value = product?.category ?? "Altele";
    productPrice.value = product?.price ?? "";
    productAvailable.checked = product ? product.available === 1 : true;
    productFields.hidden = deleting;
    productFields.disabled = deleting;
    productDeleteWarning.hidden = !deleting;
    productDeleteWarning.textContent = deleting
        ? "Ștergi „" + product.name + "”? Acțiunea este permanentă. Produsele folosite în comenzi trebuie marcate indisponibile."
        : "";
    saveProductButton.textContent = deleting ? "Șterge produs" : "Salvează";
    saveProductButton.classList.toggle("danger-action", deleting);
    saveProductButton.disabled = false;
    cancelProductButton.disabled = false;
    setProductMessage(productFormMessage, "");
    productEditor.showModal();
    document.body.classList.add("product-editor-open");
    (deleting ? cancelProductButton : productName).focus();
}

addProductButton.addEventListener("click", () => openProductEditor());
cancelProductButton.addEventListener("click", () => {
    if (!savingProduct) productEditor.close();
});
productEditor.addEventListener("cancel", event => {
    if (savingProduct) event.preventDefault();
});
productEditor.addEventListener("close", () => document.body.classList.remove("product-editor-open"));

productForm.addEventListener("submit", async function (event) {
    event.preventDefault();
    if (savingProduct || leavingAdmin || isLoggingOut || currentStaff?.role !== "MANAGER") return;
    const deleting = productEditorMode === "delete";
    let data;
    if (!deleting) {
        if (!productForm.reportValidity()) return;
        const name = productName.value.trim();
        const category = productCategory.value.trim();
        const price = Number(productPrice.value);
        if (!name || !category || !Number.isFinite(price) || price < 0) {
            setProductMessage(productFormMessage, "Completează numele, categoria și un preț valid.", true);
            return;
        }
        data = { name, category, price, available: productAvailable.checked ? 1 : 0 };
    }
    savingProduct = true;
    productFields.disabled = true;
    saveProductButton.disabled = true;
    cancelProductButton.disabled = true;
    setProductMessage(productFormMessage, deleting ? "Se șterge..." : "Se salvează...");
    try {
        const method = deleting ? "DELETE" : editedProductId === null ? "POST" : "PATCH";
        const url = editedProductId === null ? "/products" : "/products/" + editedProductId;
        const options = { method };
        if (data) {
            options.headers = { "Content-Type": "application/json" };
            options.body = JSON.stringify(data);
        }
        const response = await fetch(url, options);
        if (response.status === 401) {
            redirectToLogin();
            return;
        }
        if (!response.ok) {
            const result = await response.json().catch(() => ({}));
            const message = response.status === 403 ? "Acces permis doar managerului."
                : response.status === 404 ? "Produsul nu mai există. Închide formularul și redeschide lista."
                : typeof result.detail === "string" ? result.detail
                : "Datele nu au putut fi salvate. Verifică formularul și încearcă din nou.";
            setProductMessage(productFormMessage, message, true);
            return;
        }
        if (leavingAdmin) return;
        productEditor.close();
        setProductMessage(menuMessage, deleting ? "Produsul a fost șters." : "Produsul a fost salvat.");
        await loadManagedProducts();
    } catch (error) {
        if (!leavingAdmin) setProductMessage(productFormMessage, "Nu putem contacta serverul. Încearcă din nou.", true);
    } finally {
        savingProduct = false;
        productFields.disabled = deleting;
        saveProductButton.disabled = false;
        cancelProductButton.disabled = false;
    }
});

async function loadManagedProducts() {
    if (currentStaff?.role !== "MANAGER" || leavingAdmin || isLoggingOut) {
        return;
    }
    const requestId = ++productRequestId;
    managedProducts.textContent = "Se încarcă produsele...";
    try {
        const response = await fetch("/products");
        if (requestId !== productRequestId || leavingAdmin || isLoggingOut) return;
        if (!response.ok) {
            managedProducts.textContent = "Nu putem încărca produsele.";
            return;
        }
        const products = await response.json();
        if (requestId !== productRequestId || leavingAdmin || isLoggingOut) {
            return;
        }
        if (products.length === 0) {
            managedProducts.textContent = "Nu există produse.";
            return;
        }
        const fragment = document.createDocumentFragment();
        const categoryFragment = document.createDocumentFragment();
        for (const categoryName of [...new Set(["Altele", ...products.map(product => product.category)])].sort((a, b) => a.localeCompare(b, "ro"))) {
            const option = document.createElement("option");
            option.value = categoryName;
            option.textContent = categoryName;
            categoryFragment.append(option);
        }
        const previousCategory = productCategory.value;
        productCategory.replaceChildren(categoryFragment);
        productCategory.value = [...productCategory.options].some(option => option.value === previousCategory)
            ? previousCategory : "Altele";
        for (const product of products) {
            const card = document.createElement("div");
            card.className = "product-card";
            const name = document.createElement("h3");
            name.textContent = product.name;
            const category = document.createElement("p");
            category.textContent = product.category;
            const price = document.createElement("p");
            price.textContent = priceFormatter.format(product.price);
            const availability = document.createElement("p");
            availability.textContent = product.available === 1
                ? "Disponibil"
                : "Indisponibil";
            availability.className = product.available === 1 ? "product-stock" : "product-stock unavailable";
            price.className = "managed-product-price";
            const actions = document.createElement("div");
            actions.className = "managed-product-actions";
            const editButton = document.createElement("button");
            editButton.type = "button";
            editButton.textContent = "Editează";
            editButton.setAttribute("aria-label", "Editează " + product.name);
            editButton.addEventListener("click", () => openProductEditor(product));
            const deleteButton = document.createElement("button");
            deleteButton.type = "button";
            deleteButton.className = "danger-action";
            deleteButton.textContent = "Șterge";
            deleteButton.setAttribute("aria-label", "Șterge " + product.name);
            deleteButton.addEventListener("click", () => openProductEditor(product, "delete"));
            actions.append(editButton, deleteButton);
            card.append(name, category, price, availability, actions);
            fragment.append(card);
        }
        managedProducts.replaceChildren(fragment);
    } catch (error) {
        if (requestId === productRequestId && !leavingAdmin && !isLoggingOut) {
            managedProducts.textContent = "Verifică conexiunea la server.";
        }
    }
}

function selectAdminSection(showMenu) {
    if (showMenu && currentStaff?.role !== "MANAGER") {
        return;
    }

    ordersSection.hidden = showMenu;
    menuManagementSection.hidden = !showMenu;

    showOrdersButton.classList.toggle("selected", !showMenu);
    showMenuButton.classList.toggle("selected", showMenu);

    showOrdersButton.setAttribute("aria-pressed", String(!showMenu));
    showMenuButton.setAttribute("aria-pressed", String(showMenu));
    if (showMenu) {
        loadManagedProducts();
    }
}

showOrdersButton.addEventListener("click", function () {
    selectAdminSection(false);
});

showMenuButton.addEventListener("click", function () {
    selectAdminSection(true);
});

function redirectToLogin() {
    if (leavingAdmin) {
        return;
    }
    leavingAdmin = true;
    latestRequestId++;
    productRequestId++;
    if (productEditor.open) productEditor.close();
    managedProducts.replaceChildren();
    clearTimeout(refreshTimer);
    ordersContainer.replaceChildren();
    window.location.replace("/login");
}

logoutButton.addEventListener("click", async function () {
    if (isLoggingOut || leavingAdmin) {
        return;
    }
    isLoggingOut = true;
    latestRequestId++;
    logoutButton.disabled = true;
    try {
        const response = await fetch("/auth/logout", { method: "POST" });
        if (!response.ok && response.status !== 401) {
            alert("Deconectarea nu a reușit. Încearcă din nou.");
            return;
        }
        redirectToLogin();
    } catch (error) {
        alert("Nu putem contacta serverul. Încearcă din nou.");
    } finally {
        isLoggingOut = false;
        logoutButton.disabled = leavingAdmin;
    }
});

document.getElementById("show-active").addEventListener("click", function () {
    showHistory = false;
    loadOrders();
});

document.getElementById("show-history").addEventListener("click", function () {
    if (!showHistory) {
        historyLimit = historyPageSize;
    }
    showHistory = true;
    loadOrders();
});

loadMoreHistoryButton.addEventListener("click", function () {
    historyLimit += historyPageSize;
    loadOrders();
});

async function loadOrders() {
    if (leavingAdmin || isLoggingOut) {
        return;
    }
    const requestId = ++latestRequestId;
    const historyView = showHistory;
    const visibleHistoryLimit = historyLimit;

    document.getElementById("show-active").classList.toggle("selected", !historyView);
    document.getElementById("show-history").classList.toggle("selected", historyView);
    document.getElementById("show-active").setAttribute("aria-pressed", !historyView);
    document.getElementById("show-history").setAttribute("aria-pressed", historyView);
    if (!historyView) {
        historyCount.hidden = true;
        loadMoreHistoryButton.hidden = true;
    }

    let allOrders;
    try {
        const response = await fetch("/orders");
        if (requestId !== latestRequestId) {
            return;
        }
        if (response.status === 401) {
            redirectToLogin();
            return;
        }
        if (!response.ok) {
            refreshStatus.textContent = "Actualizarea a eșuat";
            refreshStatus.classList.add("refresh-error");
            historyCount.hidden = true;
            loadMoreHistoryButton.hidden = true;
            ordersContainer.textContent = "Nu am putut încărca comenzile.";
            return;
        }
        allOrders = await response.json();
    } catch (error) {
        if (requestId === latestRequestId) {
            console.error(error);
            refreshStatus.textContent = "Conexiune întreruptă";
            refreshStatus.classList.add("refresh-error");
            historyCount.hidden = true;
            loadMoreHistoryButton.hidden = true;
            ordersContainer.textContent = "Nu am putut încărca comenzile. Verifică conexiunea.";
        }
        return;
    }

    if (requestId !== latestRequestId) {
        return;
    }

    newCount.textContent = allOrders.filter(order => order.status === "NEW").length;
    preparingCount.textContent = allOrders.filter(order => order.status === "PREPARING").length;
    activeCount.textContent = allOrders.filter(order => order.status !== "DELIVERED").length;
    refreshStatus.textContent = "Actualizat la " + new Date().toLocaleTimeString("ro-RO", { hour: "2-digit", minute: "2-digit" });
    refreshStatus.classList.remove("refresh-error");

    const orders = allOrders.filter(function (order) {
        return historyView
            ? order.status === "DELIVERED"
            : order.status !== "DELIVERED";
    });
    if (historyView) {
        orders.reverse();
    }
    const visibleOrders = historyView ? orders.slice(0, visibleHistoryLimit) : orders;
    const fragment = document.createDocumentFragment();

    if (orders.length === 0) {
        historyCount.hidden = true;
        loadMoreHistoryButton.hidden = true;
        const emptyMessage = document.createElement("p");
        emptyMessage.className = "orders-empty";
        emptyMessage.textContent = historyView
            ? "Nu există comenzi livrate."
            : "Toate mesele sunt la zi. Comenzile noi vor apărea aici.";
        ordersContainer.replaceChildren(emptyMessage);
        return;
    }

    for (const order of visibleOrders) {
        const card = document.createElement("div");
        card.className = "order-card";
        const heading = document.createElement("div");
        heading.className = "order-card-heading";
        const title = document.createElement("div");
        const table = document.createElement("h3");
        table.textContent = "Masa " + order.table_number;
        const orderNumber = document.createElement("span");
        orderNumber.className = "order-number";
        orderNumber.textContent = "Comanda #" + order.order_id;
        title.append(table, orderNumber);
        const status = document.createElement("span");
        status.className = "order-status status-" + order.status.toLowerCase();
        status.textContent = statusLabels[order.status] || order.status;
        heading.append(title, status);
        card.append(heading);
        const dateLine = document.createElement("p");
        dateLine.className = "order-date";
        const timestamp = /Z$|[+-]\d{2}:\d{2}$/i.test(order.created_at)
            ? order.created_at : order.created_at + "Z";
        const orderDate = new Date(timestamp);

        dateLine.textContent = "Plasată: " + orderDate.toLocaleString("ro-RO", {
            day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit"
        });
        card.append(dateLine);
        fragment.append(card);
        const products = document.createElement("ul");
        products.className = "order-products";
        for (const product of order.items) {
            const productLine = document.createElement("li");
            const quantity = document.createElement("span");
            quantity.className = "order-quantity";
            quantity.textContent = product.quantity + "×";
            const name = document.createElement("span");
            name.textContent = product.name;
            productLine.append(quantity, name);
            products.append(productLine);
        }
        card.append(products);

        const footer = document.createElement("div");
        footer.className = "order-footer";
        const totalLine = document.createElement("p");
        totalLine.className = "order-total";
        const totalLabel = document.createElement("span");
        totalLabel.textContent = "Total";
        const totalValue = document.createElement("strong");
        totalValue.textContent = priceFormatter.format(order.total);
        totalLine.append(totalLabel, totalValue);
        footer.append(totalLine);
        card.append(footer);

        if (order.status === "NEW" || order.status === "PREPARING") {
            const statusButton = document.createElement("button");
            statusButton.className = "order-action";
            statusButton.disabled = pendingStatusOrders.has(order.order_id);
            const nextStatus = order.status === "NEW" ? "PREPARING" : "DELIVERED";

            statusButton.textContent = order.status === "NEW"
                ? "Începe prepararea"
                : "Marchează livrată";

            statusButton.addEventListener("click", async function () {
                statusButton.disabled = true;

                try {
                    await changeOrderStatus(order.order_id, nextStatus);
                } finally {
                    statusButton.disabled = false;
                }
            });

            footer.append(statusButton);
        }
    }
    if (requestId !== latestRequestId) {
        return;
    }

    const scrollPosition = window.scrollY;
    ordersContainer.replaceChildren(fragment);
    if (historyView) {
        historyCount.textContent = "Afișate " + visibleOrders.length + " din " + orders.length + " comenzi livrate.";
        historyCount.hidden = false;
        loadMoreHistoryButton.hidden = visibleOrders.length >= orders.length;
    }
    window.scrollTo(0, scrollPosition);
}

async function changeOrderStatus(orderId, newStatus) {
    if (leavingAdmin || isLoggingOut || pendingStatusOrders.has(orderId)) {
        return;
    }
    pendingStatusOrders.add(orderId);
    try {
        const response = await fetch("/orders/" + orderId + "/status", {
            method: "PATCH",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.status === 401) {
            redirectToLogin();
            return;
        }
        if (!response.ok) {
            alert("Nu am putut schimba statusul comenzii.");
            return;
        }

    } catch (error) {
        console.error(error);
        alert("Verifică conexiunea la server.");
    } finally {
        pendingStatusOrders.delete(orderId);
        await loadOrders();
    }
}

async function refreshOrders() {
    try {
        await loadOrders();
    } catch (error) {
        console.error(error);
    } finally {
        if (!leavingAdmin) {
            refreshTimer = setTimeout(refreshOrders, 5000);
        }
    }
}


async function loadStaff() {
    try {
        const response = await fetch("/auth/me");
        if (response.status === 401) {
            redirectToLogin();
            return false;
        }
        if (!response.ok) {
            staffInfo.textContent = "Nu putem verifica utilizatorul.";
            return false;
        }
        const user = await response.json();
        if (leavingAdmin || isLoggingOut) {
            return false;
        }
        currentStaff = user;
        staffNavigation.hidden = user.role !== "MANAGER";
        const roleLabel = user.role === "MANAGER"
            ? "Manager"
            : "Ospătar";
        staffInfo.textContent = user.username + " · " + roleLabel;
        return true;
    } catch (error) {
        staffInfo.textContent = "Conexiune întreruptă.";
        return false;
    }
}

async function initAdmin() {
    if (await loadStaff()) {
        refreshOrders();
    }
}


initAdmin();

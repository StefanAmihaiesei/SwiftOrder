const params = new URLSearchParams(window.location.search);
const qrToken = params.get("token");
let isSubmitting = false;
let tableIsValid = false;
const cart = [];
const storageKey = "swiftorder-cart:" + (qrToken || "preview");
const orderMessage = document.getElementById("order-message");
const searchInput = document.getElementById("menu-search");
let pendingOrder = null;

function saveCart() {
    try {
        localStorage.setItem(storageKey, JSON.stringify({items: cart, pendingOrder}));
    } catch (_) { /* Ordering still works when browser storage is unavailable. */ }
}

function restoreCart() {
    try {
        const saved = JSON.parse(localStorage.getItem(storageKey) || "null");
        if (!saved || !Array.isArray(saved.items) || !tableIsValid) return;
        for (const item of saved.items.slice(0, 100)) {
            const product = products.find(product => product.id === item.id && product.available === 1);
            if (product && Number.isInteger(item.quantity) && item.quantity > 0 && item.quantity <= 99) {
                cart.push({...product, quantity: item.quantity});
            }
        }
        if (saved.pendingOrder && typeof saved.pendingOrder.key === "string" && saved.pendingOrder.data?.qr_token === qrToken) {
            pendingOrder = saved.pendingOrder;
            orderMessage.textContent = "O comandă așteaptă confirmare. Apasă Plasează comanda pentru a verifica fără dublare.";
        }
    } catch (_) { /* Ignore stale or malformed browser storage. */ }
    renderCart();
}

searchInput.addEventListener("input", renderProducts);
let products = [];
const productsContainer = document.getElementById("products");
const cartSection = document.getElementById("cart-section");
const cartContainer = document.getElementById("cart");
const placeOrderButton = document.getElementById("place-order");
const categoriesContainer = document.getElementById("categories");
const categoryTitle = document.getElementById("category-title");
const foodButton = document.getElementById("show-food");
const drinksButton = document.getElementById("show-drinks");
const cartDesktopSlot = document.getElementById("cart-desktop-slot");
const cartDialog = document.getElementById("cart-dialog");
const openCartButton = document.getElementById("open-cart");
const closeCartButton = document.getElementById("close-cart");
const cartCount = document.getElementById("cart-count");
const cartButtonTotal = document.getElementById("cart-button-total");
const cartTotal = document.getElementById("cart-total");
const mobileView = window.matchMedia("(max-width: 700px)");
const priceFormatter = new Intl.NumberFormat("ro-RO", {
    style: "currency",
    currency: "RON"
});

function updateCartLayout() {
    if (mobileView.matches) {
        cartDialog.append(cartSection);
    } else {
        if (cartDialog.open) {
            cartDialog.close();
        }
        cartDesktopSlot.append(cartSection);
    }
    renderCart();
}

openCartButton.addEventListener("click", function () {
    if (tableIsValid && mobileView.matches && !cartDialog.open) {
        cartDialog.showModal();
        document.body.classList.add("cart-open");
        closeCartButton.focus();
    }
});

closeCartButton.addEventListener("click", function () {
    cartDialog.close();
});

cartDialog.addEventListener("close", function () {
    document.body.classList.remove("cart-open");
});

cartDialog.addEventListener("click", function (event) {
    if (event.target === cartDialog) {
        cartDialog.close();
    }
});

mobileView.addEventListener("change", updateCartLayout);

const defaultGroups = {
    food: [
        "Pizza", "Burgeri", "Paste", "Salate",
        "Garnituri", "Patiserie", "Deserturi"
    ],
    drinks: [
        "Băuturi calde", "Băuturi reci", "Băuturi alcoolice"
    ]
};

const menuGroups = {food: [], drinks: []};
let selectedGroup = "food";
let selectedCategory = "";

function updateGroups() {
    const categories = [...new Set(products.map(product => product.category))];
    menuGroups.drinks = categories.filter(category => defaultGroups.drinks.includes(category));
    menuGroups.food = categories.filter(category => !menuGroups.drinks.includes(category));
    foodButton.hidden = menuGroups.food.length === 0;
    drinksButton.hidden = menuGroups.drinks.length === 0;
    if (!menuGroups[selectedGroup].length) selectedGroup = menuGroups.food.length ? "food" : "drinks";
    if (!menuGroups[selectedGroup].includes(selectedCategory)) selectedCategory = menuGroups[selectedGroup][0] || "";
}

function selectGroup(group) {
    selectedGroup = group;
    selectedCategory = menuGroups[group][0];
    renderCategories();
    renderProducts();
}
foodButton.addEventListener("click", function () {
    selectGroup("food");
});
drinksButton.addEventListener("click", function () {
    selectGroup("drinks");
});


async function loadProducts() {
    try {
        const response = await fetch("/products");
        if (!response.ok) {
            productsContainer.textContent = "Nu am putut încărca meniul. Reîncarcă pagina.";
            return;
        }
        products = await response.json();
        updateGroups();
        renderCategories();
        renderProducts();
    } catch (error) {
        console.error(error);
        productsContainer.textContent = "Nu am putut încărca meniul. Reîncarcă pagina.";
    }
}


function renderCategories() {
    const hadCategoryFocus = categoriesContainer.contains(document.activeElement);
    foodButton.classList.toggle("selected", selectedGroup === "food");
    drinksButton.classList.toggle("selected", selectedGroup === "drinks");
    foodButton.setAttribute("aria-pressed", selectedGroup === "food");
    drinksButton.setAttribute("aria-pressed", selectedGroup === "drinks");
    categoriesContainer.replaceChildren();
    const categories = menuGroups[selectedGroup];
    for (const category of categories) {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = category;
        button.classList.toggle("selected", category === selectedCategory);
        button.setAttribute("aria-pressed", category === selectedCategory);
        button.addEventListener("click", function () {
            selectedCategory = category;
            renderCategories();
            renderProducts();
        });

        categoriesContainer.append(button);
    }
    const selectedButton = categoriesContainer.querySelector(".selected");
    if (selectedButton) {
        // Keep the active category visible without scrolling the page vertically.
        categoriesContainer.scrollLeft = mobileView.matches ? Math.max(0, selectedButton.offsetLeft - 8) : 0;
        if (hadCategoryFocus) {
            selectedButton.focus({ preventScroll: true });
        }
    }
}


function renderProducts() {
    categoryTitle.textContent = searchInput.value.trim() ? "Rezultatele căutării" : selectedCategory || "Meniu";
    productsContainer.replaceChildren();

    const search = searchInput.value.trim().toLocaleLowerCase("ro");
    for (const product of products) {
        if (search ? !product.name.toLocaleLowerCase("ro").includes(search) : product.category !== selectedCategory) {
            continue;
        }
        const card = document.createElement("div");
        card.className = "product-card";
        card.classList.toggle("is-unavailable", product.available !== 1);
        const addButton = document.createElement("button");
        const name = document.createElement("h3");
        const price = document.createElement("p");
        const availability = document.createElement("p");
        price.className = "product-price";
        price.textContent = priceFormatter.format(product.price);
        name.textContent = product.name;
        availability.className = "product-availability";
        if (product.available !== 1) {
            availability.textContent = "Indisponibil";
        }
        availability.hidden = product.available === 1;
        addButton.className = "product-add";
        addButton.dataset.available = product.available;
        const addLabel = document.createElement("span");
        addLabel.textContent = "Adaugă";
        addButton.append(addLabel);
        addButton.hidden = !tableIsValid;
        addButton.disabled = product.available !== 1 || isSubmitting;
        addButton.setAttribute("aria-label", "Adaugă " + product.name + " în coș");
        addButton.addEventListener("click", function () {
            addToCart(product);

        });
        card.append(name, price, availability, addButton);
        productsContainer.append(card);
    }
    if (!productsContainer.children.length) productsContainer.textContent = "Nu există produse în această selecție.";
}


function renderCart() {
    saveCart();
    document.querySelector("main").classList.toggle("ordering-enabled", tableIsValid);
    cartSection.hidden = !tableIsValid;
    cartDesktopSlot.hidden = !tableIsValid || mobileView.matches;
    openCartButton.hidden = !tableIsValid || !mobileView.matches;
    if (!tableIsValid && cartDialog.open) {
        cartDialog.close();
    }
    const total = cart.reduce((sum, product) => sum + product.price * product.quantity, 0);
    const quantity = cart.reduce((sum, product) => sum + product.quantity, 0);
    cartCount.textContent = quantity;
    cartTotal.textContent = priceFormatter.format(total);
    cartButtonTotal.textContent = priceFormatter.format(total);
    openCartButton.setAttribute("aria-label", "Deschide coșul: " + quantity + " produse, total " + priceFormatter.format(total));
    const focusedProductId = document.activeElement.dataset.productId;
    cartContainer.replaceChildren();
    placeOrderButton.disabled = (cart.length === 0 && !pendingOrder) || isSubmitting || !tableIsValid;
    placeOrderButton.textContent = isSubmitting ? "Se trimite comanda..." : "Plasează comanda";
    document.querySelectorAll(".product-add").forEach(function (button) {
        button.disabled = button.dataset.available !== "1" || isSubmitting || Boolean(pendingOrder);
    });
    if (cart.length === 0) {
        const emptyMessage = document.createElement("p");
        emptyMessage.className = "cart-empty";
        emptyMessage.textContent = "Coșul este gol. Alege ceva bun din meniu.";
        cartContainer.append(emptyMessage);
        if (focusedProductId && cartDialog.open) {
            closeCartButton.focus();
        }
        return;
    }

    for (const product of cart) {
        const item = document.createElement("div");
        item.className = "cart-item";
        const details = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = product.name;
        const linePrice = document.createElement("p");
        linePrice.textContent = product.quantity + " × " + priceFormatter.format(product.price);
        details.append(name, linePrice);
        const controls = document.createElement("div");
        controls.className = "cart-item-controls";
        const subtotal = document.createElement("strong");
        subtotal.textContent = priceFormatter.format(product.price * product.quantity);
        const decreaseButton = document.createElement("button");
        decreaseButton.className = "quantity-button";
        decreaseButton.textContent = "−";
        decreaseButton.disabled = isSubmitting || Boolean(pendingOrder);
        decreaseButton.dataset.productId = product.id;
        decreaseButton.setAttribute("aria-label", "Scade cantitatea pentru " + product.name);

        decreaseButton.addEventListener("click", function () {
            decreaseQuantity(product.id);
        });

        controls.append(subtotal, decreaseButton);
        item.append(details, controls);
        cartContainer.append(item);
    }
    if (focusedProductId) {
        const buttons = Array.from(cartContainer.querySelectorAll(".quantity-button"));
        const nextFocus = buttons.find(button => button.dataset.productId === focusedProductId) || buttons[0];
        if (nextFocus && !nextFocus.disabled) {
            nextFocus.focus({ preventScroll: true });
        }
    }
}


function addToCart(product){
    if (isSubmitting || pendingOrder || !tableIsValid || product.available !== 1) {
        return;
    }
    const existingItem = cart.find(function (item) {
        return item.id === product.id;
    });
    if (existingItem){
        if (existingItem.quantity >= 99) return;
        existingItem.quantity +=1;
    } else{
        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            quantity: 1
        });
    }
    renderCart();
}

function decreaseQuantity(productId) {
    if (isSubmitting || pendingOrder) {
        return;
    }
    const index = cart.findIndex(function (item) {
        return item.id === productId;
    });

    if (index === -1) {
        return;
    }

    if (cart[index].quantity > 1) {
        cart[index].quantity -= 1;
    } else {
        cart.splice(index, 1);
    }

    renderCart();
}






async function loadTable(){
    const tableInfo = document.getElementById("table-info");

    if (!qrToken){
        tableInfo.textContent = " Scanează codul QR pentru a comanda !"
        return;
    }
    try {
        const response = await fetch("/tables/by-token/" + encodeURIComponent(qrToken));
        if (!response.ok) {
            tableInfo.textContent = "Masa nu a fost găsită. Scanează din nou QR-ul.";
            return;
        }
        const table = await response.json();
        tableInfo.textContent = "Masa " + table.number;
        tableIsValid = true;
    } catch (error) {
        console.error(error);
        tableInfo.textContent = "Nu am putut verifica masa. Reîncarcă pagina.";
        tableIsValid = false;
        renderCart();
    }
}


async function placeOrder() {
    if (isSubmitting || (cart.length === 0 && !pendingOrder) || !tableIsValid){
        return;
    }
    isSubmitting = true;
    renderCart();
    try {
        const orderData = pendingOrder?.data || {
            qr_token: qrToken,
            items: cart.map(function (product) {
                return {
                    product_id: product.id,
                    quantity: product.quantity
                };
            })
        };

        if (!pendingOrder) {
            pendingOrder = {key: Array.from(crypto.getRandomValues(new Uint8Array(24)), b => b.toString(16).padStart(2, "0")).join(""), data: orderData};
            saveCart();
        }
        const response = await fetch("/orders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Idempotency-Key": pendingOrder.key
            },
            body: JSON.stringify(orderData)
        });

        const result = await response.json();

        if (!response.ok){
            if (response.status < 500) pendingOrder = null;
            orderMessage.textContent = typeof result.detail === "string" ? result.detail : "Comanda nu a fost trimisă. Verifică meniul și încearcă din nou.";
            return;
        }
        orderMessage.textContent = "Comanda #" + result.order_id + " a fost plasată! Total: " + priceFormatter.format(result.total) + ". Personalul o va prelua în curând.";
        pendingOrder = null;
        if (cartDialog.open) cartDialog.close();

        cart.length = 0;
        renderCart();
    } catch(error){
        console.error(error);
        orderMessage.textContent = "Nu am putut confirma comanda. Încearcă din nou; aceeași comandă nu va fi dublată.";

    } finally{
        isSubmitting = false;
        renderCart();
    }
}


placeOrderButton.addEventListener("click", placeOrder);
async function init() {
    await loadTable();
    await loadProducts();
    restoreCart();
}

init().then(updateCartLayout);

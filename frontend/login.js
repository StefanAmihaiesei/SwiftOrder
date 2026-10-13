const loginForm = document.getElementById("login-form");
const loginMessage = document.getElementById("login-message");
const loginButton = loginForm.querySelector("button");

loginForm.addEventListener("submit", async function (event) {
    event.preventDefault();

    if (loginButton.disabled) {
        return;
    }

    loginButton.disabled = true;
    loginMessage.textContent = "Se verifică datele...";

    try {
        const response = await fetch("/auth/login", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username: document.getElementById("username").value.trim(),
                password: document.getElementById("password").value
            })
        });

        if (!response.ok) {
            loginMessage.textContent = response.status === 401
                ? "Username sau parolă incorectă."
                : "Autentificarea nu a reușit. Încearcă din nou.";
            return;
        }

        window.location.replace("/admin");
    } catch (error) {
        loginMessage.textContent = "Nu putem contacta serverul.";
    } finally {
        loginButton.disabled = false;
    }
});
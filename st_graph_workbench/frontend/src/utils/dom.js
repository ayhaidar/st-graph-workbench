function setButtonState(
    button,
    { enabled, title = null, pressed = null } = {}
) {
    if (!button) {
        return;
    }

    button.disabled = !enabled;
    button.setAttribute("aria-disabled", String(!enabled));

    if (title !== null) {
        button.setAttribute("title", title);
        button.setAttribute("aria-label", title);
    }

    if (pressed !== null) {
        button.classList.toggle("is-active", pressed);
        button.setAttribute("aria-pressed", String(pressed));
    }
}

export { setButtonState };

async function saveCurrentSlide(sessionId) {
    const title = document.getElementById("slideTitleInput").value;
    const body = document.getElementById("slideBodyInput").value;
    const flash = document.getElementById("saveFlash");

    flash.className = "flash show ok";
    flash.textContent = "Saving...";

    try {
        const resp = await fetch(`/save-slide/${sessionId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                slide_index: 0,
                title: title,
                body: body
            })
        });

        const data = await resp.json();

        if (!resp.ok) {
            flash.className = "flash show err";
            flash.textContent = data.error || "Save failed.";
            return;
        }

        flash.className = "flash show ok";
        flash.textContent = "Saved. Refresh other device.";

        setTimeout(() => {
            window.location.reload();
        }, 400);

    } catch (err) {
        flash.className = "flash show err";
        flash.textContent = "Save failed.";
    }
}

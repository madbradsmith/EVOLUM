let runStartedAt = null;
let timerInterval = null;
let lastStatus = "IDLE";
let approvedScriptFile = null;
let buildInFlight = false;
let sawFreshBuildStatus = false;
let analyzeFlowMode = null;
const slideCustomImages = {};

const QUOTES = [
    { text: "Here's looking at you, kid.", attr: "— Casablanca", type: "SCREENPLAY" },
    { text: "I'm gonna make him an offer he can't refuse.", attr: "— The Godfather", type: "SCREENPLAY" },
    { text: "You can't handle the truth!", attr: "— A Few Good Men", type: "SCREENPLAY" },
    { text: "Get busy living, or get busy dying.", attr: "— The Shawshank Redemption", type: "SCREENPLAY" },
    { text: "The stuff that dreams are made of.", attr: "— The Maltese Falcon", type: "SCREENPLAY" },
    { text: "Keep your friends close, but your enemies closer.", attr: "— The Godfather Part II", type: "SCREENPLAY" },
    { text: "Every passing minute is another chance to turn it all around.", attr: "— Vanilla Sky", type: "SCREENPLAY" },
    { text: "After all, tomorrow is another day.", attr: "— Gone with the Wind", type: "SCREENPLAY" },
    { text: "It ain't about how hard you hit. It's about how hard you can get hit and keep moving forward.", attr: "— Rocky Balboa", type: "SCREENPLAY" },
    { text: "They may take our lives, but they'll never take our freedom!", attr: "— Braveheart", type: "SCREENPLAY" },
    { text: "Why so serious?", attr: "— The Dark Knight", type: "SCREENPLAY" },
    { text: "To infinity and beyond.", attr: "— Toy Story", type: "SCREENPLAY" },
    { text: "Nobody puts Baby in a corner.", attr: "— Dirty Dancing", type: "SCREENPLAY" },
    { text: "You is kind, you is smart, you is important.", attr: "— The Help", type: "SCREENPLAY" },
    { text: "I feel the need — the need for speed!", attr: "— Top Gun", type: "SCREENPLAY" },
    { text: "Speed!", attr: "— Camera rolling", type: "ON SET" },
    { text: "Quiet on set!", attr: "— First AD", type: "ON SET" },
    { text: "Picture's up!", attr: "— Ready to roll", type: "ON SET" },
    { text: "That's a wrap.", attr: "— End of shoot", type: "ON SET" },
    { text: "We'll fix it in post.", attr: "— Universal set truth", type: "ON SET" },
    { text: "Check the gate.", attr: "— After every take", type: "ON SET" },
    { text: "Martini shot.", attr: "— Last shot of the day", type: "ON SET" },
    { text: "Back to one.", attr: "— Reset", type: "ON SET" },
    { text: "Crafty is open.", attr: "— The most important announcement", type: "ON SET" },
    { text: "Talent on set.", attr: "— Here they come", type: "ON SET" },
    { text: "That's a company move.", attr: "— Packing up", type: "ON SET" },
    { text: "Lunch is up!", attr: "— The call everyone waits for", type: "ON SET" },
];

let quoteInterval = null;
let quoteIndex = Math.floor(Math.random() * QUOTES.length);

function showNextQuote(){
    const textEl = document.getElementById("quoteText");
    const attrEl = document.getElementById("quoteAttribution");
    const labelEl = document.getElementById("quoteLabel");
    if (!textEl) return;
    textEl.style.opacity = "0";
    attrEl.style.opacity = "0";
    setTimeout(() => {
        quoteIndex = (quoteIndex + 1) % QUOTES.length;
        const q = QUOTES[quoteIndex];
        textEl.textContent = "\u201C" + q.text + "\u201D";
        attrEl.textContent = q.attr;
        labelEl.textContent = q.type;
        textEl.style.opacity = "1";
        attrEl.style.opacity = "1";
    }, 600);
}

function startQuoteRotation(){
    showNextQuote();
    quoteInterval = setInterval(showNextQuote, 7000);
}

function stopQuoteRotation(){
    if (quoteInterval) { clearInterval(quoteInterval); quoteInterval = null; }
}
let progressValue = 0;
let progressInterval = null;
let infoModalAction = null;
let activeCompleteView = "preview";
let latestSlidesLoadedForComplete = false;

const fallbackSlides = [
    {
        type: "Title Slide",
        title: "COURT JESTER",
        subtitle: "Animated fantasy comedy with heart, music moments, and chaos.",
        body: "A gifted misfit stumbles into the royal court and becomes the most dangerous fool in the kingdom.",
        caption: "Preview of the currently selected placeholder slide.",
        accent: "#ffb347"
    },
    {
        type: "Logline",
        title: "Logline",
        subtitle: "The one-line pitch",
        body: "When a sharp-tongued outsider is pulled into palace politics, he must outwit enemies, protect the kingdom, and prove that laughter can be a weapon.",
        caption: "Placeholder logline slide preview.",
        accent: "#ff9955"
    },
    {
        type: "Synopsis",
        title: "Synopsis",
        subtitle: "Story overview",
        body: "Court Jester follows a clever survivor who becomes an unexpected player inside a kingdom full of secrets, danger, and spectacle.",
        caption: "Placeholder synopsis slide preview.",
        accent: "#ffc266"
    },
    {
        type: "Characters",
        title: "Main Characters",
        subtitle: "Core ensemble",
        body: "The Jester, the Princess, the Shadow Adviser, and the King each drive a different part of the conflict.",
        caption: "Placeholder characters slide preview.",
        accent: "#ff9c3d"
    },
    {
        type: "Why This Project",
        title: "Why This Project",
        subtitle: "Tone + audience + hook",
        body: "Court Jester blends spectacle, comedy, and emotional storytelling into a world that can support franchise thinking.",
        caption: "Placeholder closing slide preview.",
        accent: "#ffcf70"
    }
];

let refineSlides = JSON.parse(JSON.stringify(fallbackSlides));
let latestRefineProjectTitle = "UNTITLED PROJECT";
let _lastAnalyzedTitle = null;
let currentRefineSlide = 0;
let currentImageOptionModalIndex = 0;
const BASE_PATH_PREFIX = window.BASE_PATH_PREFIX || "";

function enterFlowMode(){
    document.body.classList.add("flow-mode");
}
function exitFlowMode(){
    document.body.classList.remove("flow-mode");
}
function enterActiveBuildMode(){
    document.body.classList.add("active-build");
}
function exitActiveBuildMode(){
    document.body.classList.remove("active-build");
    document.body.classList.remove("complete-mode");
}
function setProgress(value){
    progressValue = Math.max(0, Math.min(100, value));
    const fill = document.getElementById("progressFill");
    if (fill) fill.style.width = progressValue + "%";
}

function stopProgressCreep(){
    if (progressInterval){
        clearInterval(progressInterval);
        progressInterval = null;
    }
}

function startProgressCreep(target, step, delay){
    stopProgressCreep();
    progressInterval = setInterval(() => {
        if (progressValue >= target){
            stopProgressCreep();
            return;
        }
        setProgress(progressValue + step);
    }, delay);
}

function updateProgressForStatus(status){
    if (status === "IDLE"){
        stopProgressCreep();
        setProgress(0);
    } else if (status === "UPLOADED"){
        setProgress(Math.max(progressValue, 12));
        startProgressCreep(22, 1, 500);
    } else if (status === "ANALYZING"){
        setProgress(Math.max(progressValue, 38));
        startProgressCreep(68, 1.2, 700);
    } else if (status === "BUILDING"){
        setProgress(Math.max(progressValue, 78));
        startProgressCreep(96, 1, 500);
    } else if (status === "DEMO_RUNNING"){
        setProgress(Math.max(progressValue, 20));
        startProgressCreep(60, 1, 650);
    } else if (status === "COMPLETE"){
        stopProgressCreep();
        setProgress(100);
    } else if (status === "ERROR"){
        stopProgressCreep();
    }
}

function startAnalyzeFlow(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    analyzeFlowMode = "analyze";
    resetCreateProject();
    showUploadAnalyzeModal();
}

function startUploadFlow(){
    analyzeFlowMode = "upload";
    resetCreateProject();
    showUploadAnalyzeModal();
}

function hideWorkspacePanels(){
    document.getElementById("analyzerPanel").style.display = "none";
    document.getElementById("uploadState").style.display = "none";
    document.getElementById("ideaPanel").style.display = "none";
}

function resumeUploadAfterInfo(){
    closeModal("infoModal");
    infoModalAction = null;
    document.getElementById("uploadModal").classList.add("show");
}

function closeModal(id){
    const el = document.getElementById(id);
    if (el) el.classList.remove("show");
}
function showLoginState(){
    document.getElementById("welcomeState").style.display = "none";
    document.getElementById("loginState").style.display = "block";
}


let selectedFeedbackType = "";

function toggleTopNavMenu(){
    const menu = document.getElementById("topNavMenu");
    if (!menu) return;
    menu.classList.toggle("show");
}
function navTo(url){
    const menu = document.getElementById("topNavMenu");
    if (menu) menu.classList.remove("show");
    setTimeout(() => { window.location.href = url; }, 80);
}
function checkTerms(e) {
    const cb = document.getElementById("agreeTerms");
    const err = document.getElementById("termsError");
    if (cb && !cb.checked) {
        e.preventDefault();
        if (err) err.style.display = "block";
        cb.focus();
        return false;
    }
    if (err) err.style.display = "none";
    return true;
}

function showAuthModal(){
    closeAllModals();
    const badge = document.getElementById("authPlanBadge");
    if (badge && !_selectedPlan) badge.style.display = "none";
    const m = document.getElementById("authModal");
    if (m) m.classList.add("show");
}
function requireAuth(fn){
    if (typeof userLoggedIn !== "undefined" && userLoggedIn) { fn(); return; }
    showAuthModal();
}
function switchAuthTab(tab, el){
    document.querySelectorAll(".auth-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".auth-panel").forEach(p => p.classList.remove("active"));
    if (el) el.classList.add("active");
    const panel = document.getElementById("authPanel_" + tab);
    if (panel) panel.classList.add("active");
}
document.addEventListener("click", function(event){
    const shell = document.querySelector(".top-nav-shell");
    const menu = document.getElementById("topNavMenu");
    if (!shell || !menu) return;
    if (!shell.contains(event.target)){
        menu.classList.remove("show");
    }
});

function openFeedbackModal(){
    const menu = document.getElementById("topNavMenu");
    if (menu) menu.classList.remove("show");
    document.getElementById("feedbackModal").classList.add("show");
}
function openContactModal(){
    const menu = document.getElementById("topNavMenu");
    if (menu) menu.classList.remove("show");
    document.getElementById("contactModal").classList.add("show");
}
function openPrivacyModal(){
    const menu = document.getElementById("topNavMenu");
    if (menu) menu.classList.remove("show");
    document.getElementById("privacyModal").classList.add("show");
}
async function submitContact(){
    const name = (document.getElementById("contactName").value || "").trim();
    const email = (document.getElementById("contactEmail").value || "").trim();
    const message = (document.getElementById("contactMessage").value || "").trim();
    if (!message){ showInfoModal("Contact", "Please write a message before sending."); return; }
    try {
        const resp = await fetch("/contact", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({name, email, message})
        });
        const data = await resp.json();
        closeModal("contactModal");
        document.getElementById("contactName").value = "";
        document.getElementById("contactEmail").value = "";
        document.getElementById("contactMessage").value = "";
        showInfoModal("Message Sent", "Thanks for reaching out. We'll get back to you soon.");
    } catch(e) {
        showInfoModal("Contact", "Something went wrong. Please try again.");
    }
}
function setFeedbackType(type, el){
    selectedFeedbackType = type;
    document.querySelectorAll(".feedback-chip").forEach(btn => btn.classList.remove("active"));
    if (el) el.classList.add("active");
}
function submitFeedback(){
    const name = (document.getElementById("feedbackName") || {}).value || "";
    const email = (document.getElementById("feedbackEmail") || {}).value || "";
    const message = (document.getElementById("feedbackMessage") || {}).value || "";

    if (!message.trim()) {
        alert("Please enter a message before submitting.");
        return;
    }

    fetch("/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: selectedFeedbackType, name, email, message })
    });

    closeModal("feedbackModal");
    showInfoModal("Feedback Received", "Thanks — your beta feedback has been captured for review.");

    const logEl = document.getElementById("liveProcessLog");
    if (logEl){
        const payload = [selectedFeedbackType, name, message].filter(Boolean).join(" | ");
        logEl.innerHTML += "<br><span class=\"terminal-success\">[feedback]</span> " + payload.replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
    }

    selectedFeedbackType = "";
    document.querySelectorAll(".feedback-chip").forEach(btn => btn.classList.remove("active"));
    if (document.getElementById("feedbackName")) document.getElementById("feedbackName").value = "";
    if (document.getElementById("feedbackEmail")) document.getElementById("feedbackEmail").value = "";
    if (document.getElementById("feedbackMessage")) document.getElementById("feedbackMessage").value = "";
}
    function downloadCurrentDeck(){
    window.location.href = "/download/latest.pptx";
}

function closeAllModals(){
    closeModal("loginModal");
    closeModal("infoModal");
    closeModal("uploadModal");
    closeModal("uploadPassModal");
    closeModal("analyzeFailModal");
    closeModal("analyzePassModal");
    closeModal("actorPrepModal");
    closeModal("actorPrepPasteModal");
    closeModal("actorPrepPassModal");
    closeModal("actorBookedModal");
    closeModal("actorBookedPasteModal");
    closeModal("actorBookedCompleteModal");
    closeModal("feedbackModal");
}

function showInfoModal(title, copy, action = null, buttonLabel = "Continue"){
    document.getElementById("infoTitle").textContent = title;
    document.getElementById("infoCopy").textContent = copy;
    infoModalAction = action;
    const btn = document.getElementById("infoModalActionButton");
    if (btn) btn.textContent = buttonLabel;
    document.getElementById("infoModal").classList.add("show");
}

function handleInfoModalAction(){
    closeModal("infoModal");
    if (typeof infoModalAction === "function"){
        const fn = infoModalAction;
        infoModalAction = null;
        fn();
    } else {
        infoModalAction = null;
    }
}

function showUploadState(){
    exitActiveBuildMode();
    enterFlowMode();
    hideWorkspacePanels();

    const homeCardGrid = document.querySelector(".home-card-grid");
    const choicesRow = document.querySelector(".choices-row");
    const uploadState = document.getElementById("uploadState");

    if (homeCardGrid) homeCardGrid.style.display = "none";
    if (choicesRow) choicesRow.style.display = "none";
    if (uploadState) uploadState.style.display = "block";
}

function resetCreateProject(){
    closeAllModals();
    stopProgressCreep();
    setProgress(0);
    exitActiveBuildMode();
    exitFlowMode();
    hideWorkspacePanels();

    approvedScriptFile = null;
    buildInFlight = false;
    sawFreshBuildStatus = false;
    activeCompleteView = "preview";
    currentRefineSlide = 0;
    latestSlidesLoadedForComplete = false;

    const approvedScriptBox = document.getElementById("approvedScriptBox");
    const approvedScriptName = document.getElementById("approvedScriptName");
    const imagesInput = document.getElementById("imagesInput");
    const posterInput = document.getElementById("posterInput");
    const homeCardGrid = document.querySelector(".home-card-grid");
    const choicesRow = document.querySelector(".choices-row");

    if (approvedScriptBox) approvedScriptBox.style.display = "none";
    if (approvedScriptName) approvedScriptName.textContent = "-";
    if (imagesInput) imagesInput.value = "";
    if (posterInput) posterInput.value = "";
    if (homeCardGrid) homeCardGrid.style.display = "block";
    if (choicesRow) choicesRow.style.display = "grid";

    document.getElementById("liveProcessLog").style.display = "block";
    document.getElementById("buildMeta").style.display = "none";
    document.getElementById("buildCopy").style.display = "block";
    document.getElementById("completePanel").style.display = "none";
    const previewStage = document.getElementById("previewStage");
    const refinementStage = document.getElementById("refinementStage");
    if (previewStage) previewStage.style.display = "block";
    if (refinementStage) refinementStage.style.display = "none";
}

function newDeck() {
    resetCreateProject();
    showUploadAnalyzeModal();
}

function showUploadAnalyzeModal(){
    document.getElementById("uploadModal").classList.add("show");
}

function openAnalyzePassModal(){
    closeAllModals();
    document.getElementById("analyzePassModal").classList.add("show");
}

function analyzeToDecFlow(){
    closeAllModals();
    if (!approvedScriptFile) {
        // Script was lost (e.g. page reload) — fall back to upload form
        newDeck();
        return;
    }
    startBuildDirect();
}

function startBuildDirect() {
    if (!approvedScriptFile) return;
    buildInFlight = true;
    sawFreshBuildStatus = false;
    resetTimer();
    showLiveProcess();
    setLocalStatus("UPLOADED");

    const formData = new FormData();
    formData.append("script", approvedScriptFile);
    const titleFromBrain = _lastAnalyzedTitle;
    const titleFromFile = approvedScriptFile.name.replace(/\.[^.]+$/, "").replace(/[_\-]+/g, " ").trim();
    const title = titleFromBrain || titleFromFile;
    if (title) formData.append("project_title", title);
    const _vs = document.getElementById("visualStyleSelect");
    if (_vs) formData.append("visual_style", _vs.value);

    fetch("/upload", { method: "POST", body: formData })
        .then(res => {
            if (res.status === 403) {
                buildInFlight = false;
                showProjectLimitModal();
            }
        })
        .catch(err => console.error("Upload failed:", err));
}

function continueToApprovedUpload(){
    closeAllModals();
    showUploadState();

    const scriptInput = document.getElementById("scriptInput");

    if (approvedScriptFile && scriptInput) {
        try {
            const dt = new DataTransfer();
            dt.items.add(approvedScriptFile);
            scriptInput.files = dt.files;
        } catch (e) {}
    }
}

async function analyzeSelectedScript(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    const fileInput = document.getElementById("uploadAnalyzeFile");

    if (!fileInput || !fileInput.files || fileInput.files.length === 0){
        closeModal("uploadModal");
        document.getElementById("infoTitle").textContent = "Upload Script";
        document.getElementById("infoCopy").textContent = "Please choose a script file before continuing.";
        document.getElementById("infoModal").classList.add("show");
        return;
    }

    const file = fileInput.files[0];
    const fileName = (file.name || "").toLowerCase();
    const passes = fileName.endsWith(".txt") || fileName.endsWith(".pdf") || fileName.endsWith(".fdx") || fileName.endsWith(".docx") || fileName.endsWith(".doc");

    if (!passes){
        closeModal("uploadModal");
        showInfoModal("Unsupported File", "Please upload a TXT, PDF, FDX, or DOCX file.");
        return;
    }

    closeModal("uploadModal");

    // Show progress modal
    const progressModal = document.getElementById("buildProgressModal");
    document.getElementById("buildProgressTitle").textContent = "Analyzing Your Script";
    document.getElementById("buildProgressCopy").textContent = "The Developum AI Engine is reading your script. This takes about 30–60 seconds.";
    document.getElementById("buildProgressStage").textContent = "Analyzing script with Developum AI Engine…";
    document.getElementById("buildProgressFill").style.width = "35%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    progressModal.classList.add("show");

    const formData = new FormData();
    formData.append("script", file);

    try {
        const response = await fetch("/analyze-script-pass", {
            method: "POST",
            body: formData
        });

        if (!response.ok){
            document.getElementById("buildProgressWorking").style.display = "none";
            document.getElementById("buildProgressTitle").textContent = "Analysis Failed";
            document.getElementById("buildProgressCopy").textContent = "Something went wrong. Please check your file and try again.";
            const actionsEl = document.getElementById("buildProgressActions");
            actionsEl.style.display = "flex";
            actionsEl.querySelector("button").textContent = "Close";
            actionsEl.querySelector("button").onclick = closeBuildProgressModal;
            return;
        }

        const data = await response.json();
        window.latestGeneratedDeck = data.deck || "";

        const summaryEl = document.getElementById("analysisSummaryCopy");
        if (summaryEl) {
            summaryEl.textContent =
                data.summary_note ||
                "Your script has been analyzed and your full report is ready to view.";
        }

        document.getElementById("buildProgressFill").style.width = "100%";
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Analysis Complete";
        document.getElementById("buildProgressCopy").textContent = "Your script has been analyzed by the Developum AI Engine.";
        const actionsEl = document.getElementById("buildProgressActions");
        actionsEl.style.display = "flex";

        // Always store file + brain title so Create Pitch Deck can use them directly
        approvedScriptFile = file;
        _lastAnalyzedTitle = data.title || null;

        if (analyzeFlowMode === "analyze") {
            actionsEl.querySelector("button").textContent = "View Results";
            actionsEl.querySelector("button").onclick = function(){
                closeBuildProgressModal();
                openAnalyzePassModal();
            };
        } else {
            closeBuildProgressModal();
            startBuildDirect();
        }

    } catch (err) {
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Analysis Failed";
        document.getElementById("buildProgressCopy").textContent = "Something went wrong. Please try again.";
        const actionsEl = document.getElementById("buildProgressActions");
        actionsEl.style.display = "flex";
        actionsEl.querySelector("button").textContent = "Close";
        actionsEl.querySelector("button").onclick = closeBuildProgressModal;
    }
}


function validateUploadAndStart(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { showAuthModal(); return false; }
    const form = document.querySelector('#uploadState form');
    const imagesInput = document.getElementById("imagesInput");

    if (imagesInput && imagesInput.files && imagesInput.files.length > 10){
        showInfoModal("Upload Images", "Please upload no more than 10 images.");
        return false;
    }

    if (imagesInput && imagesInput.files){
        for (const file of imagesInput.files){
            if (file.size > 1024 * 1024){
                showInfoModal("Upload Images", "Each image must be 1 MB or smaller.");
                return false;
            }
        }
    }

    buildInFlight = true;
    sawFreshBuildStatus = false;
    resetTimer();
    showLiveProcess();
    setLocalStatus("UPLOADED");

    const formData = new FormData(form);
    // Auto-append project title from script filename
    if (approvedScriptFile && !formData.get("project_title")) {
        const stem = approvedScriptFile.name.replace(/\.[^.]+$/, "");
        const title = stem.replace(/[_\-]+/g, " ").trim();
        if (title) formData.append("project_title", title);
    }

    fetch("/upload", {
        method: "POST",
        body: formData
    }).then(res => {
        if (res.status === 403) {
            buildInFlight = false;
            showProjectLimitModal();
        }
    }).catch(err => {
        console.error("Upload failed:", err);
    });

    return false;
}

function showLiveProcess(){
    exitFlowMode();
    enterActiveBuildMode();
    hideWorkspacePanels();
    stopProgressCreep();
    setProgress(0);

    const homeCardGrid = document.querySelector(".home-card-grid");
    const choicesRow = document.querySelector(".choices-row");
    if (homeCardGrid) homeCardGrid.style.display = "none";
    if (choicesRow) choicesRow.style.display = "none";

    document.getElementById("analyzerPanel").style.display = "block";
    document.getElementById("buildProgressBar").style.display = "block";
    document.getElementById("liveProcessLog").style.display = "block";
    document.getElementById("buildCopy").style.display = "block";
    document.getElementById("buildMeta").style.display = "flex";
    document.getElementById("completePanel").style.display = "none";
    document.body.classList.remove("complete-mode");
    startQuoteRotation();
}

function escapeHtml(text){
    return String(text)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}

function renderLiveProcessLog(status){
    const logEl = document.getElementById("liveProcessLog");
    if (!logEl) return;

    let lines = [];
    if (status === "IDLE"){
        lines = ['[system] waiting for deck generation...','','> pipeline idle','> upload a script and click Generate Deck to begin'];
    } else if (status === "UPLOADED"){
        lines = ['[system] build request received','','> intake: screenplay file accepted','> preparing canonical input','> initializing pipeline environment','> waiting for analysis stage...'];
    } else if (status === "ANALYZING" || status === "running"){
        lines = ['[system] Analyzing Screenplay...','','> converting script into engine-ready format','> cleaning screenplay content','> sending story into brain pass','> extracting characters','> identifying world and tone','> generating pitch intelligence','> analysis still running...'];
    } else if (status === "BUILDING"){
        lines = [
            '[system] deck generation in progress',
            '',
            '> analysis approved',
            '> creating slide plan',
            '> selecting visual placements',
            '> assembling presentation structure',
            '> building PowerPoint file',
            '> finalizing export package...',
            '> preparing delivery...'
        ];
    } else if (status === "DEMO_RUNNING"){
        lines = ['[system] demo build launched','','> loading demo screenplay','> initializing demo pipeline','> analysis queue started','> waiting for deck assembly...'];
    } else if (status === "COMPLETE"){
        lines = ['[system] build complete','','> screenplay processed successfully','> analysis complete','> deck assembly complete','> PowerPoint export ready','','[success] preview ready'];
    } else if (status === "ERROR"){
        lines = ['[system] pipeline interrupted','','> build error detected','> story analysis may be incomplete','> deck assembly may have stopped early','> check terminal / backend logs for details'];
    } else {
        lines = ['[system] processing...','','> pipeline active'];
    }

    const html = lines.map((line) => {
        const safe = escapeHtml(line);
        if (line.startsWith('[success]')) return '<span class="terminal-success">' + safe + '</span>';
        if (line.startsWith('[system]')) return '<span class="terminal-prompt">' + safe + '</span>';
        if (line.startsWith('>')) return '<span class="terminal-accent">' + safe + '</span>';
        return safe;
    }).join('<br>')

    logEl.innerHTML = html;
    logEl.scrollTop = logEl.scrollHeight;
}

function setLocalStatus(status){
    updateStatusUI(status);
}

function formatElapsed(seconds){
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return String(mins).padStart(2, "0") + ":" + String(secs).padStart(2, "0");
}

function startTimer(){
    if (!runStartedAt){ runStartedAt = Date.now(); }
    if (timerInterval){ return; }
    timerInterval = setInterval(() => {
        if (!runStartedAt) return;
        const elapsedSeconds = Math.floor((Date.now() - runStartedAt) / 1000);
        const formatted = formatElapsed(elapsedSeconds);
        document.getElementById("inlineStatusValue").textContent = lastStatus + " • " + formatted;
    }, 250);
}

function stopTimer(){
    if (timerInterval){
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function resetTimer(){
    runStartedAt = null;
    stopTimer();
    document.getElementById("inlineStatusValue").textContent = "IDLE • 00:00";
}

function makePreviewSlideDataUri(title, subtitle, accent){
    const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="720" height="960" viewBox="0 0 720 960">
        <defs>
            <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#111111"/>
                <stop offset="100%" stop-color="#1b1b1b"/>
            </linearGradient>
            <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#ff7a00"/>
                <stop offset="100%" stop-color="${accent}"/>
            </linearGradient>
        </defs>
        <rect width="720" height="960" fill="url(#bg)"/>
        <rect x="50" y="52" width="620" height="6" rx="3" fill="url(#accent)"/>
        <rect x="50" y="120" width="620" height="310" rx="20" fill="#0f0f0f" stroke="rgba(255,255,255,0.12)"/>
        <circle cx="360" cy="275" r="92" fill="rgba(255,122,0,0.12)"/>
        <rect x="120" y="228" width="480" height="94" rx="16" fill="rgba(255,255,255,0.03)"/>
        <text x="60" y="520" font-family="Arial, Helvetica, sans-serif" font-size="42" font-weight="700" fill="#ffffff">${title}</text>
        <text x="60" y="575" font-family="Arial, Helvetica, sans-serif" font-size="24" fill="#cfcfcf">${subtitle}</text>
        <rect x="60" y="650" width="600" height="16" rx="8" fill="rgba(255,255,255,0.10)"/>
        <rect x="60" y="688" width="560" height="16" rx="8" fill="rgba(255,255,255,0.08)"/>
        <rect x="60" y="726" width="585" height="16" rx="8" fill="rgba(255,255,255,0.08)"/>
        <rect x="60" y="764" width="520" height="16" rx="8" fill="rgba(255,255,255,0.08)"/>
        <text x="60" y="890" font-family="Arial, Helvetica, sans-serif" font-size="18" fill="#333333">EVOLUM STUDIO</text>
    </svg>`;
    return "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
}

function makeAccentForIndex(index){
    const accents = ["#ffb347", "#ff9955", "#ffc266", "#ff9c3d", "#ffcf70"];
    return accents[index % accents.length];
}


function projectFileUrl(path){
    if (!path) return "";

    const rel = String(path)
        .replace(BASE_PATH_PREFIX || "", "")
        .replace(/^\/?opt\/render\/project\/src\//, "")
        .replace(/^\/+/, "");

    return "/project-file?path=" + encodeURIComponent(rel);
}


function normalizeImageOption(option, fallbackSlide, optionIndex){
    const normalized = option || {};
    const imagePath = normalized.image_path || "";
    return {
        rank: normalized.rank || optionIndex + 1,
        option_id: normalized.option_id || `option_${optionIndex + 1}`,
        label: normalized.label || `Option ${optionIndex + 1}`,
        focus: normalized.focus || "",
        image_path: imagePath,
        image_name: normalized.image_name || "",
        image_source: normalized.image_source || "",
        image_url: normalized.image_url || projectFileUrl(imagePath)
    };
}

function normalizeSlideForRefine(slide, index){
    const normalized = slide || {};
    const imagePath = normalized.image_path || "";
    const options = Array.isArray(normalized.image_options)
        ? normalized.image_options.map((option, optionIndex) => normalizeImageOption(option, normalized, optionIndex))
        : [];

    return {
        type: normalized.type || normalized.stage || normalized.layout || `Slide ${index + 1}`,
        title: normalized.title || `Slide ${index + 1}`,
        subtitle: normalized.subtitle || "",
        body: normalized.body || normalized.content || normalized.text || normalized.copy || "",
        caption: normalized.caption || "Generated slide preview.",
        accent: normalized.accent || makeAccentForIndex(index),
        layout: normalized.layout || "text",
        stage: normalized.stage || "refine",
        image_url: normalized.image_url || projectFileUrl(imagePath),
        image_name: normalized.image_name || "",
        image_path: imagePath,
        image_source: normalized.image_source || "",
        image_options: options,
        selected_option_id: normalized.selected_option_id || (options[0] && options[0].option_id) || "selected"
    };
}

function previewImageSrcForSlide(slide){
    if (slide && slide.image_url){
        return slide.image_url;
    }
    if (slide && slide.image_path){
        return projectFileUrl(slide.image_path);
    }
    return makePreviewSlideDataUri((slide && slide.title) || "", (slide && slide.subtitle) || "", (slide && slide.accent) || "#ffb347");
}

async function syncLatestSlidesForPreview(){
    const loaded = await loadLatestRefineSlides();
    if (loaded) latestSlidesLoadedForComplete = true;
    renderDeckPreview();
    if (activeCompleteView === "refine") {
        renderCurrentRefineSlide();
    }
    return loaded;
}

async function loadLatestRefineSlides(){
    try {
        if (activeLoadedProjectId) {
            const response = await fetch(`/project/${activeLoadedProjectId}/slides`, { cache: "no-store" });
            if (!response.ok) throw new Error("slides_missing");
            const data = await response.json();
            if (data.error) throw new Error(data.error);
            const slides = data.slides || [];
            if (!slides.length) throw new Error("manifest_empty");
            refineSlides = slides.map((slide, index) => normalizeSlideForRefine(slide, index));
            latestRefineProjectTitle = data.title || refineSlides[0]?.title || "UNTITLED PROJECT";
        } else {
            const response = await fetch(`/api/latest-manifest`, { cache: "no-store" });
            if (!response.ok) throw new Error("manifest_missing");
            const data = await response.json();
            if (!Array.isArray(data) || !data.length) throw new Error("manifest_empty");
            refineSlides = data.map((slide, index) => normalizeSlideForRefine(slide, index));
            latestRefineProjectTitle = refineSlides[0]?.title || "UNTITLED PROJECT";
        }
        currentRefineSlide = Math.min(currentRefineSlide, Math.max(refineSlides.length - 1, 0));
        return true;
    } catch (err) {
        if (activeLoadedProjectId) {
            try {
                const response = await fetch(`/api/latest-manifest`, { cache: "no-store" });
                if (response.ok) {
                    const data = await response.json();
                    if (Array.isArray(data) && data.length) {
                        refineSlides = data.map((slide, index) => normalizeSlideForRefine(slide, index));
                        latestRefineProjectTitle = refineSlides[0]?.title || "UNTITLED PROJECT";
                        currentRefineSlide = Math.min(currentRefineSlide, Math.max(refineSlides.length - 1, 0));
                        return true;
                    }
                }
            } catch (_) {}
        }
        refineSlides = fallbackSlides.map((slide, index) => normalizeSlideForRefine(slide, index));
        latestRefineProjectTitle = "UNTITLED PROJECT";
        currentRefineSlide = Math.min(currentRefineSlide, Math.max(refineSlides.length - 1, 0));
        return false;
    }
}

function renderDeckPreview(){
    const strip = document.getElementById("deckPreviewStrip");
    if (!strip) return;

    if (!Array.isArray(refineSlides) || !refineSlides.length){
        strip.innerHTML = "";
        return;
    }

    strip.innerHTML = refineSlides.map((slide, index) => {
        const hasRealImage = !!(slide.image_url || slide.image_path);
        const titleText = escapeHtml(slide.title || `Slide ${index + 1}`);
        const typeText = escapeHtml(slide.type || `Slide ${index + 1}`);
        const accentColor = slide.accent || "#ff7a00";

        let mediaHtml;
        if (hasRealImage) {
            mediaHtml = `<div class="deck-preview-img-wrap">
                <img src="${previewImageSrcForSlide(slide)}" alt="Slide ${index + 1}">
                <div class="deck-preview-overlay"><div class="deck-preview-overlay-title">${titleText}</div></div>
            </div>`;
        } else {
            const bodyPreview = escapeHtml((slide.body || slide.subtitle || "").slice(0, 200));
            mediaHtml = `<div class="deck-preview-text-slide" style="border-top:3px solid ${accentColor};">
                <div class="deck-preview-text-title">${titleText}</div>
                ${bodyPreview ? `<div class="deck-preview-text-body">${bodyPreview}</div>` : ""}
            </div>`;
        }

        const snippetText = hasRealImage
            ? escapeHtml((slide.subtitle || slide.body || "").slice(0, 90))
            : "";

        return `
            <div class="deck-preview-card" draggable="true"
                 onclick="jumpToRefineSlide(${index})" title="${titleText} — click to edit"
                 ondragstart="previewDragStart(event,${index})"
                 ondragover="previewDragOver(event,${index})"
                 ondragleave="previewDragLeave(event)"
                 ondrop="previewDrop(event,${index})"
                 ondragend="previewDragEnd(event)">
                <button class="deck-preview-delete" onclick="event.stopPropagation();deletePreviewSlide(${index})" title="Delete slide">×</button>
                ${mediaHtml}
                <div class="deck-preview-card-title">
                    <span class="deck-preview-num">${index + 1}</span>${typeText}
                    ${snippetText ? `<div class="deck-preview-snippet">${snippetText}</div>` : ""}
                </div>
            </div>
        `;
    }).join("");
}

function jumpToRefineSlide(index){
    currentRefineSlide = Math.max(0, Math.min(index, refineSlides.length - 1));
    openRefinementStage();
}

// --- Preview panel: delete & drag-reorder ---
let _previewDragSrc = null;

function deletePreviewSlide(index) {
    if (refineSlides.length <= 1) { alert("A deck needs at least one slide."); return; }
    const label = refineSlides[index].type || refineSlides[index].title || "Slide";
    if (!confirm(`Delete slide ${index + 1}: "${label}"?`)) return;
    refineSlides.splice(index, 1);
    if (currentRefineSlide >= refineSlides.length) currentRefineSlide = refineSlides.length - 1;
    renderDeckPreview();
    renderRefineSlideList();
}

function previewDragStart(e, index) {
    _previewDragSrc = index;
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
    setTimeout(() => { if (e.target) e.target.classList.add("dragging"); }, 0);
}

function previewDragOver(e, index) {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (_previewDragSrc !== null && _previewDragSrc !== index) {
        e.currentTarget.classList.add("drag-over");
    }
}

function previewDragLeave(e) {
    e.currentTarget.classList.remove("drag-over");
}

function previewDragEnd(e) {
    document.querySelectorAll(".deck-preview-card").forEach(c => c.classList.remove("drag-over", "dragging"));
    _previewDragSrc = null;
}

function previewDrop(e, toIndex) {
    e.preventDefault();
    e.stopPropagation();
    const from = _previewDragSrc;
    _previewDragSrc = null;
    if (from === null || from === toIndex) return;
    const moved = refineSlides.splice(from, 1)[0];
    refineSlides.splice(toIndex, 0, moved);
    if (currentRefineSlide === from) {
        currentRefineSlide = toIndex;
    } else if (from < currentRefineSlide && toIndex >= currentRefineSlide) {
        currentRefineSlide--;
    } else if (from > currentRefineSlide && toIndex <= currentRefineSlide) {
        currentRefineSlide++;
    }
    renderDeckPreview();
    renderRefineSlideList();
}

function renderRefineSlideList(){
    const list = document.getElementById("slideList");
    if (!list) return;
    list.innerHTML = refineSlides.map((slide, index) => {
        const active = index === currentRefineSlide ? "active" : "";
        return `<div class="slide-pill ${active}">${index + 1}. ${slide.type}</div>`;
    }).join("");
}


function renderImageOptionStrip(){
    const strip = document.getElementById("imageOptionStrip");
    const empty = document.getElementById("imageOptionEmpty");
    if (!strip || !empty || !Array.isArray(refineSlides) || !refineSlides.length) return;

    const slide = refineSlides[currentRefineSlide];
    const options = Array.isArray(slide.image_options) ? slide.image_options : [];

    if (!options.length){
        strip.innerHTML = "";
        empty.style.display = "block";
        return;
    }

    empty.style.display = "none";
    const noImageActive = slide.image_path === "__none__" ? "active" : "";
    strip.innerHTML = options.map((option, optionIndex) => {
        const active = option.option_id === slide.selected_option_id ? "active" : "";
        return `
            <div class="image-option-thumb ${active}" onclick="openImageOptionModal(${optionIndex})">
                <img src="${option.image_url || previewImageSrcForSlide(slide)}" alt="${option.label || 'Image option'}">
                <div class="image-option-thumb-label">${option.label || `Option ${optionIndex + 1}`}</div>
            </div>
        `;
    }).join("") + `
        <div class="image-option-thumb no-image-tile ${noImageActive}" onclick="selectNoImage()" title="Text only — no background image">
            <div class="no-image-icon">T</div>
            <div class="image-option-thumb-label">No Image</div>
        </div>
    `;
}

function openImageOptionModal(optionIndex){
    const slide = refineSlides[currentRefineSlide];
    const options = Array.isArray(slide.image_options) ? slide.image_options : [];
    if (!options.length) return;
    currentImageOptionModalIndex = Math.max(0, Math.min(optionIndex, options.length - 1));
    renderImageOptionModal();
    document.getElementById("imageOptionModal").classList.add("show");
}

function renderImageOptionModal(){
    const slide = refineSlides[currentRefineSlide];
    const options = Array.isArray(slide.image_options) ? slide.image_options : [];
    const option = options[currentImageOptionModalIndex];
    if (!option) return;

    document.getElementById("imageOptionModalTitle").textContent = option.label || "Preview Image Option";
    document.getElementById("imageOptionModalPreview").src = option.image_url || previewImageSrcForSlide(slide);
    document.getElementById("imageOptionModalMeta").textContent =
        `Slide ${currentRefineSlide + 1} • ${slide.title || slide.type || "Slide"} • ${option.focus || "image option"}`;
}

function shiftImageOptionModal(direction){
    const slide = refineSlides[currentRefineSlide];
    const options = Array.isArray(slide.image_options) ? slide.image_options : [];
    if (!options.length) return;
    currentImageOptionModalIndex = (currentImageOptionModalIndex + direction + options.length) % options.length;
    renderImageOptionModal();
}

function selectCurrentImageOption(){
    const slide = refineSlides[currentRefineSlide];
    const options = Array.isArray(slide.image_options) ? slide.image_options : [];
    const option = options[currentImageOptionModalIndex];
    if (!option) return;

    slide.selected_option_id = option.option_id || "selected";
    slide.image_path = option.image_path || "";
    slide.image_name = option.image_name || "";
    slide.image_source = option.image_source || "";
    slide.image_url = option.image_url || "";
    document.getElementById("refineSlideImage").src = previewImageSrcForSlide(slide);
    document.getElementById("refineSlideCaption").textContent = `${option.label || "Current Pick"} • ${slide.image_name || slide.title || "image selected"}`;
    renderImageOptionStrip();
    renderDeckPreview();
    closeModal("imageOptionModal");
}

async function loadSlideImageOptions(){
    const slide = refineSlides[currentRefineSlide];
    const title = document.getElementById("refineTitleInput").value || slide.title || "";
    const body = document.getElementById("refineBodyInput").value || slide.body || "";
    const userPrompt = (document.getElementById("refineImagePrompt").value || "").trim();
    const btn = document.getElementById("loadOptionsBtn");

    btn.disabled = true;
    btn.textContent = "Generating options…";

    try {
        const resp = await fetch("/generate-slide-options", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                slide_title: title,
                slide_body: body,
                user_prompt: userPrompt,
                slide_number: currentRefineSlide + 1,
                current_image_path: slide.image_path || "",
                current_image_url: slide.image_url || "",
            })
        });
        const data = await resp.json();
        if (data.options && data.options.length) {
            slide.image_options = [
                ...(slide.image_options || []).filter(o => o.option_id === "selected"),
                ...data.options
            ];
            renderImageOptionStrip();
            showInfoModal("Image Options", `${data.options.length} new options loaded. Browse them in the image strip below.`);
        } else {
            showInfoModal("Image Options", data.error || "Could not generate options. Try again.");
        }
    } catch(e) {
        showInfoModal("Image Options", "Something went wrong. Try again.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Load Image Options";
    }
}

async function regenerateSlideImage(){
    const slide = refineSlides[currentRefineSlide];
    const title = document.getElementById("refineTitleInput").value || slide.title || "";
    const body = document.getElementById("refineBodyInput").value || slide.body || "";
    const userPrompt = (document.getElementById("refineImagePrompt").value || "").trim();
    const btn = document.getElementById("regenImageBtn");

    btn.disabled = true;
    btn.textContent = "Generating…";

    try {
        const resp = await fetch("/regenerate-slide-image", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                slide_title: title,
                slide_body: body,
                user_prompt: userPrompt,
                slide_number: currentRefineSlide + 1,
            })
        });
        const data = await resp.json();
        if (data.image_url) {
            slide.image_url = data.image_url;
            slide.image_path = data.image_path || "";
            slide.image_source = "fal_generated";
            slide.selected_option_id = "regen";
            document.getElementById("refineSlideImage").src = data.image_url;
            document.getElementById("refineSlideCaption").textContent = "Regenerated image";
            renderImageOptionStrip();
            renderDeckPreview();
        } else {
            showInfoModal("Image Generation", data.error || "Generation failed. Try again.");
        }
    } catch(e) {
        showInfoModal("Image Generation", "Something went wrong. Try again.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Regenerate Image";
    }
}

function selectNoImage(){
    const slide = refineSlides[currentRefineSlide];
    slide.selected_option_id = "__none__";
    slide.image_path = "__none__";
    slide.image_name = "none";
    slide.image_source = "text_only";
    slide.image_url = "";
    document.getElementById("refineSlideImage").src = "";
    document.getElementById("refineSlideCaption").textContent = "Text Only — no background image";
    renderImageOptionStrip();
    renderDeckPreview();
}

function renderCurrentRefineSlide(){
    if (!Array.isArray(refineSlides) || !refineSlides.length){
        return;
    }

    const slide = refineSlides[currentRefineSlide];
    document.getElementById("slideCounter").textContent = `Slide ${currentRefineSlide + 1} of ${refineSlides.length}`;
    document.getElementById("slideType").textContent = slide.type;
    document.getElementById("refineTitleInput").value = slide.title;
    document.getElementById("refineSubtitleInput").value = slide.subtitle;
    document.getElementById("refineBodyInput").value = slide.body;
    const customImg = slideCustomImages[currentRefineSlide];
    document.getElementById("refineSlideImage").src = customImg ? customImg.url : previewImageSrcForSlide(slide);
    document.getElementById("refineSlideCaption").textContent = slide.caption || `Preview for ${latestRefineProjectTitle}`;
    const nameEl = document.getElementById("slideImageUploadName");
    if (nameEl) nameEl.textContent = customImg ? "Custom image set" : "No image selected";
    renderImageOptionStrip();
    document.getElementById("refineBackBtn").disabled = currentRefineSlide === 0;
    document.getElementById("refineNextBtn").disabled = currentRefineSlide === refineSlides.length - 1;
    renderRefineSlideList();
}

function saveCurrentRefineSlide(){
    if (!Array.isArray(refineSlides) || !refineSlides.length){
        return;
    }
    const slide = refineSlides[currentRefineSlide];
    slide.title = document.getElementById("refineTitleInput").value;
    slide.subtitle = document.getElementById("refineSubtitleInput").value;
    slide.body = document.getElementById("refineBodyInput").value;
    renderCurrentRefineSlide();
    renderDeckPreview();
}

async function openRefinementStage(){
    syncTrackEnterRefine();
    activeCompleteView = "refine";
    const loaded = await loadLatestRefineSlides();
    if (loaded) latestSlidesLoadedForComplete = true;
    document.getElementById("previewStage").style.display = "none";
    document.getElementById("refinementStage").style.display = "block";
    renderDeckPreview();
    renderCurrentRefineSlide();
}

function returnToPreviewStage(){
    saveCurrentRefineSlide();
    activeCompleteView = "preview";
    document.getElementById("refinementStage").style.display = "none";
    document.getElementById("previewStage").style.display = "block";
    renderDeckPreview();
}

function goPrevRefineSlide(){
    saveCurrentRefineSlide();
    if (currentRefineSlide > 0){
        currentRefineSlide -= 1;
        renderCurrentRefineSlide();
    }
}

function goNextRefineSlide(){
    saveCurrentRefineSlide();
    if (currentRefineSlide < refineSlides.length - 1){
        currentRefineSlide += 1;
        renderCurrentRefineSlide();
    }
}

function changePlaceholderImage(){
    showInfoModal("Change Image", "Image selection is the next pass. For now, refine text first.");
}
const _BUILD_QUOTES = [
    { text: "Every great film begins with a great story — written for the screen, felt in the gut.", attr: "— Screenwriting tradition" },
    { text: "The pitch is where the dream meets the room.", attr: "— Film development saying" },
    { text: "Cinema is a mirror by which we often see ourselves.", attr: "— Martin Scorsese" },
    { text: "A story is not what happened. It’s why it happened, and to whom.", attr: "— Robert McKee" },
    { text: "The most honest form of filmmaking is to make a film for yourself.", attr: "— Peter Jackson" },
    { text: "You can’t wait for inspiration. You have to go after it with a club.", attr: "— Jack London" },
    { text: "Drama is life with the dull bits cut out.", attr: "— Alfred Hitchcock" },
    { text: "The secret to a great pitch is making them feel the movie.", attr: "— Hollywood maxim" },
    { text: "Every story worth telling is a story about change.", attr: "— Writing principle" },
    { text: "Character is revealed through choice under pressure.", attr: "— Aristotle (via McKee)" },
    { text: "Films can illuminate the darkness or they can be part of it.", attr: "— Roger Ebert" },
    { text: "Make the audience want to know what happens next. That’s the whole job.", attr: "— Billy Wilder" },
];
let _quoteInterval = null;
let _quoteIdx = 0;

function _startBuildQuotes() {
    const textEl = document.getElementById("buildQuoteText");
    const attrEl = document.getElementById("buildQuoteAttr");
    if (!textEl) return;
    _quoteIdx = Math.floor(Math.random() * _BUILD_QUOTES.length);
    const show = () => {
        const q = _BUILD_QUOTES[_quoteIdx % _BUILD_QUOTES.length];
        textEl.style.opacity = "0";
        attrEl.style.opacity = "0";
        setTimeout(() => {
            textEl.textContent = "\u201c" + q.text + "\u201d";
            attrEl.textContent = q.attr;
            textEl.style.opacity = "1";
            attrEl.style.opacity = "1";
        }, 600);
        _quoteIdx++;
    };
    show();
    _quoteInterval = setInterval(show, 5000);
}

function _stopBuildQuotes() {
    if (_quoteInterval) { clearInterval(_quoteInterval); _quoteInterval = null; }
}

function openBuildProgressModal(){
    const modal = document.getElementById("buildProgressModal");
    document.getElementById("buildProgressTitle").textContent = "Building Your Deck";
    document.getElementById("buildProgressCopy").textContent = "This takes about 30–60 seconds while we generate your images.";
    document.getElementById("buildProgressStage").textContent = "Analyzing script\u2026";
    document.getElementById("buildProgressFill").style.width = "10%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    modal.classList.add("show");
    _startBuildQuotes();
}

function updateBuildProgressModal(status){
    const modal = document.getElementById("buildProgressModal");
    if (!modal.classList.contains("show")) return;
    const fill = document.getElementById("buildProgressFill");
    const stage = document.getElementById("buildProgressStage");
    if (status === "ANALYZING"){
        stage.textContent = "Analyzing script with Developum AI Engine\u2026";
        fill.style.width = "35%";
    } else if (status === "BUILDING"){
        stage.textContent = "Generating images and building deck\u2026";
        fill.style.width = "75%";
    } else if (status === "COMPLETE"){
        _stopBuildQuotes();
        fill.style.width = "100%";
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Deck Ready";
        document.getElementById("buildProgressCopy").textContent = "Your pitch deck has been generated.";
        document.getElementById("buildProgressActions").style.display = "flex";
    } else if (status === "ERROR"){
        _stopBuildQuotes();
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Build Failed";
        document.getElementById("buildProgressCopy").textContent = "Something went wrong. Please try again.";
        document.getElementById("buildProgressActions").style.display = "flex";
        document.getElementById("buildProgressActions").querySelector("button").textContent = "Close";
    }
}

function closeBuildProgressModal(){
    _stopBuildQuotes();
    document.getElementById("buildProgressModal").classList.remove("show");
}

async function submitRefineDeck() {
    saveCurrentRefineSlide();
    document.getElementById("buildProgressTitle").textContent = "Rebuilding Deck";
    document.getElementById("buildProgressCopy").textContent = "Applying your edits and rebuilding the deck.";
    document.getElementById("buildProgressStage").textContent = "Rebuilding…";
    document.getElementById("buildProgressFill").style.width = "35%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    document.getElementById("buildProgressModal").classList.add("show");

    try {
        const res = await fetch("/refine-deck", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ slides: refineSlides })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Rebuild failed.");
        document.getElementById("buildProgressFill").style.width = "100%";
        closeBuildProgressModal();
        latestSlidesLoadedForComplete = false;
        await syncLatestSlidesForPreview();
        renderCurrentRefineSlide();
    } catch (e) {
        closeBuildProgressModal();
        showInfoModal("Rebuild Failed", e.message || "Rebuild failed.");
    }
}

async function submitRegenDeck() {
    syncTrackRegen();
    let prompt = (
        document.getElementById("refineRegenInput")?.value ||
        document.getElementById("regenPromptInput")?.value || ""
    ).trim();
    if (!prompt) {
        showInfoModal("New Direction Required", "Type a new creative direction in the input field above the Regenerate Deck button, then try again.");
        return;
    }

    document.getElementById("buildProgressTitle").textContent = "Regenerating Deck";
    document.getElementById("buildProgressCopy").textContent = "Please wait while your updated deck is rebuilt.";
    document.getElementById("buildProgressStage").textContent = "Rebuilding deck…";
    document.getElementById("buildProgressFill").style.width = "35%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    document.getElementById("buildProgressModal").classList.add("show");

    try {
        const res = await fetch("/regen-deck", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (!data.ok) {
            throw new Error(data.error || "Regenerate failed.");
        }
        document.getElementById("buildProgressFill").style.width = "100%";
        closeBuildProgressModal();
        latestSlidesLoadedForComplete = false;
        await syncLatestSlidesForPreview();
        renderCurrentRefineSlide();
    } catch (e) {
        closeBuildProgressModal();
        showInfoModal("Regenerate Deck", e.message || "Regenerate failed.");
    }
}


// ===== JAVASCRIPT: ACTOR PREP FLOW START ==============
function startActorPrepFlow(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    resetCreateProject();
    document.getElementById("actorPrepModal").classList.add("show");
}

async function submitActorPrep(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    const role = (document.getElementById("actorRoleInput").value || "").trim();
    const movieTitle = (document.getElementById("actorPrepMovieTitle")?.value || "").trim();
    const fileInput = document.getElementById("actorPrepFile");
    const file = fileInput && fileInput.files && fileInput.files.length ? fileInput.files[0] : null;

    if (!role){
        showInfoModal("Actor Preparation", "Please enter the role you are preparing.");
        return;
    }

    if (!file){
        showInfoModal("Actor Preparation", "Please choose a script before continuing.");
        return;
    }

    closeModal("actorPrepModal");
    document.getElementById("buildProgressTitle").textContent = "Analyzing Your Sides";
    document.getElementById("buildProgressCopy").textContent = "The Developum AI Engine is breaking down your script. This takes about 30–60 seconds.";
    document.getElementById("buildProgressStage").textContent = "Analyzing sides with Developum AI Engine…";
    document.getElementById("buildProgressFill").style.width = "15%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    document.getElementById("buildProgressModal").classList.add("show");

    const formData = new FormData();
    formData.append("character_name", role);
    if (movieTitle) formData.append("movie_title", movieTitle);
    formData.append("script", file);

    try {
        const response = await fetch("/actor-prep-pass", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (response.status === 422 && data.needs_paste){
            closeBuildProgressModal();
            document.getElementById("actorPrepPasteModal").classList.add("show");
            return;
        }

        if (!response.ok){
            document.getElementById("buildProgressWorking").style.display = "none";
            document.getElementById("buildProgressTitle").textContent = "Analysis Failed";
            document.getElementById("buildProgressCopy").textContent = data.error || "Actor preparation failed. Please try again.";
            const actionsEl = document.getElementById("buildProgressActions");
            actionsEl.style.display = "flex";
            actionsEl.querySelector("button").textContent = "Close";
            actionsEl.querySelector("button").onclick = closeBuildProgressModal;
            return;
        }

        document.getElementById("buildProgressFill").style.width = "100%";
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Audition Analysis Complete";
        document.getElementById("buildProgressCopy").textContent = "Your preparation packet is ready.";
        const actionsEl = document.getElementById("buildProgressActions");
        actionsEl.style.display = "flex";
        actionsEl.querySelector("button").textContent = "View Results";
        actionsEl.querySelector("button").onclick = () => {
            closeBuildProgressModal();
            document.getElementById("actorPrepSummaryCopy").textContent = data.summary_note || "Your actor preparation packet is ready.";
            document.getElementById("actorPrepCompleteModal").classList.add("show");
        };
    } catch (err) {
        stopProgressCreep();
        closeBuildProgressModal();
        showInfoModal("Actor Preparation", "Actor preparation failed. Please try again.");
    }
}

async function submitActorPrepPaste(){
    const role = (document.getElementById("actorRoleInput").value || "").trim();
    const pastedText = (document.getElementById("actorPrepPasteText").value || "").trim();

    if (!role){
        showInfoModal("Actor Preparation", "Please enter the role you are preparing.");
        return;
    }

    if (!pastedText){
        showInfoModal("Actor Preparation", "Please paste the script text to continue.");
        return;
    }

    const formData = new FormData();
    formData.append("character_name", role);
    formData.append("script_text", pastedText);

    try {
        const response = await fetch("/actor-prep-pass", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok){
            showInfoModal("Actor Preparation", data.error || "Actor preparation failed.");
            return;
        }

        document.getElementById("actorPrepSummaryCopy").textContent = data.summary_note || "Your actor preparation packet is ready.";
        closeModal("actorPrepPasteModal");
        document.getElementById("actorPrepCompleteModal").classList.add("show");
    } catch (err) {
        showInfoModal("Actor Preparation", "Actor preparation failed. Please try again.");
    }
}
// ===== JAVASCRIPT: ACTOR PREP FLOW END ================


// ===== JAVASCRIPT: ACTOR BOOKED FLOW START ==============
function startActorBookedFlow(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    resetCreateProject();
    document.getElementById("actorBookedModal").classList.add("show");
}

async function submitActorBooked(){
    if (typeof userLoggedIn !== "undefined" && !userLoggedIn) { openPricingModal(); return; }
    const role = (document.getElementById("actorBookedRoleInput").value || "").trim();
    const movieTitle = (document.getElementById("actorBookedMovieTitle")?.value || "").trim();
    const fileInput = document.getElementById("actorBookedFile");
    const file = fileInput && fileInput.files && fileInput.files.length ? fileInput.files[0] : null;

    const roleErr = document.getElementById("actorBookedRoleError");
    if (!role){
        if (roleErr) { roleErr.style.display = "block"; }
        document.getElementById("actorBookedRoleInput").focus();
        return;
    }
    if (roleErr) roleErr.style.display = "none";

    if (!file){
        showInfoModal("Booked Role Analyzer", "Please choose a script before continuing.");
        return;
    }

    closeModal("actorBookedModal");
    document.getElementById("buildProgressTitle").textContent = "Analyzing Your Role";
    document.getElementById("buildProgressCopy").textContent = "The Developum AI Engine is building your character breakdown. This takes about 30–60 seconds.";
    document.getElementById("buildProgressStage").textContent = "Analyzing full script with Developum AI Engine…";
    document.getElementById("buildProgressFill").style.width = "15%";
    document.getElementById("buildProgressWorking").style.display = "block";
    document.getElementById("buildProgressActions").style.display = "none";
    document.getElementById("buildProgressModal").classList.add("show");

    const formData = new FormData();
    formData.append("character_name", role);
    if (movieTitle) formData.append("movie_title", movieTitle);
    formData.append("script", file);

    try {
        const response = await fetch("/actor-booked-pass", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (response.status === 422 && data.needs_paste){
            closeBuildProgressModal();
            document.getElementById("actorBookedPasteModal").classList.add("show");
            return;
        }

        if (!response.ok){
            document.getElementById("buildProgressWorking").style.display = "none";
            document.getElementById("buildProgressTitle").textContent = "Analysis Failed";
            document.getElementById("buildProgressCopy").textContent = data.error || "Booked role analysis failed. Please try again.";
            const actionsEl = document.getElementById("buildProgressActions");
            actionsEl.style.display = "flex";
            actionsEl.querySelector("button").textContent = "Close";
            actionsEl.querySelector("button").onclick = closeBuildProgressModal;
            return;
        }

        document.getElementById("buildProgressFill").style.width = "100%";
        document.getElementById("buildProgressWorking").style.display = "none";
        document.getElementById("buildProgressTitle").textContent = "Role Analysis Complete";
        document.getElementById("buildProgressCopy").textContent = "Your character breakdown is ready.";
        const actionsEl = document.getElementById("buildProgressActions");
        actionsEl.style.display = "flex";
        actionsEl.querySelector("button").textContent = "View Results";
        actionsEl.querySelector("button").onclick = () => {
            closeBuildProgressModal();
            document.getElementById("actorBookedSummaryCopy").textContent = data.summary_note || "Your booked role preparation packet is ready.";
            document.getElementById("actorBookedCompleteModal").classList.add("show");
        };
    } catch (err) {
        stopProgressCreep();
        closeBuildProgressModal();
        showInfoModal("Booked Role Analyzer", "Booked role analysis failed. Please try again.");
    }
}

async function submitActorBookedPaste(){
    const role = (document.getElementById("actorBookedRoleInput").value || "").trim();
    const pastedText = (document.getElementById("actorBookedPasteText").value || "").trim();

    if (!role){
        showInfoModal("Booked Role Analyzer", "Please enter the role you booked.");
        return;
    }

    if (!pastedText){
        showInfoModal("Booked Role Analyzer", "Please paste the script text to continue.");
        return;
    }

    const formData = new FormData();
    formData.append("character_name", role);
    formData.append("script_text", pastedText);

    try {
        const response = await fetch("/actor-booked-pass", {
            method: "POST",
            body: formData
        });
        const data = await response.json();

        if (!response.ok){
            showInfoModal("Booked Role Analyzer", data.error || "Booked role analysis failed.");
            return;
        }

        document.getElementById("actorBookedSummaryCopy").textContent = data.summary_note || "Your booked role preparation packet is ready.";
        closeModal("actorBookedPasteModal");
        document.getElementById("actorBookedCompleteModal").classList.add("show");
    } catch (err) {
        showInfoModal("Booked Role Analyzer", "Booked role analysis failed. Please try again.");
    }
}
// ===== JAVASCRIPT: ACTOR BOOKED FLOW END ================


function updateStatusUI(status){
    const inlineStatusEl = document.getElementById("inlineStatusValue");
    const inlineStageEl = document.getElementById("inlineStageValue");
    const previousStatus = lastStatus;

    lastStatus = status;

    const progress = document.getElementById("progressFill");
    if (status === "UPLOADED") progress.style.width = "20%";
    if (status === "ANALYZING" || status === "running") progress.style.width = "50%";
    if (status === "BUILDING") progress.style.width = "85%";
    if (status === "COMPLETE") progress.style.width = "100%";

    const activeStatuses = ["UPLOADED", "ANALYZING", "BUILDING", "DEMO_RUNNING"];
    if (activeStatuses.includes(status)) startTimer();

    if (status === "IDLE"){
        resetTimer();
        inlineStageEl.textContent = "Awaiting input...";
        document.body.classList.remove("complete-mode");
    } else if (status === "UPLOADED"){
        inlineStatusEl.textContent = "UPLOADED • 00:00";
        inlineStageEl.textContent = "Preparing engine";
    } else if (status === "ANALYZING" || status === "running"){
        inlineStageEl.textContent = "Analyzing script";
        updateBuildProgressModal("ANALYZING");
    } else if (status === "BUILDING"){
        inlineStageEl.textContent = "Finalizing deck...";
        updateBuildProgressModal("BUILDING");
    } else if (status === "DEMO_RUNNING"){
        inlineStageEl.textContent = "Preparing engine";
    } else if (status === "COMPLETE"){
        updateBuildProgressModal("COMPLETE");
        stopTimer();
        stopQuoteRotation();
        buildInFlight = false;
        document.body.classList.add("complete-mode");
        syncTrackDeckDone();
        document.getElementById("buildProgressBar").style.display = "none";
        document.getElementById("liveProcessLog").style.display = "none";
        document.getElementById("buildCopy").style.display = "none";
        document.getElementById("buildMeta").style.display = "none";
        document.getElementById("completePanel").style.display = "block";

        if (activeCompleteView === "refine") {
            document.getElementById("previewStage").style.display = "none";
            document.getElementById("refinementStage").style.display = "block";
            if (previousStatus !== "COMPLETE" || !latestSlidesLoadedForComplete) {
                syncLatestSlidesForPreview().then(() => {
                    renderCurrentRefineSlide();
                });
            }
        } else {
            document.getElementById("previewStage").style.display = "block";
            document.getElementById("refinementStage").style.display = "none";
            if (previousStatus !== "COMPLETE" || !latestSlidesLoadedForComplete) {
                syncLatestSlidesForPreview();
            }
            if (previousStatus !== "COMPLETE") fetchMyProjects();
        }
    } else if (status === "ERROR"){
        updateBuildProgressModal("ERROR");
        stopTimer();
        buildInFlight = false;
        inlineStageEl.textContent = "Check terminal / backend";
        document.body.classList.remove("complete-mode");
        document.getElementById("liveProcessLog").style.display = "block";
        document.getElementById("buildCopy").style.display = "block";
        document.getElementById("buildMeta").style.display = "flex";
        document.getElementById("completePanel").style.display = "none";
    } else {
        inlineStageEl.textContent = "Processing";
        document.body.classList.remove("complete-mode");
    }
    updateProgressForStatus(status);
    renderLiveProcessLog(status);
}

async function pollStatus(){
    try {
        const response = await fetch("/status", { cache: "no-store" });
        if (!response.ok) return;
        const data = await response.json();

        if (data && data.status) {
            if (buildInFlight && !sawFreshBuildStatus) {
                if (data.status === "ANALYZING" || data.status === "BUILDING" || data.status === "running") {
                    sawFreshBuildStatus = true;
                } else if (data.status === "COMPLETE" || data.status === "ERROR") {
                    // Server was single-threaded — we never saw ANALYZING/BUILDING,
                    // but the build finished. Accept it.
                    sawFreshBuildStatus = true;
                } else {
                    return;
                }
            }
            if (!buildInFlight && data.status === "COMPLETE") return;
            if (data.status === "COMPLETE" && data.project_id) {
                activeLoadedProjectId = data.project_id;
            }
            updateStatusUI(data.status);
        }
    } catch (e) {}
}

refineSlides = fallbackSlides.map((slide, index) => normalizeSlideForRefine(slide, index));
renderDeckPreview();
renderCurrentRefineSlide();

updateStatusUI("IDLE");


// ===== PER-SLIDE IMAGE UPLOAD =================================

async function handleSlideImageUpload(input) {
    const file = input.files[0];
    if (!file) return;
    const nameEl = document.getElementById("slideImageUploadName");
    if (nameEl) nameEl.textContent = "Uploading...";

    const formData = new FormData();
    formData.append("image", file);
    try {
        const res = await fetch("/upload-slide-image", { method: "POST", body: formData });
        const data = await res.json();
        if (data.ok) {
            slideCustomImages[currentRefineSlide] = { path: data.path, url: data.url };
            if (refineSlides[currentRefineSlide]) {
                refineSlides[currentRefineSlide].image_path = data.path;
            }
            const img = document.getElementById("refineSlideImage");
            if (img) img.src = data.url;
            if (nameEl) nameEl.textContent = file.name;
        } else {
            if (nameEl) nameEl.textContent = "Upload failed";
        }
    } catch(e) {
        if (nameEl) nameEl.textContent = "Upload failed";
    }
    input.value = "";
}
// ===== PER-SLIDE IMAGE UPLOAD END ============================

// ===== MY PROJECTS PANEL =====================================
let activeLoadedProjectId = null;
let _cachedProjects = [];

async function fetchMyProjects() {
    const panel = document.getElementById("projectsList");
    if (!panel) return;
    try {
        const res = await fetch("/my-projects", { cache: "no-store" });
        if (!res.ok) { renderProjectsList([]); return; }
        const data = await res.json();
        _cachedProjects = data.projects || [];
        renderProjectsList(_cachedProjects);
    } catch(e) {
        renderProjectsList([]);
    }
}

function renderProjectsList(projects) {
    const panel = document.getElementById("projectsList");
    if (!panel) return;
    if (!projects.length) {
        panel.innerHTML = '<div style="color:#444; font-size:11px;">No saved projects yet.</div>';
        return;
    }
    panel.innerHTML = projects.map(p => `
        <div class="proj-list-item${activeLoadedProjectId === p.id ? ' active' : ''}" onclick="loadProjectFromPanel('${p.id}')">
            ${p.thumbnail ? `<img class="proj-thumb" src="${p.thumbnail}" alt="">` : '<div class="proj-thumb-empty"></div>'}
            <span class="proj-list-title">${escapeHtml(p.title)}</span>
            ${p.has_deck ? '<span class="proj-list-badge">✓</span>' : ''}
            <button class="proj-list-del" onclick="event.stopPropagation(); deleteProjectFromPanel('${p.id}', '${escapeHtml(p.title)}')" title="Delete">×</button>
        </div>
    `).join('');
    // Update header title to active project name
    const active = projects.find(p => p.id === activeLoadedProjectId);
    const titleEl = document.getElementById("studioTitle");
    if (titleEl && active) titleEl.textContent = active.title;
}

async function loadProjectFromPanel(projectId) {
    if (
        activeLoadedProjectId === projectId &&
        document.body.classList.contains("complete-mode")
    ) {
        return;
    }

    try {
        const res = await fetch(`/project/${projectId}/load`, { method: "POST" });
        const data = await res.json();

        if (data.ok) {
            activeLoadedProjectId = projectId;
            activeCompleteView = "preview";
            currentRefineSlide = 0;

            const p = _cachedProjects.find(x => x.id === projectId);
            const titleEl = document.getElementById("studioTitle");
            if (titleEl && p) titleEl.textContent = p.title;

            // Enter studio mode from any page state (landing, flow, etc.)
            exitFlowMode();
            enterActiveBuildMode();

            // Hide home cards so analyzerPanel has the full space
            const homeCardGrid = document.querySelector(".home-card-grid");
            const choicesRow = document.querySelector(".choices-row");
            if (homeCardGrid) homeCardGrid.style.display = "none";
            if (choicesRow) choicesRow.style.display = "none";

            // Show analyzerPanel (it defaults to display:none)
            document.getElementById("analyzerPanel").style.display = "block";

            // Switch to complete/preview state
            document.body.classList.add("complete-mode");
            document.getElementById("buildProgressBar").style.display = "none";
            document.getElementById("liveProcessLog").style.display = "none";
            document.getElementById("buildCopy").style.display = "none";
            document.getElementById("buildMeta").style.display = "none";
            document.getElementById("completePanel").style.display = "block";
            document.getElementById("previewStage").style.display = "block";
            document.getElementById("refinementStage").style.display = "none";

            latestSlidesLoadedForComplete = false;
            await syncLatestSlidesForPreview();
            renderProjectsList(_cachedProjects);
        }
    } catch (e) {}
}


function resetWelcomeModal() {
    const choices = document.getElementById("welcomeChoices");
    const list = document.getElementById("welcomeProjectsList");
    if (choices) choices.style.display = "block";
    if (list) list.style.display = "none";
}

async function openWelcomeProjectsPicker() {
    document.getElementById("welcomeChoices").style.display = "none";
    document.getElementById("welcomeProjectsList").style.display = "block";
    const itemsEl = document.getElementById("welcomeProjectsItems");
    itemsEl.innerHTML = '<div style="color:#aaa; font-size:13px; padding:8px 0;">Loading...</div>';
    try {
        const res = await fetch("/my-projects", { cache: "no-store" });
        const data = await res.json();
        _cachedProjects = data.projects || [];
        renderWelcomeProjects(_cachedProjects);
    } catch(e) {
        itemsEl.innerHTML = '<div style="color:#aaa; font-size:13px;">Could not load projects.</div>';
    }
}

function renderWelcomeProjects(projects) {
    const el = document.getElementById("welcomeProjectsItems");
    if (!el) return;

    if (!projects || !projects.length) {
        el.innerHTML = '<div style="color:#aaa; font-size:13px; padding:8px 0;">No saved projects yet.</div>';
        return;
    }

    el.innerHTML = projects.map(p => `
        <div class="proj-list-item" onclick="selectWelcomeProject('${p.id}')">
            ${p.thumbnail ? `<img class="proj-thumb" src="${p.thumbnail}" alt="">` : '<div class="proj-thumb-empty"></div>'}
            <span class="proj-list-title">${escapeHtml(p.title)}</span>
            ${p.has_deck ? '<span class="proj-list-badge">✓</span>' : ''}
        </div>
    `).join('');
}

async function selectWelcomeProject(projectId) {
    closeModal('welcomeModal');
    resetWelcomeModal();

    setTimeout(async () => {
        await loadProjectFromPanel(projectId);
    }, 150);
}


async function deleteProjectFromPanel(projectId, title) {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
        const res = await fetch(`/project/${projectId}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.ok) {
            _cachedProjects = _cachedProjects.filter(p => p.id !== projectId);
            if (activeLoadedProjectId === projectId) activeLoadedProjectId = null;
            renderProjectsList(_cachedProjects);
            renderLimitProjectsList(_cachedProjects);
        }
    } catch(e) {}
}

async function showProjectLimitModal() {
    closeAllModals();
    document.getElementById("projectLimitModal").classList.add("show");
    const listEl = document.getElementById("limitProjectsList");
    listEl.innerHTML = '<div style="color:#aaa; font-size:12px;">Loading your projects…</div>';
    try {
        const res = await fetch("/my-projects", { cache: "no-store" });
        const data = await res.json();
        _cachedProjects = data.projects || [];
        renderLimitProjectsList(_cachedProjects);
    } catch(e) {
        listEl.innerHTML = '<div style="color:#aaa; font-size:12px;">Could not load projects.</div>';
    }
}

function renderLimitProjectsList(projects) {
    const listEl = document.getElementById("limitProjectsList");
    if (!listEl) return;
    if (!projects.length) {
        listEl.innerHTML = '<div style="color:#aaa; font-size:12px;">No projects found.</div>';
        return;
    }
    listEl.innerHTML = projects.map(p => `
        <div style="display:flex; align-items:center; gap:8px; padding:8px 10px; background:#111; border-radius:8px; border:1px solid rgba(255,255,255,0.07);">
            <span style="flex:1; font-size:13px; color:#ddd; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(p.title)}</span>
            ${p.has_deck ? '<span style="font-size:10px; color:#ff7a00; flex-shrink:0;">HAS DECK</span>' : ''}
            <button style="background:transparent; border:1px solid rgba(255,80,80,0.4); border-radius:6px; color:#ff6666; font-size:11px; padding:3px 8px; cursor:pointer; flex-shrink:0;" onclick="deleteLimitProject('${p.id}', '${escapeHtml(p.title)}')">Delete</button>
        </div>
    `).join('');
}

async function deleteLimitProject(projectId, title) {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return;
    try {
        const res = await fetch(`/project/${projectId}/delete`, { method: "POST" });
        const data = await res.json();
        if (data.ok) {
            _cachedProjects = _cachedProjects.filter(p => p.id !== projectId);
            if (activeLoadedProjectId === projectId) activeLoadedProjectId = null;
            renderProjectsList(_cachedProjects);
            renderLimitProjectsList(_cachedProjects);
        }
    } catch(e) {}
}
// ===== MY PROJECTS PANEL END ==================================

setInterval(pollStatus, 1200);
pollStatus();

// Post-login welcome modal
(function () {
    const params = new URLSearchParams(window.location.search);
    const welcome = params.get("welcome");
    if (!welcome) return;
    history.replaceState({}, "", "/");
    const heading = document.getElementById("welcomeModalHeading");
    const sub = document.getElementById("welcomeModalSubtext");
    const userName = (document.querySelector(".top-nav-item[style*='cursor:default']") || {}).textContent || "";
    const firstName = userName.split(" ")[0].trim();
    if (welcome === "new") {
        if (heading) heading.textContent = "Welcome to EVOLUM" + (firstName && firstName !== "Account" ? ", " + firstName : "") + "!";
        if (sub) sub.textContent = "You're in. What would you like to do first?";
    } else {
        if (heading) heading.textContent = "Welcome back" + (firstName && firstName !== "Account" ? ", " + firstName : "") + "!";
        if (sub) sub.textContent = "Pick up where you left off or start something new.";
    }
    document.getElementById("welcomeModal").classList.add("show");
})();

// ===== SYNC AI ASSISTANT ==============================

const _syncState = {
    open: false,
    history: [],          // [{role, text}]
    unread: 0,
    regenCount: 0,
    refineEntered: null,
    deckCompleted: false,
    tipsShown: new Set(),
    busy: false,
};

const _SYNC_PROACTIVE_TIPS = [
    {
        id: "regen3",
        trigger: () => _syncState.regenCount >= 3 && !_syncState.tipsShown.has("regen3"),
        prompt: "The user has regenerated their entire deck 3 or more times in a row. Gently suggest they try editing individual slides in the Refine view instead of regenerating the full deck, since it's faster and gives more control. Keep it to 2 sentences.",
    },
    {
        id: "refineIdle",
        trigger: () => _syncState.refineEntered && (Date.now() - _syncState.refineEntered > 180000) && !_syncState.tipsShown.has("refineIdle"),
        prompt: "The user has been in the Refine view for 3+ minutes. Remind them to hit 'Update & Rebuild' to save their edits to the actual deck file, since edits aren't saved until they rebuild. One sentence.",
    },
    {
        id: "deckDone",
        trigger: () => _syncState.deckCompleted && !_syncState.tipsShown.has("deckDone"),
        prompt: "The user just finished building their first pitch deck — congratulate them briefly and mention that EVOLUM's Writer's Room plan lets them bring in collaborators and manage up to 10 projects, in case they're working with a team. Keep it warm and under 2 sentences. Don't be pushy.",
    },
    {
        id: "upgradeNudge",
        trigger: () => _syncState.regenCount >= 2 && _syncState.deckCompleted && !_syncState.tipsShown.has("upgradeNudge"),
        prompt: "The user has built a deck and run multiple regenerations — they're clearly invested in the tool. Casually mention that the Writer's Room plan gives them more projects and collaboration features if they're working with others. One sentence, no hard sell.",
    },
];

function _syncGetContext() {
    return {
        status: lastStatus || "IDLE",
        has_deck: document.body.classList.contains("complete-mode"),
        in_refine: activeCompleteView === "refine",
        regen_count: _syncState.regenCount,
    };
}

function _syncShowBadge() {
    const badge = document.getElementById("syncBadge");
    if (badge) badge.classList.add("show");
}

function _syncClearBadge() {
    const badge = document.getElementById("syncBadge");
    if (badge) badge.classList.remove("show");
    _syncState.unread = 0;
}

function _syncAppendBubble(role, text) {
    const el = document.getElementById("syncMessages");
    if (!el) return;
    const bubble = document.createElement("div");
    bubble.className = `sync-bubble ${role}`;
    const inner = document.createElement("div");
    inner.className = "sync-bubble-text";
    inner.textContent = text;
    bubble.appendChild(inner);
    el.appendChild(bubble);
    el.scrollTop = el.scrollHeight;
    _syncState.history.push({ role, text });
}

function _syncShowTyping() {
    const el = document.getElementById("syncMessages");
    if (!el) return;
    const t = document.createElement("div");
    t.className = "sync-typing";
    t.id = "syncTyping";
    t.textContent = "Sync is thinking…";
    el.appendChild(t);
    el.scrollTop = el.scrollHeight;
}

function _syncRemoveTyping() {
    const t = document.getElementById("syncTyping");
    if (t) t.remove();
}

async function _syncFetch(message, proactiveTrigger) {
    if (_syncState.busy) return;
    _syncState.busy = true;
    const btn = document.getElementById("syncSendBtn");
    if (btn) btn.disabled = true;
    _syncShowTyping();
    try {
        const body = { context: _syncGetContext() };
        if (message) body.message = message;
        if (proactiveTrigger) body.context.proactive_trigger = proactiveTrigger;
        const res = await fetch("/sync/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        const data = await res.json();
        _syncRemoveTyping();
        _syncAppendBubble("sync", data.reply || "…");
    } catch (e) {
        _syncRemoveTyping();
        _syncAppendBubble("sync", "I'm having trouble connecting — try again in a moment.");
    } finally {
        _syncState.busy = false;
        if (btn) btn.disabled = false;
    }
}

async function _syncCheckProactive() {
    for (const tip of _SYNC_PROACTIVE_TIPS) {
        if (tip.trigger()) {
            _syncState.tipsShown.add(tip.id);
            if (_syncState.open) {
                await _syncFetch(null, tip.prompt);
            } else {
                _syncState.unread++;
                _syncShowBadge();
                // Queue it — show when user opens panel
                _syncState._pendingProactive = tip.prompt;
            }
            break;
        }
    }
}

function toggleSyncPanel() {
    _syncState.open = !_syncState.open;
    const panel = document.getElementById("syncPanel");
    if (!panel) return;
    panel.classList.toggle("open", _syncState.open);

    if (_syncState.open) {
        _syncClearBadge();
        // First open: greet
        if (_syncState.history.length === 0) {
            _syncFetch(null, "Greet the user warmly in 1-2 sentences. Tell them you're Sync, their EVOLUM studio guide, and you can help them get the best results. Be brief and friendly.");
        }
        // Pending proactive tip
        if (_syncState._pendingProactive) {
            const p = _syncState._pendingProactive;
            _syncState._pendingProactive = null;
            setTimeout(() => _syncFetch(null, p), 400);
        }
        const input = document.getElementById("syncInput");
        if (input) input.focus();
    }
}

async function sendSyncMessage() {
    const input = document.getElementById("syncInput");
    const msg = (input?.value || "").trim();
    if (!msg || _syncState.busy) return;
    input.value = "";
    _syncAppendBubble("user", msg);
    await _syncFetch(msg, null);
}

function syncInputKeydown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendSyncMessage();
    }
}

// Behavior hooks — called from submitRegenDeck, submitRefineDeck, openRefinementStage
function syncTrackRegen() {
    _syncState.regenCount++;
    _syncCheckProactive();
}

function syncTrackDeckDone() {
    if (!_syncState.deckCompleted) {
        _syncState.deckCompleted = true;
        setTimeout(_syncCheckProactive, 3000);
    }
}

function syncTrackEnterRefine() {
    if (!_syncState.refineEntered) {
        _syncState.refineEntered = Date.now();
        setTimeout(_syncCheckProactive, 180000); // check after 3 min
    }
}

// ===== SYNC AI ASSISTANT END ==========================

// ===== CTA BANNER + PRICING MODAL =====================

const _BANNER_PHRASES = [
    "Start your 3-day free trial — only $5/month",
    "Pitch decks, script analysis & actor tools — all in one place",
    "Built for writers, actors & filmmakers who move fast",
    "Cancel any time. No questions. No forms.",
    "Join the beta today — limited access available",
];
let _bannerIdx = 0;
function _rotateBannerText() {
    const el = document.getElementById("ctaBannerText");
    if (!el) return;
    el.classList.add("fade");
    setTimeout(() => {
        _bannerIdx = (_bannerIdx + 1) % _BANNER_PHRASES.length;
        el.textContent = _BANNER_PHRASES[_bannerIdx];
        el.classList.remove("fade");
    }, 380);
}
(function _initBanner() {
    if (document.getElementById("ctaBannerText")) {
        setInterval(_rotateBannerText, 4000);
    }
})();

const _PLANS = [
    {
        id: "solo", name: "Solo",
        monthly: 5, annual: 42,
        projects: "3 projects", collaborators: "1 collaborator",
        features: ["Pitch deck generator", "Script analyzer", "Actor prep tools", "3-day free trial"],
        featured: false,
    },
    {
        id: "writers-room", name: "Writer's Room",
        monthly: 15, annual: 126,
        projects: "10 projects", collaborators: "5 collaborators",
        features: ["All Solo features", "Team workspace", "Priority builds", "Project sharing"],
        featured: true, badge: "Most Popular",
    },
    {
        id: "production", name: "Production Co.",
        monthly: 35, annual: 294,
        projects: "20 projects", collaborators: "10 collaborators",
        features: ["All Writer's Room features", "Advanced analytics", "White-label exports", "Dedicated queue"],
        featured: false,
    },
    {
        id: "studio", name: "Studio",
        monthly: 75, annual: 630,
        projects: "50 projects", collaborators: "100 collaborators",
        features: ["All Production features", "Custom branding", "Dedicated support", "API access"],
        featured: false,
    },
];
let _pricingBilling = "monthly";
let _selectedPlan = null;
let _pricingModalSyncShown = false;

function setPricingBilling(mode) {
    _pricingBilling = mode;
    document.getElementById("ptogMonthly").classList.toggle("active", mode === "monthly");
    document.getElementById("ptogAnnual").classList.toggle("active", mode === "annual");
    _renderPricingCards();
}

function _renderPricingCards() {
    const container = document.getElementById("pricingCards");
    if (!container) return;
    const annual = _pricingBilling === "annual";
    container.innerHTML = _PLANS.map(p => {
        const price = annual ? Math.round(p.annual / 12) : p.monthly;
        const billedNote = annual ? `$${p.annual}/yr billed annually` : "billed monthly";
        const featured = p.featured ? " featured" : "";
        const badge = p.badge ? `<div class="plan-badge">${p.badge}</div>` : "";
        const featureList = [`<div class="plan-feature">${p.projects}</div>`,
            `<div class="plan-feature">${p.collaborators}</div>`,
            ...p.features.map(f => `<div class="plan-feature">${f}</div>`)
        ].join("");
        return `
        <div class="plan-card${featured}" id="planCard_${p.id}">
            ${badge}
            <div class="plan-name">${p.name}</div>
            <div class="plan-price"><span class="plan-price-cents">$</span>${price}</div>
            <div class="plan-period">per month</div>
            <div class="plan-billed">${annual ? billedNote : "billed monthly"}</div>
            <div class="plan-divider"></div>
            ${featureList}
            <div class="plan-cta">
                <button class="plan-btn plan-btn-primary" onclick="selectPlan('${p.id}')">Get Started</button>
            </div>
        </div>`;
    }).join("");
}

function selectPlan(planId) {
    const plan = _PLANS.find(p => p.id === planId);
    _selectedPlan = plan || null;
    const badge = document.getElementById("authPlanBadge");
    if (badge && plan) {
        const priceStr = _pricingBilling === "annual"
            ? `$${Math.round(plan.annual / 12)}/mo · billed $${plan.annual}/yr`
            : `$${plan.monthly}/month`;
        badge.textContent = `Selected plan: ${plan.name} — ${priceStr}`;
        badge.style.display = "block";
    }
    const planInput = document.getElementById("signupPlanId");
    if (planInput && plan) planInput.value = plan.id;
    const billingInput = document.getElementById("signupBillingPeriod");
    if (billingInput) billingInput.value = _pricingBilling;
    switchAuthTab("signup", document.querySelector(".auth-tab"));
    closePricingModal();
    showAuthModal();
}

function openPricingModal() {
    _pricingBilling = "monthly";
    document.getElementById("ptogMonthly")?.classList.add("active");
    document.getElementById("ptogAnnual")?.classList.remove("active");
    _renderPricingCards();
    document.getElementById("pricingModal").classList.add("open");
    document.body.style.overflow = "hidden";
    if (!_pricingModalSyncShown && !_syncState.open) {
        _pricingModalSyncShown = true;
        setTimeout(() => {
            if (!document.getElementById("pricingModal").classList.contains("open")) return;
            if (!_syncState.open) toggleSyncPanel();
            setTimeout(() => {
                _syncAppendBubble("sync", "Not sure which plan fits? Tell me what you're working on and I'll point you in the right direction.");
            }, _syncState.history.length === 0 ? 1800 : 300);
        }, 1000);
    }
}

function closePricingModal() {
    document.getElementById("pricingModal").classList.remove("open");
    document.body.style.overflow = "";
}

document.getElementById("pricingModal")?.addEventListener("click", function(e) {
    if (e.target === this) closePricingModal();
});

// ===== CTA BANNER + PRICING MODAL END =================

// ===== REFERRAL MODAL =================================

async function openReferralModal() {
    document.getElementById("referralModal").classList.add("open");
    document.body.style.overflow = "hidden";
    document.getElementById("referralCount").textContent = "—";
    document.getElementById("referralCredits").textContent = "—";
    document.getElementById("referralLinkInput").value = "Loading…";
    try {
        const res = await fetch("/api/referral-info");
        const data = await res.json();
        if (data.ok) {
            document.getElementById("referralCount").textContent = data.count;
            document.getElementById("referralCredits").textContent = data.weeks;
            document.getElementById("referralLinkInput").value = data.link;
        }
    } catch (e) {
        document.getElementById("referralLinkInput").value = "Could not load — try again.";
    }
}

function closeReferralModal() {
    document.getElementById("referralModal").classList.remove("open");
    document.body.style.overflow = "";
}

function copyReferralLink() {
    const input = document.getElementById("referralLinkInput");
    const val = input?.value;
    if (!val || val === "Loading…") return;
    navigator.clipboard.writeText(val).then(() => {
        const btn = document.querySelector(".referral-copy-btn");
        if (btn) { btn.textContent = "Copied!"; setTimeout(() => { btn.textContent = "Copy"; }, 2000); }
    }).catch(() => {
        input.select();
        document.execCommand("copy");
    });
}

document.getElementById("referralModal")?.addEventListener("click", function(e) {
    if (e.target === this) closeReferralModal();
});

// ===== REFERRAL MODAL END =============================

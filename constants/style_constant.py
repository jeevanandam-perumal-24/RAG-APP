page_style = """
<style>
#MainMenu, footer { visibility: hidden; }

header[data-testid="stHeader"] {
    background-color: #1E1E2E; /* Replace with your desired color */
}

[data-testid="stAppViewContainer"] {
    background-color: #1E1E2E;
    user-select: none;
}

[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128,128,128,.18);
    background-color: #1E1E2E;
    user-select: none;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1rem;
    background-color: #1E1E2E;
    user-select: none;
}

[data-testid="stSidebarNav"] {
    padding-top: 20px;
}

[data-testid="stSidebarNav"] a {
    border-radius: 8px;
    padding: 10px 12px;
    margin: 4px 8px;
    transition: background-color 0.2s ease;
}

[data-testid="stSidebarNav"] a:hover {
    background-color: #2a2b32;
}

[data-testid="stSidebarNav"] a[aria-current="page"] {
    background-color: #2E3440;
    font-weight: 600;
}

[data-testid="stSidebarNav"] a[aria-current="page"] span {
    color: #ECEFF4 !important;
}

[data-testid="stFileUploader"] {
    background-color: #1e1e1e;
    padding: 15px;
    border-radius: 12px;
    border: 3px solid #444;
    user-select: none;
}

.no-cursor {
    user-select: none;
}

.full-line {
    position: fixed;
    top: 45px;
    left: 0;
    width: 100vw;
    border-top: 1px solid #444;
    z-index: 999;
}

[data-testid="stChatInputContainer"] {
    background-color: #1E1E2E !important;
    border-radius: 10px;
}

[data-testid="stChatInputContainer"] textarea {
    background-color: #1E1E2E !important;
    color: #ECEFF4;
}

[data-testid="stChatInputContainer"] button {
    background-color: #5E81AC;
    color: white;
}

[data-testid="stChatInputContainer"] button:hover {
    background-color: #81A1C1;
}
</style>"""
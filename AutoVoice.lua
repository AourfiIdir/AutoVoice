-- ============================================================
-- AutoVoice.lua  (Launcher)
--
-- This file is cached by DaVinci Resolve.  It does NOT contain
-- server logic.  It simply loads and runs the real code from
-- disk via dofile(), which always reads the latest version.
-- ============================================================

local PROJECT_DIR =
    [[C:\Users\omen1\Desktop\autoVoice]]

local SERVER_SCRIPT =
    PROJECT_DIR ..
    "\\modules\\autovoice_server.lua"

print("[AutoVoice] Loading server from: " .. SERVER_SCRIPT)

dofile(SERVER_SCRIPT)

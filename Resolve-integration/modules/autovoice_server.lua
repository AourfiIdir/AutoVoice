-- ============================================================
-- autovoice_server.lua
-- Loaded fresh via dofile() on every script run.
-- ============================================================

local SERVER_VERSION = "0.7.0"

local HOST = "127.0.0.1"
local BASE_PORT = 56132

local MODULES_DIR =
    [[C:\Users\omen1\Desktop\autoVoice\Resolve-integration\modules]]

local PROJECT_DIR =
    [[C:\Users\omen1\Desktop\autoVoice]]


package.path =
    package.path ..
    ";" ..
    MODULES_DIR ..
    "\\?.lua"

local socket = require("ljsocket")
local json = require("dkjson")


local function log(message)
    print("[AutoVoice] " .. tostring(message))
end


-- ============================================================
-- RESOLVE
-- ============================================================

local function get_resolve()
    if resolve then return resolve end
    if bmd and bmd.scriptapp then
        local r = bmd.scriptapp("Resolve")
        if r then return r end
    end
    return nil
end


local function get_project()
    local r = get_resolve()
    if not r then return nil, "Could not connect to DaVinci Resolve" end
    local pm = r:GetProjectManager()
    if not pm then return nil, "Could not access Project Manager" end
    local p = pm:GetCurrentProject()
    if not p then return nil, "No project is currently open" end
    return p
end


local function get_timeline()
    local p, e = get_project()
    if not p then return nil, e end
    local t = p:GetCurrentTimeline()
    if not t then return nil, "No timeline is currently open" end
    return t
end


local function get_timeline_info()
    local t, e = get_timeline()
    if not t then return nil, e end
    local fps = t:GetSetting("timelineFrameRate")
    return {
        name = t:GetName(),
        fps = tonumber(fps) or 0,
        startFrame = t:GetStartFrame(),
        endFrame = t:GetEndFrame()
    }
end


local function get_subtitles(track_index)
    local t, e = get_timeline()
    if not t then return nil, e end
    track_index = track_index or 1
    local items = t:GetItemListInTrack("subtitle", track_index)
    if not items then
        return nil, "No subtitle items found on track " .. tostring(track_index)
    end
    local subs = {}
    for i, item in ipairs(items) do
        subs[i] = {
            index = i,
            name = item:GetName(),
            startFrame = item:GetStart(),
            endFrame = item:GetEnd(),
            duration = item:GetDuration()
        }
    end
    return { trackIndex = track_index, count = #subtitles, subtitles = subs }
end


local function parse_duration_to_frames(duration_str, fps)
    if not duration_str or fps == 0 then return 1 end
    local h, m, s, f = string.match(duration_str, "(%d+):(%d+):(%d+):(%d+)")
    if not h then
        local sec = tonumber(duration_str)
        if sec then return math.floor(sec * fps + 0.5) end
        return 1
    end
    return math.floor(((h * 3600 + m * 60 + s) * fps) + f + 0.5)
end


local function import_and_place_audio(params)
    local t, e = get_timeline()
    if not t then return nil, e end
    local p, pe = get_project()
    if not p then return nil, pe end
    local mp = p:GetMediaPool()
    if not mp then return nil, "Could not access Media Pool" end

    local fps = tonumber(t:GetSetting("timelineFrameRate")) or 24
    local files = params.files or {}
    local track = params.trackIndex or 2

    log("PlaceAudioOnTimeline: " .. #files .. " files, track " .. tostring(track) .. ", fps=" .. tostring(fps))

    local root = mp:GetRootFolder()
    local folder = mp:AddSubFolder(root, "AutoVoice")
    if not folder then
        log("Could not create AutoVoice folder, using root")
        folder = root
    end

    local track_count = t:GetTrackCount("audio")
    log("Audio tracks on timeline: " .. tostring(track_count))
    local new_track = track_count + 1
    t:AddTrack("audio")
    log("Created audio track " .. tostring(new_track) .. " for AutoVoice")
    track = new_track

    local imported = {}
    for _, path in ipairs(files) do
        local items = mp:ImportMedia({path})
        if items and #items > 0 then
            table.insert(imported, items[1])
        else
            log("FAILED to import: " .. path)
        end
    end

    if #imported == 0 then
        return nil, "No audio files could be imported"
    end

    log("Imported " .. #imported .. "/" .. #files .. " files")

    local clip_info_list = {}
    local pos = t:GetStartFrame() or 0
    for i, clip in ipairs(imported) do
        local frames = tonumber(clip:GetClipProperty("Frames")) or 0
        local dur_raw = clip:GetClipProperty("Duration")
        if frames == 0 and dur_raw then
            frames = parse_duration_to_frames(dur_raw, fps)
        end
        if frames == 0 then
            local dur = clip:GetClipProperty("Length")
            frames = tonumber(dur) or 0
        end
        if frames == 0 then frames = math.floor(fps * 3) end

        log("Clip " .. i .. ": " .. tostring(frames) .. " frames, recordFrame=" .. tostring(pos) .. ", Duration=" .. tostring(dur_raw))
        table.insert(clip_info_list, {
            mediaPoolItem = clip,
            startFrame = 0,
            endFrame = frames,
            mediaType = 2,
            trackIndex = track,
            recordFrame = pos
        })
        pos = pos + frames
    end

    log("Appending " .. #clip_info_list .. " clips to timeline on track " .. tostring(track) .. "...")
    local placed = mp:AppendToTimeline(clip_info_list)
    log("Placed: " .. tostring(placed and #placed or 0) .. " clips")

    if placed and #placed > 0 then
        for i, item in ipairs(placed) do
            log("  Placed[" .. i .. "]: start=" .. tostring(item:GetStart()) .. " end=" .. tostring(item:GetEnd()) .. " dur=" .. tostring(item:GetDuration()))
        end
    end

    return {
        ok = true,
        imported = #imported,
        placed = placed and #placed or 0
    }
end


-- ============================================================
-- API HANDLERS
-- ============================================================

local quit_server = false

local function handle_request(data)
    if not data then
        return { ok = false, error = "Invalid JSON request" }
    end

    local func = tostring(data.func or "")
    log("Request: [" .. func .. "]")
    local f = func

    if f == "Ping" or string.find(f, "Ping", 1, true) == 1 then
        return { ok = true, service = "AutoVoice", version = SERVER_VERSION }

    elseif f == "Shutdown" or string.find(f, "Shutdown", 1, true) == 1 then
        log("Shutdown requested.")
        quit_server = true
        return { ok = true, message = "Shutting down" }

    elseif f == "GetTimelineInfo" or string.find(f, "GetTimelineInfo", 1, true) == 1 then
        local info, err = get_timeline_info()
        if not info then return { ok = false, error = err } end
        return { ok = true, timeline = info }

    elseif f == "GetSubtitles" or string.find(f, "GetSubtitles", 1, true) == 1 then
        local track = data and data.trackIndex or 1
        local subs, err = get_subtitles(track)
        if not subs then return { ok = false, error = err } end
        return { ok = true, subtitles = subs }

    elseif f == "PlaceAudioOnTimeline" or string.find(f, "PlaceAudioOnTimeline", 1, true) == 1 then
        if not data then return { ok = false, error = "No audio data provided" } end
        local result, err = import_and_place_audio(data)
        if not result then return { ok = false, error = err } end
        return result
    end

    return { ok = false, error = "Unknown function: [" .. f .. "]" }
end


-- ============================================================
-- HTTP
-- ============================================================

local function create_response(body)
    return
        "HTTP/1.1 200 OK\r\n" ..
        "Server: AutoVoice/" .. SERVER_VERSION .. "\r\n" ..
        "Content-Type: application/json\r\n" ..
        "Content-Length: " .. #body .. "\r\n" ..
        "Connection: close\r\n" ..
        "\r\n" ..
        body
end


-- ============================================================
-- KILL FILE — how new runs stop old servers
-- ============================================================

local KILL_FILE = PROJECT_DIR .. "\\autovoice_kill.txt"
local PORT_FILE = PROJECT_DIR .. "\\autovoice_port.txt"
local JOBS_FILE = PROJECT_DIR .. "\\autovoice_jobs.json"
local RESULTS_FILE = PROJECT_DIR .. "\\autovoice_results.json"
local KILL_ID = tostring(os.time()) .. "-" .. tostring(math.random(100000))


local function write_kill_signal()
    local f = io.open(KILL_FILE, "w")
    if f then
        f:write(KILL_ID)
        f:close()
    end
end


local function delete_kill_signal()
    os.remove(KILL_FILE)
end


local function check_kill_signal()
    local f = io.open(KILL_FILE, "r")
    if not f then return false end
    local content = f:read("*a")
    f:close()
    if content and content ~= KILL_ID then
        return true
    end
    return false
end


-- ============================================================
-- SERVER
-- ============================================================

local function start_server()

    log("Starting server (id=" .. KILL_ID .. ")...")

    -- Signal old server to stop.
    write_kill_signal()

    -- Wait for old server to die.
    for i = 1, 20 do
        local alive = pcall(function()
            local info = socket.find_first_address(HOST, BASE_PORT)
            local c = socket.create(info.family, info.socket_type, info.protocol)
            c:set_blocking(false)
            local ok = pcall(function() c:connect(info) end)
            pcall(function() c:close() end)
            if not ok then error("not alive") end
        end)
        if not alive then
            log("Old server gone.")
            break
        end
        local t = os.clock()
        while os.clock() - t < 0.15 do end
    end

    delete_kill_signal()


    -- Find a free port.
    local server = nil
    local bound_port = nil

    for attempt = 0, 9 do
        local port = BASE_PORT + attempt
        local info = socket.find_first_address(HOST, port)
        local s = socket.create(info.family, info.socket_type, info.protocol)
        s:set_blocking(false)
        s:set_option("nodelay", true, "tcp")
        s:set_option("reuseaddr", false)

        local ok = pcall(function() s:bind(info) end)
        if ok then
            s:listen()
            server = s
            bound_port = port
            break
        end
        pcall(function() s:close() end)
    end

    if not server then
        log("ERROR: No free port in range " .. BASE_PORT .. "-" .. (BASE_PORT + 9))
        return
    end

    -- Write port for frontend.
    local pf = io.open(PORT_FILE, "w")
    if pf then pf:write(tostring(bound_port)); pf:close() end

    log("========================================")
    log("AutoVoice server v" .. SERVER_VERSION)
    log("http://" .. HOST .. ":" .. tostring(bound_port))
    log("========================================")


    -- ----------------------------------------
    -- Main loop
    -- ----------------------------------------

    os.remove(JOBS_FILE)
    os.remove(RESULTS_FILE)

    while not quit_server do

        -- Check kill signal from a new run.
        if check_kill_signal() then
            log("Kill signal received — exiting.")
            break
        end

        -- Poll for file-based jobs (PlaceAudioOnTimeline).
        local jf = io.open(JOBS_FILE, "r")
        if jf then
            local content = jf:read("*a")
            jf:close()
            if content and #content > 0 then
                os.remove(JOBS_FILE)
                log("Job file found: " .. #content .. " bytes")
                local ok, decoded = pcall(json.decode, content)
                if ok and decoded then
                    local result = nil
                    local rerr = nil
                    local api_ok, api_res = pcall(function()
                        return handle_request(decoded)
                    end)
                    if api_ok then result = api_res else rerr = tostring(api_res) end
                    if not result then
                        result = { ok = false, error = rerr or "Unknown error" }
                    end
                    local rf = io.open(RESULTS_FILE, "w")
                    if rf then
                        rf:write(json.encode(result))
                        rf:close()
                        log("Results written: " .. tostring(result.ok))
                    end
                else
                    log("Job JSON parse error: " .. tostring(decoded))
                end
            end
        end

        local client, accept_error = server:accept()

        if client then

            local handler_ok, handler_err = pcall(function()

                local peername = client:get_peer_name()
                if not peername then
                    pcall(function() client:close() end)
                    return
                end

                client:set_blocking(false)
                if client.settimeout then client:settimeout(0) end

                local request = ""
                local attempts = 0

                while attempts < 20 do
                    local chunk, chunk_err, partial = client:receive(65536)

                    if chunk and #chunk > 0 then
                        request = request .. chunk
                        attempts = 0
                    elseif type(partial) == "string" and #partial > 0 then
                        request = request .. partial
                        attempts = 0
                    end

                    if #request > 0 then
                        local _, sep = string.find(request, "\r\n\r\n", 1, true)
                        if sep then
                            local cl = string.match(request, "[Cc]ontent%-[Ll]ength:%s*(%d+)")
                            if cl then
                                if (#request - sep) >= tonumber(cl) then break end
                            else
                                break
                            end
                        end
                    end

                    attempts = attempts + 1
                    local t = os.clock()
                    while os.clock() - t < 0.001 do end
                end

                local _, body_end = string.find(request, "\r\n\r\n", 1, true)
                local content = nil
                if body_end then
                    content = string.sub(request, body_end + 1)
                end

                log(#request .. " bytes" ..
                    (content and (", body " .. #content .. "b: " .. content) or ""))

                local data = nil
                if content and #content > 0 then
                    local ok, decoded = pcall(json.decode, content)
                    if ok then data = decoded else log("JSON error: " .. tostring(decoded)) end
                end

                local api_ok, api_result = pcall(function()
                    return handle_request(data)
                end)

                local response_data
                if api_ok then
                    response_data = api_result
                else
                    log("Handler error: " .. tostring(api_result))
                    response_data = { ok = false, error = "Server handler failed", detail = tostring(api_result) }
                end

                local response_body = json.encode(response_data)
                local response = create_response(response_body)
                local sent, send_error = client:send(response)
                if not sent then log("Send error: " .. tostring(send_error)) end

            end)

            if not handler_ok then log("Crash: " .. tostring(handler_err)) end
            pcall(function() client:close() end)

        elseif accept_error ~= "timeout" then
            log("Accept: " .. tostring(accept_error))
        end

    end

    server:close()
    os.remove(PORT_FILE)
    log("Server stopped.")
end


-- ============================================================
-- LAUNCH BACKEND + FRONTEND
-- ============================================================

local function launch_backend()
    local installed = PROJECT_DIR .. "\\backend\\autovoice-server.exe"
    local dev = PROJECT_DIR .. "\\backend\\target\\release\\autovoice-server.exe"
    local exe = installed
    local f = io.open(installed, "r")
    if not f then exe = dev else f:close() end
    log("Backend: " .. exe)
    os.execute('start "" "' .. exe .. '"')
end


local function launch_frontend()
    local installed = PROJECT_DIR .. "\\AutoVoice.exe"
    local dev_python = PROJECT_DIR .. "\\app\\venv-win\\Scripts\\python.exe"
    local dev_script = PROJECT_DIR .. "\\app\\main.py"
    local f = io.open(installed, "r")
    if f then
        f:close()
        log("Frontend: " .. installed)
        os.execute('start "" "' .. installed .. '"')
    else
        log("Frontend: " .. dev_script)
        os.execute('start "" "' .. dev_python .. '" "' .. dev_script .. '"')
    end
end


-- ============================================================
-- MAIN
-- ============================================================

local function main()
    log("========================================")
    log("AutoVoice v" .. SERVER_VERSION .. " (server)")
    log("========================================")

    local r = get_resolve()
    if not r then log("ERROR: Resolve connection failed"); return end
    log("Resolve connected")

    local p, pe = get_project()
    if not p then log("ERROR: " .. tostring(pe)); return end
    log("Project: " .. tostring(p:GetName()))

    local t, te = get_timeline()
    if not t then log("ERROR: " .. tostring(te)); return end
    log("Timeline: " .. tostring(t:GetName()))

    local info = get_timeline_info()
    if info then
        log("FPS: " .. tostring(info.fps))
        log("Frames: " .. tostring(info.startFrame) .. " -> " .. tostring(info.endFrame))
    end

    launch_backend()
    local timer = os.clock()
    while os.clock() - timer < 3 do end
    launch_frontend()

    start_server()
end


main()

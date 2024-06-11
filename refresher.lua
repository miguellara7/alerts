--[[
**
**  refresh-browser-sources.lua -- OBS Studio Lua Script for Refreshing Browser Sources
**  Copyright (c) 2021-2022 Dr. Ralf S. Engelschall <rse@engelschall.com>
**  Distributed under MIT license <https://spdx.org/licenses/MIT.html>
**
--]]

--  global OBS API
local obs = obslua

--  global context information
local ctx = {
    hotkey = obs.OBS_INVALID_HOTKEY_ID
}

--  helper function: refresh the specific browser source
local function refreshBrowserSource (source_name)
    local source = obs.obs_get_source_by_name(source_name)
    if source ~= nil then
        local source_id = obs.obs_source_get_unversioned_id(source)
        if source_id == "browser_source" then
            --  trigger the refresh functionality through its "RefreshNoCache" button property
            local properties = obs.obs_source_properties(source)
            local property = obs.obs_properties_get(properties, "refreshnocache")
            obs.obs_property_button_clicked(property, source)
            obs.obs_properties_destroy(properties)
        end
        obs.obs_source_release(source)
    end
end

--  timer callback to refresh the specific browser source every 60 seconds
local function timer_callback ()
    refreshBrowserSource("donatetc")
end

--  script hook: description displayed on script window
function script_description ()
    return [[
        <h2>Refresh Browser Source "donatetc"</h2>

        Copyright &copy; 2021-2022 <a style="color: #ffffff; text-decoration: none;"
        href="http://engelschall.com">Dr. Ralf S. Engelschall</a><br/>
        Distributed under <a style="color: #ffffff; text-decoration: none;"
        href="https://spdx.org/licenses/MIT.html">MIT license</a>

        <p>
        This script refreshes the browser source named "donatetc" every 60 seconds.
    ]]
end

--  script hook: define UI properties
function script_properties ()
    --  create new properties
    local props = obs.obs_properties_create()
    obs.obs_properties_add_button(props, "refresh_browser",
        "Refresh Browser Source \"donatetc\"", function()
            refreshBrowserSource("donatetc")
        end)
    return props
end

--  script hook: on script load
function script_load (settings)
    ctx.hotkey = obs.obs_hotkey_register_frontend(
        "refresh_browser.trigger", "Refresh Browser Source \"donatetc\"",
        function (pressed)
            if not pressed then
                return
            end
            refreshBrowserSource("donatetc")
        end
    )
    local hotkey_save_array = obs.obs_data_get_array(settings,
        "refresh_browser.trigger")
    obs.obs_hotkey_load(ctx.hotkey, hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)
    
    -- Start the timer to refresh the browser source every 60 seconds
    obs.timer_add(timer_callback, 60000)
end

--  script hook: on script save
function script_save (settings)
    local hotkey_save_array = obs.obs_hotkey_save(ctx.hotkey)
    obs.obs_data_set_array(settings,
        "refresh_browser.trigger", hotkey_save_array)
    obs.obs_data_array_release(hotkey_save_array)
end

--  script hook: on script unload
function script_unload ()
    -- Stop the timer when the script is unloaded
    obs.timer_remove(timer_callback)
end

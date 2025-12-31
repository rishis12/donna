#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use auto_launch::AutoLaunchBuilder;
use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem,
    GlobalShortcutManager, PhysicalPosition, PhysicalSize,
};

// Store normal window state for restoring
static mut NORMAL_SIZE: Option<(u32, u32)> = None;
static mut NORMAL_POSITION: Option<(i32, i32)> = None;

#[tauri::command]
fn get_autostart_enabled() -> bool {
    let auto_launch = AutoLaunchBuilder::new()
        .set_app_name("Donna")
        .set_app_path(std::env::current_exe().unwrap().to_str().unwrap())
        .build()
        .unwrap();
    auto_launch.is_enabled().unwrap_or(false)
}

#[tauri::command]
fn set_autostart_enabled(enabled: bool) -> Result<(), String> {
    let auto_launch = AutoLaunchBuilder::new()
        .set_app_name("Donna")
        .set_app_path(std::env::current_exe().unwrap().to_str().unwrap())
        .build()
        .map_err(|e| e.to_string())?;
    
    if enabled {
        auto_launch.enable().map_err(|e| e.to_string())
    } else {
        auto_launch.disable().map_err(|e| e.to_string())
    }
}

#[tauri::command]
fn enter_mini_mode(window: tauri::Window) -> Result<(), String> {
    // Save current size and position
    if let Ok(size) = window.outer_size() {
        unsafe { NORMAL_SIZE = Some((size.width, size.height)); }
    }
    if let Ok(pos) = window.outer_position() {
        unsafe { NORMAL_POSITION = Some((pos.x, pos.y)); }
    }
    
    // Get monitor info to position in bottom right
    if let Some(monitor) = window.current_monitor().ok().flatten() {
        let monitor_size = monitor.size();
        let monitor_pos = monitor.position();
        
        // Mini widget size (very compact - 50% smaller)
        let mini_width = 140u32;
        let mini_height = 100u32;
        let margin = 16i32;
        
        // Calculate bottom-right position
        let new_x = monitor_pos.x + (monitor_size.width as i32) - (mini_width as i32) - margin;
        let new_y = monitor_pos.y + (monitor_size.height as i32) - (mini_height as i32) - margin - 40; // 40 for taskbar
        
        // Apply changes
        let _ = window.set_decorations(false);
        let _ = window.set_always_on_top(true);
        let _ = window.set_size(PhysicalSize::new(mini_width, mini_height));
        let _ = window.set_position(PhysicalPosition::new(new_x, new_y));
    }
    
    Ok(())
}

#[tauri::command]
fn exit_mini_mode(window: tauri::Window) -> Result<(), String> {
    // Restore normal window
    let _ = window.set_decorations(true);
    let _ = window.set_always_on_top(false);
    
    unsafe {
        if let Some((width, height)) = NORMAL_SIZE {
            let _ = window.set_size(PhysicalSize::new(width, height));
        } else {
            let _ = window.set_size(PhysicalSize::new(520, 700));
        }
        
        if let Some((x, y)) = NORMAL_POSITION {
            let _ = window.set_position(PhysicalPosition::new(x, y));
        } else {
            let _ = window.center();
        }
    }
    
    Ok(())
}

fn main() {
    let quit = CustomMenuItem::new("quit".to_string(), "Quit");
    let show = CustomMenuItem::new("show".to_string(), "Show Window");
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            get_autostart_enabled, 
            set_autostart_enabled,
            enter_mini_mode,
            exit_mini_mode
        ])
        .system_tray(system_tray)
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::LeftClick { .. } => {
                if let Some(window) = app.get_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "quit" => std::process::exit(0),
                "show" => {
                    if let Some(window) = app.get_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                _ => {}
            },
            _ => {}
        })
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            
            // Register global shortcut (Ctrl+Shift+Space)
            let mut shortcut_manager = app.global_shortcut_manager();
            let window_clone = window.clone();
            shortcut_manager
                .register("Ctrl+Shift+Space", move || {
                    if window_clone.is_visible().unwrap_or(false) {
                        let _ = window_clone.hide();
                    } else {
                        let _ = window_clone.show();
                        let _ = window_clone.set_focus();
                    }
                })
                .expect("Failed to register global shortcut");

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

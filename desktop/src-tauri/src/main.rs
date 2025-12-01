#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{
    CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem,
    GlobalShortcutManager,
};

fn main() {
    let quit = CustomMenuItem::new("quit".to_string(), "Quit");
    let show = CustomMenuItem::new("show".to_string(), "Show Window");
    let tray_menu = SystemTrayMenu::new()
        .add_item(show)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);

    let system_tray = SystemTray::new().with_menu(tray_menu);

    tauri::Builder::default()
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


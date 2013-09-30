import sublime


def get_plugin_settings():
    setting_name = 'sublime_jedi.sublime-settings'
    plugin_settings = sublime.load_settings(setting_name)
    return plugin_settings


def get_settings_param(view, param_name, default=None):
    plugin_settings = get_plugin_settings()
    project_settings = view.settings()
    return project_settings.get(
        param_name,
        plugin_settings.get(param_name, default)
    )

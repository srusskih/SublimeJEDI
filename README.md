SublimeJEDI
============

[![Gitter](https://badges.gitter.im/Join Chat.svg)](https://gitter.im/srusskih/SublimeJEDI?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[SublimeJEDI](https://github.com/srusskih/SublimeJEDI) is a [Sublime Text 2](http://www.sublimetext.com/) and Sublime Text 3 plugin
to the awesome autocomplete library [Jedi](https://github.com/davidhalter/jedi)


Installation
------------

#### with Git

    cd ~/.config/sublime-text-2/Packages/
    git clone https://github.com/srusskih/SublimeJEDI.git "Jedi - Python autocompletion"


#### with [Sublime Package Control](http://wbond.net/sublime_packages/package_control)

 1. Open command pallet (default: `ctrl+shift+p`)
 2. Type `package control install` and select command `Package Control: Install Package`
 3. Type `jedi` and select "SublimeJEDI"

Additonal info installations you can find here [http://wbond.net/sublime_packages/package_control/usage](http://wbond.net/sublime_packages/package_control/usage)

Settings
--------

#### Python interpreter settings

By default **SublimeJEDI** will use default Python interpreter from the `PATH`.
Also you can set different interpreter for each Sublime Project.

To set project related Python interpreter you have to edit yours project config file.
By default project config name is `<project name>.sublime-project`

You can set Python interpreter, and additional python package directories, using for example the following:

    # <project name>.sublime-project
    {
        // ...

        "settings": {
            // ...
            "python_interpreter": "$project_path/../../virtual/bin/python",

            "python_package_paths": [
                "$home/.buildout/eggs",
                "$project_path/addons",
                ]
        }
    }

When setting paths, [Sublime Text Build System Variables](http://docs.sublimetext.info/en/latest/reference/build_systems.html#build-system-variables) and OS environment variables are automatically expanded.
Note that using placeholders and substitutions, like in regular Sublime Text Build System paths is not supported.


#### Autocomplete on DOT

If you want auto-completion on dot, you can define a trigger in the
Sublime User or Python preferences:

    # User/Preferences.sublime-settings or User/Python.sublime-settings
    {
        // ...
        "auto_complete_triggers": [{"selector": "source.python", "characters": "."}],
    }

If you want auto-completion ONLY on dot and not while typing, you can
set (additionally to the trigger above):


    # User/Preferences.sublime-settings or User/Python.sublime-settings
    {
        // ...
        "auto_complete_selector": "-",
    }

#### Function args fill up on completion

SublimeJEDI allow fill up function parameters by [default](sublime_jedi.sublime-settings#12). Thanks to @krya, now you can turn it off.
Function parameters completion has 3 different behavior:

  - insert all function arguments on autocomplete

        # complete result
        func(a, b, c, d=True, e=1, f=None)

        # sublime_jedi.sublime-settins
        {
            "auto_complete_function_params": "all"
        }


  - insert only required arguments that don't have default value (default behavior)

        # complete result
        func(a, b, c)

        # sublime_jedi.sublime-settins
        {
            "auto_complete_function_params": "required"
        }

  - do not insert any arguments

        # complete result
        func()

        # sublime_jedi.sublime-settins
        {
            "auto_complete_function_params": ""
        }

#### Completion visbility

Sublime Text has a bit strange completion behavior and some times does not adds it's own completion suggestions.
This option is try to bring more comfortable workflow.

 - Suggest only Jedi completion

        # sublime_jedi.sublime-settins
        {
            "sublime_completions_visibility": "jedi"
        }

   or

        # sublime_jedi.sublime-settins
        {
            "sublime_completions_visibility": "default"
        }

 - Suggest Jedi completion and Sublime completion in the end of the list

        # sublime_jedi.sublime-settins
        {
            "sublime_completions_visibility": "list"
        }

Please note, if you are using [SublimeAllAutocomplete](https://github.com/alienhard/SublimeAllAutocomplete) - you should not care about this option.


#### Jedi Goto / Go Definition

Find function / variable / class definition

Shortcuts: `CTRL+SHIFT+G`

Mouse binding, was disabled, becase it's hard to keep ST default behavior.
Now you can bind `CTRL + LeftMouseButton` by themself in this way:

    # User/Default.sublime-mousemap
    [{
        "modifiers": ["ctrl"], "button": "button1",
        "command": "sublime_jedi_goto",
        "press_command": "drag_select"
    }]


#### Jedi Find Related Names ("Find Usages")

Find function / method / variable / class usage, definition

Shortcut: `Alt+Shift+f`


#### Jedi Show Docstring

Show docstring in output panel

Exposed command is `sublime_jedi_docstring` which can be assigned to appropriate shortcut (i.e. `F1`)


#### Jedi Show Calltip

Show calltip in status bar

Exposed command is `sublime_jedi_signature`


#### Logging

To change logging level of the plugin - change `logging_level` value in settings.

Possible values: "debug", "info", "error"


    # User/sublime_jedi.sublime-settings
    {
        // ...
		"logging_level": "error"
    }

License
-------

[MIT](/LICENSE.txt)

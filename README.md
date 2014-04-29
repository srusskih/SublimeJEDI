SublimeJEDI
============

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

You can set Python interpreter, and additional python package directories, using following:

    # <project name>.sublime-project
    {
        // ...

        "settings": {
            // ...
            "python_interpreter_path": "/home/sr/.virtualenvs/django1.5/bin/python",

            "python_package_paths": [
                "/home/sr/python_packages1",
                "/home/sr/python_packages2",
                "/home/sr/python_packages3"
                ]
        }
    }

Note that the `python_interpreter_path` and `python_package_paths` should be absolute path.
If necessary you can use `$project_path` to present project's folder path.

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

SublimeJEDI allow fill up function parameters by [default](sublime_jedi.sublime-settins#12). Thanks to @krya, now you can turn it off.
Function parameters completion has 3 different behavior:

  - insert all function arguments on autocomplete (default behavior)

        # complete result
        func(a, b, c, d=True, e=1, f=None)        

        # sublime_jedi.sublime-settins
        {
            "auto_complete_function_params": "all"
        }	
    

  - insert arguments that don't have default value (e.g. required)

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

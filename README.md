SublimeJEDI
============

[SublimeJEDI](https://github.com/svaiter/SublimeJEDI) is a [Sublime Text 2](http://www.sublimetext.com/) plugin
to the awesome autocomplete library [Jedi](https://github.com/davidhalter/jedi)

**The plugin has not full functional yet !**
Join the effort to bring Jedi to Sublime (see jedi-vim).

Installation
------------

#### with Git

    cd ~/.config/sublime-text-2/Packages/
    git clone https://github.com/svaiter/SublimeJEDI.git


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
            "python_interpreter_path": "/home/sr/.virtualenvs/django1.5/bin/python"

            "python_package_paths": [
                "/home/sr/python_packages1",
                "/home/sr/python_packages2",
                "/home/sr/python_packages3"
                ]
        }
    }

#### Autocomplete on DOT

By default it's [turned on](https://github.com/svaiter/SublimeJEDI/blob/master/sublime_jedi.sublime-settings#L7)

    # sublime_jedi.sublime-settings
    {
        // ...
        "auto_complete_on_dot": true
    }

#### Jedi Goto/ Go Definition

Find function / variable / class definition
Shortcuts: `CTRL+B` or `CTRL + LeftMouseButton`


TODO
----

 - add Jedi "Related Names"
 - reduce PYTHONPATH getting overhead

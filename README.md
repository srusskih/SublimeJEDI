SublimeJEDI
============

[SublimeJEDI](https://github.com/svaiter/SublimeJEDI) is a [Sublime Text 2](http://www.sublimetext.com/) plugin
to the awesome autocomplete library [Jedi](https://github.com/davidhalter/jedi)

**The plugin has not full functional yet !**
Join the effort to bring Jedi to Sublime (see jedi-vim).


Settings
--------

#### Python interpreter settings

By default **SublimeJEDI** will use default Python interpreter from the `PATH`.
Also you can set different interpreter for each Sublime Project.

To set project related Python interpreter you have to edit yours project config file.
By default project config name is `<project name>.sublime-project`

You can set Python interpreter in this way...

    # <project name>.sublime-project`
    {
        // ...

        "settings": {
            // ...
            "python_interpreter_path": "/home/sr/.virtualenvs/django1.5/bin/python"
        }
    }

#### Autocomplete on DOT

    "auto_complete_on_dot": true


TODO
----

 - add Jedi "Go To" functionality
 - add Jedi "Get Definitions"
 - add Jedi "Related Names" (Find Usages)
 - reduce PYTHONPATH getting overhead

SublimeJEDI
============

[SublimeJEDI](https://github.com/svaiter/SublimeJEDI) is a [Sublime Text 2](http://www.sublimetext.com/) and Sublime Text 3 plugin
to the awesome autocomplete library [Jedi](https://github.com/davidhalter/jedi)


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

By default it's [turned on](sublime_jedi.sublime-settings#L10)

    # sublime_jedi.sublime-settings
    {
        // ...
        "auto_complete_on_dot": true
    }

#### Function args fill up on completion

SublimeJEDI allow fill up function parameters by [default](sublime_jedi.sublime-settins#13). Thanks to @krya, now you can turn it off.

	# sublime_jedi.sublime-settings
	{
		// ..
		"auto_complete_function_params": true
	}


#### Jedi Goto/ Go Definition

Find function / variable / class definition
Shortcuts: `CTRL+SHIFT+G` or `CTRL + LeftMouseButton`


TODO
----
 - allow use SublimeJEDI in SublimeText 3 and Sublime Text 2 [pull request](https://github.com/svaiter/SublimeJEDI/pull/18)
 - add Jedi "Related Names" (Find usages) [Jedi API info](https://jedi.readthedocs.org/en/latest/docs/plugin-api.html#api.Script.related_names). Issue #19


License
-------

GNU LGPL v3 
[full text](http://www.gnu.org/licenses/lgpl.txt)

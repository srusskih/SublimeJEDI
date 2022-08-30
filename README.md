SublimeJEDI
============

[![Build Status](https://travis-ci.com/srusskih/SublimeJEDI.svg?branch=master)](https://travis-ci.com/srusskih/SublimeJEDI) [![Gitter](https://badges.gitter.im/Join%20Chat.svg)](https://gitter.im/srusskih/SublimeJEDI?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge)

[SublimeJEDI](https://github.com/srusskih/SublimeJEDI) is a [Sublime Text 3](http://www.sublimetext.com/) and [Sublime Text 2](http://www.sublimetext.com/2) and plugin
to the awesome autocomplete library [Jedi](https://github.com/davidhalter/jedi)

Python Version Support
----------------------


| Sublime Jedi Plugin  | Branch   | Jedi version   | Python 2.6.x   | Python 2.7.x   | Python >3.3   | Python 3.3   |Sublime Text 2   | Sublime Text 3
| -------------------- | -------- | -------------- | -------------- | -------------- | ------------ | ------------ |---------------- | ----------------
| >= 0.14.0            | master   | >=0.13.2       | ❌             | ✅             | ✅           | ❌           |❌               | ✅
| >= 0.12.0            | master   | >=0.12.0       | ❌             | ✅             | ✅           | ✅           |❌               | ✅
| < 0.12.0             | st2      | 0.11.1         | ✅             | ✅             | ✅           | ✅           |✅               | ✅

_Please note [Jedi](https://github.com/davidhalter/jedi) does not support Python 3.3 any more._

Installation
------------

#### with Git

    cd ~/.config/sublime-text-2/Packages/
    git clone https://github.com/srusskih/SublimeJEDI.git "Jedi - Python autocompletion"


#### with [Sublime Package Control](http://wbond.net/sublime_packages/package_control)

 1. Open command pallet (default: `ctrl+shift+p`)
 2. Type `package control install` and select command `Package Control: Install Package`
 3. Type `Jedi` and select `Jedi - Python autocompletion`

Additional info about to use Sublime Package Control you can find here: [http://wbond.net/sublime_packages/package_control/usage](http://wbond.net/sublime_packages/package_control/usage).

Settings
--------

#### Python interpreter settings

By default **SublimeJEDI** will use default Python interpreter from the `PATH`.
Also you can set different interpreter for each Sublime Project.

To set project related Python interpreter you have to edit yours project's settings file.
By default file name look like `<project name>.sublime-project`

You can set Python interpreter, and additional python package directories, using for example the following:

    # <project name>.sublime-project
    {
        // ...

        "settings": {
            // ...
            "python_virtualenv": "$project_path/../../virtual/",
            "python_interpreter": "$project_path/../../virtual/bin/python",

            "python_package_paths": [
                "$home/.buildout/eggs",
                "$project_path/addons"
            ]
        }
    }

**NOTE**: You can configure `python_interpreter` and `python_virtualen` at the same time, no problem with that. If you configure `python_interpreter` alone, the `python_virtualen` will be inferred  so it will be 2 directories above `python_interpreter`. If you configure `python_virtualen` alone, the `python_interpreter` will be always where ever `python_virtualen` plus `'bin/python'`. If you don't configure any of this then the default Python environment of your system will be used.

**NOTE**: Please note that Python will goes through the directories from `"python_package_paths"` to search for modules and files. In other words, each item in `"python_package_paths"` list is a directory with extra packages and modules, not a direct path to package or module.

When setting paths, [Sublime Text Build System Variables](http://docs.sublimetext.info/en/latest/reference/build_systems.html#build-system-variables) and OS environment variables are automatically expanded.
Note that using placeholders and substitutions, like in regular Sublime Text Build System paths is not supported.


#### SublimeREPL integration

By default completion for [SublimeREPL](https://github.com/wuub/SublimeREPL) turned off. If you want use autocompletion feature of SublimeJEDI in a repl, 
please set `enable_in_sublime_repl: true` in `User/sublime_jedi.sublime-setting` or in your project setting.


#### Autocomplete on DOT

If you want auto-completion on dot, you can define a trigger in the
Sublime User or Python preferences:

    # User/Preferences.sublime-settings or User/Python.sublime-settings
    {
        // ...
        "auto_complete_triggers": [{"selector": "source.python", "characters": "."}],
    }

If you want auto-completion **ONLY** on dot and not while typing, you can
set (additionally to the trigger above):


    # User/Preferences.sublime-settings or User/Python.sublime-settings
    {
        // ...
        "auto_complete_selector": "-",
    }


#### Autocomplete after only certain characters

If you want Jedi auto-completion only after certain characters, you can use the `only_complete_after_regex` setting.

For example, if you want Jedi auto-completion only after the `.` character but don't want to affect auto-completion from other packages, insert the following into `User/sublime_jedi.sublime-settings`:

~~~json
{
  "only_complete_after_regex": "\\.",
}
~~~

Using this setting in this way means you can remove `"auto_complete_selector": "-",` from `User/Python.sublime-settings`, so that the rest of your packages still trigger auto-completion after every keystroke.


#### Goto / Go Definition

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

**NOTE**: You can configure the behavior of this command by changing the setting `follow_imports`. If this setting is `True` (default behavior) you will travel directly to where the term was defined or declared. If you want to travel back step by step the import path of the term then set this to `False`.

#### Find Related Names ("Find Usages")

Find function / method / variable / class usage, definition.

Shortcut: `ALT+SHIFT+F`.

There are two settings related to finding usages:

- `highlight_usages_on_select`: highlights usages of symbol in file when symbol is selected (default `false`)
- `highlight_usages_color`: color for highlighted symbols (default `"region.bluish"`)
    + other available options are `"region.redish", "region.orangish", "region.yellowish", "region.greenish", "region.bluish", "region.purplish", "region.pinkish", "region.blackish"`
    + these colors are actually scopes that were added to Sublime Text around build 3148; these scopes aren't documented, but the __BracketHighlighter__ plugin has an excellent explanation [here](http://facelessuser.github.io/BracketHighlighter/customize/#configuring-highlight-style)


#### Show Python Docstring

Show docstring as tooltip.

For ST2:
	Show docstring in output panel.

Shortcut: `CTRL+ALT+D`.


#### Styling Python Docstring

If available [mdpopups](https://github.com/facelessuser/sublime-markdown-popups) is used to display the docstring tooltips. To modify the style please follow mdpopups' [styling guide](http://facelessuser.github.io/sublime-markdown-popups/styling).

Basically a `Packages/User/mdpopups.css` is required to define your own style.

To specify rules which apply to Jedi tooltips only, use `.jedi` selector as displayed in the following example.

```css

/* JEDI's python function signature */
.jedi .highlight {
    font-size: 1.1rem;
}

/* JEDI's docstring titles
  
  h6 is used to highlight special keywords in the docstring such as

  Args:
  Return:
*/
.jedi h6 {
    font-weight: bold;
}
```

mdpopups provides a [default.css](https://github.com/facelessuser/sublime-markdown-popups/blob/master/css/default.css) which might be used as cheat sheet to learn about the available styles.


#### Jedi Show Calltip

Show calltip in status bar.

Exposed command is `sublime_jedi_signature`.


#### Function args fill up on completion

SublimeJEDI allow fill up function parameters by [default](sublime_jedi.sublime-settings#12).
Thanks to [@krya](https://github.com/krya), now you can turn it off.

Function parameters completion has 3 different behaviors:

  - insert all function arguments on autocomplete

        # complete result
        func(a, b, c, d=True, e=1, f=None)

        # sublime_jedi.sublime-settings
        {
            "auto_complete_function_params": "all"
        }


  - insert only required arguments that don't have default value (default behavior)

        # complete result
        func(a, b, c)

        # sublime_jedi.sublime-settings
        {
            "auto_complete_function_params": "required"
        }

  - do not insert any arguments

        # complete result
        func()

        # sublime_jedi.sublime-settings
        {
            "auto_complete_function_params": ""
        }
	
[More info about `auto_complete_function_params`](https://github.com/srusskih/SublimeJEDI/wiki/What-is-%22auto_complete_function_params%22)

#### Completion visibility

Sublime Text has a bit strange completion behavior and some times does not adds it's own completion suggestions.
Enabling this option to try to bring more comfortable workflow.

 - Suggest only Jedi completion

        # sublime_jedi.sublime-settings
        {
            "sublime_completions_visibility": "jedi"
        }

   or

        # sublime_jedi.sublime-settings
        {
            "sublime_completions_visibility": "default"
        }

 - Suggest Jedi completion and Sublime completion in the end of the list

        # sublime_jedi.sublime-settings
        {
            "sublime_completions_visibility": "list"
        }

Please note, if you are using [SublimeAllAutocomplete](https://github.com/alienhard/SublimeAllAutocomplete) - you should not care about this option.


#### Logging

Plugin uses Python logging lib to log everything. It allow collect propper information in right order rather then `print()`-ing to sublime console.
To make logging more usefull I'd suggest ST Plugin [Logging Control](https://packagecontrol.io/packages/Logging%20Control), it allows stream logs into file/console/etc. 
On github page you can find great documenation how you can use it.

Here is *quickstart* config that I'm using for *DEBUG* purposes:

```json
{
    "logging_enable_on_startup": false,
    "logging_use_basicConfig": false,
    "logging_root_level": "DEBUG",
    "logging_console_enabled": true,
    "logging_console_level": "INFO",     // Only print warning log messages in the console.
    "logging_file_enabled": true,
    "logging_file_level": "DEBUG",
    "logging_file_datefmt": null,
    "logging_file_fmt": "%(asctime)s %(levelname)-6s - %(name)s:%(lineno)s - %(funcName)s() - %(message)s",
    "logging_file_path": "/tmp/sublime_output.log",
    "logging_file_rotating": false,
    "logging_file_clear_on_reset": false
}
```

By default, detailed (debug) loggin turned off and you would not see any messages in ST console, only exceptions.

If you need get more information about the issue with the plugin:

1. Install [Logging Control](https://packagecontrol.io/packages/Logging%20Control)
2. Use *quickstart* config that was provided above.
3. Enable logging. Ivoke "Command Pannel" (CMD+SHIFT+P for mac) and start typing “Logging”. Select the `"Logging: Enable logging"` command to enable logging.
4. Reproduce the issue.
5. Check the log file!


Troubleshooting
---------------

#### Auto-complete for `import XXXX` does not works.

It's a common issue for ST3.
All language related settings are stored in Python Package.
There is a `Completion Rules.tmPreferences` file where defined that completion should be cancelled after a keyword (def, class, import & etc.).

To solve this issue Sublime Jedi plugin already has a proper `Completion Rules.tmPreferences` file for ST2, but ST3 ignores it.

Some workarounds how to update completion rules and fix the issue:

##### Copy-Paste

1. Delete your Sublime Text Cache file `Cache/Python/Completion Rules.tmPreferences.cache`
2. Download [Completion Rules.tmPreferences.cache](https://raw.githubusercontent.com/srusskih/SublimeJEDI/master/Completion%20Rules.tmPreferences) to `User/Packages/Python/`

##### There is package for this...

1. install Package https://packagecontrol.io/packages/PackageResourceViewer
2. cmd+shift+p (Command Panel)
3. type `PackageResourceViewer: Open Resource`
4. type `python` and select [Python package](https://www.scaler.com/topics/python/python-packages/)
5. type `Completion Rules.tmPreferences`
6. remove `import` from the regexp.
7. save


License
-------

[MIT](/LICENSE.txt)

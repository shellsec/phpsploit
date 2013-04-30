"""A generic command interpreter with multicommand support.

The cmdshell library has been initially developped to correctly handle
PhpSploit framework's shell interfaces. That being said, it was built
in order to stand generic, and usable by any other open-source project.

It extends the pretty good 'cmd' library, adding many new features, and
a little bit new behaviors.

It was built to theorically work on all 3.x python versions.
For any bug, issue or enhancement proposal, please contact the author.

NOTE: Keep in mind that the cmdshell library extends and wraps the
      `cmd` python standard library. It means that you must read
      the `cmd` documentation, in order to correctly understand
      how cmdshell works, and its new features.

NEW FEATURES:
=============

Command line interface:
  * The command line interpreter has been highly enhanced, with a
    complete overwrite of the parseline() method, to provide the
    most bash-like features as possible.
  * Multi commands, separated by semicolons can now be typed.
  * Multi line command also can be written, like on bash prompt by
    ending a line with a backslash, prompting the user to continue
    writing the command in the next line (like bash's PS2).
  * Strings can now be enquoted, to be processed as a single argument.

Command execution:
  * An argv array of arguments is now passed as do_foo() argument
    (an all other *cmd related methods) instead of the 'cmd' tuple.
  * The interpret() method can be used to eval a string as a list of
    cmdshell commands. It also can be used inside do_* commands.

Prompt feature:
  * Included an input() wrapper (classe's raw_input() method) that
    makes use of regular expressions to automatically enclose
    enventual prompt's ANSI color codes with '\\01%s\\02', fixing
    readline's prompt length missinterpretation on colored ones.
  * Since multiline commands are supported, a new variable:
    prompt_ps2 can be used to change PS2 prompt prefix.
  * EOFError raised during input() are the same as sending the
    'exit' command to the interpreter.

Exception handling:
  * The new onexception() method has been made to handle exceptions.
    It eases a lot command methods (do_foo()) development, allowing
    them to simply raise exceptions on error, that will be
    automatically handled and represented by a standard error line.
  * An exception `foo` is dispatched to a method `except_foo` if
    available; the except_ method is passed a single argument, the
    exception object itself.
  * The new variable `error` defines the error line template.

Command return values:
  * Adding support for command return values. Instead of the 'cmd'
    trivial boolean behavior, any command are now able to return
    anything. The postcmd method manages integer return values, in
    a similar way than the sys.exit's behavior.
  * The feature above also implies that error messages (if any)
    are printed into stderr, thats why self.stderr is now available
    and can be declared in __init__().
  * To leave the cmdloop() method, a SystemExit must be raised
    (with the exit() built_in function for example)

Misc behaviors:
  * Extended the get_names() method, which now can take an instance
    as argument, limiting the returned attributes to this one.
  * Unlike `cmd` lib, emptyline()'s default behavior defaultly does
    nothing instead of repeating the last typed command (bash like).
  * Typing 'EOF' to leave is not used on cmdshell, consider using
    'exit' and raise SystemExit instead.
  * The classe's default() method had been enhanced, writing command
    representation in case of unprintable chars, and also takes use of
    the new 'nocmd' variable.
  * When left, the cmdloop() methods acts exactly in the same way
    that command return values behavior, meaning that the return
    value will be an interger anyway, 0 in case of no error.

Limitations & Other changes:
  * Unlike 'cmd', the cmdshell library do not provides support for
    command line interpretation without input() built-in function.
  * Unlike 'cmd', cmdshell is NOT compatible with python 2.x.


"""

import cmd, shlex, re, sys

__author__ = "nil0x42 <http://goo.gl/kb2wf>"

class Cmd(cmd.Cmd):
    prompt = "cmdshell > "
    prompt_ps2 = "> "
    nocmd = "*** Unknow command: %s"
    error = "*** Error raised: %s"


    def __init__(self, completekey='tab', stdin=None, \
                 stdout=None, stderr=None):
        # handle new stderr manager
        if stderr is not None:
            self.stderr = stderr
        else:
            self.stderr = sys.stderr
        # explicitly run parent's __init__()
        super(Cmd, self).__init__(completekey=completekey, \
                                  stdin=stdin, stdout=stdout)


    def raw_input(self, prompt):
        """An input() wrapper that fixes readline ansi colored prompt
        length missinterpretation by wrapping terminal ansi codes as
        "ANSI" = "\\x01ANSI\\x02".

        """
        # if not readline, return prompt as it is
        try: import readline
        except: return input(prompt)

        # else, fix readline length missinterpretation
        pattern = "\x01?(\x1b\[((?:\d|;)*)([a-zA-Z]))\x02?"
        return input( re.sub(pattern, "\x01\\1\x02", prompt) )


    def cmdloop(self, intro=None):
        """Repeatedly issue a prompt, accept input, parse an initial prefix
        off the received input, and dispatch to action methods, passing them
        the remainder of the line as argument.

        """
        # try to load readline (if available)
        if self.completekey:
            try:
                import readline
                self.old_completer = readline.get_completer()
                readline.set_completer(self.complete)
                readline.parse_and_bind(self.completekey+": complete")
            except ImportError:
                pass

        # print intro message (if any)
        if intro:
            self.intro = intro
        if self.intro:
            self.stdout.write( str(self.intro)+"\n" )



        # start command loop
        try:
            self.preloop() # pre command hook method
            while True:
                try:
                    line = self.raw_input(self.prompt)
                except EOFError:
                    self.stdout.write("\n")
                    line = "exit"
                except BaseException as e:
                    # nothing to interpret on exception
                    self.onexception(e)
                    continue
                try:
                    self.interpret(line)
                # system exit is the correct way to leave loop
                except SystemExit as e:
                    return e.code

        # restore readline completer (if used)
        finally:
            if self.completekey:
                try:
                    import readline
                    readline.set_completer(self.old_completer)
                except ImportError:
                    pass
            self.postloop() # post command hook method


    def interpret(self, string):
        """Interpret the given string as commands"""
        retval = 0
        for argv in self.parseline(string):
            try:
                argv = self.precmd(argv)
                retval = self.onecmd(argv)
                retval = self.postcmd(retval, argv)
            except SystemExit as e:
                raise SystemExit(self.return_handler(e.code))
        return self.return_handler(retval)


    def postcmd(self, retval, argv):
        """Hook method executed just after a command dispatch is finished.

        """
        return retval


    def parseline(self, string):
        """Parse `string` into an ordered list of `argv`, each of them
        representing a single command's argument list.

        Example:
        >>> string = "echo -e 'foo bar'\\nls /tmp; help"
        >>> for argv in parseline(string):
        ...     print(argv)
        ...
        ...
        ["echo", "-e", "foo bar"]
        ["ls", "/tmp"]
        ["help"]

        """
        def shlex_patch(cmd, reverse=False):
            """Force enquoted separators to not be interpreted as such"""
            patch_strings = ['\r\n', '\n', ';']
            quote_chars = ['"', "'", "`"]
            patch_strings = [(s, str(hash(s))) for s in patch_strings]
            if not reverse:
                for s,m in patch_strings:
                    for q in quote_chars:
                        cmd = cmd.replace('%s%s%s' %(q, s, q),
                                          '%s%s%s' %(q, m, q))
            else:
                for s,m in patch_strings:
                    cmd = [e.replace(m, s) for e in cmd]
            return cmd

        string = string.lstrip()

        # get a list of arguments from custom shlex configuration
        # Example: ['ls','-a',';','help']
        ok = False
        while not ok:
            try:
                lex = shlex.shlex( instream=shlex_patch(string), posix=True )
                lex.quotes += '`'
                lex.wordchars += '$%&()*+,-./:<=>!?@[]^_{|}~'
                lex.whitespace = ' \t'
                arguments = list(lex)
                ok = True
            except ValueError as e:
                # if the last argument quotation has not be closed, assume
                # the string is unfinished, and add a newline to it's end.
                if str(e) == "No closing quotation":
                    string += '\n'
                # if a lines ends with an antislash, assume the pressed
                # <RETURN> key as an escaped char, then just remove it.
                elif str(e) == "No escaped character":
                    string = string[:-1]
                # pursue interpretation on the next line (bash like)
                try:
                    string += self.raw_input(self.prompt_ps2)
                except (EOFError, KeyboardInterrupt):
                    string = ''

        # separate arguments by commands [['ls','-a'],['help']]
        commands = []
        begidx = 0
        for idx, arg in enumerate(arguments):
            if arg in [';','\n','\r\n']:
                new = arguments[begidx:idx]
                commands.append(new)
                begidx = idx + 1
        commands.append( arguments[begidx:] ) # add last command args

        for idx, cmd in enumerate(commands): # reverse the patch morph
            commands[idx] = shlex_patch(cmd, reverse=True)

        return commands


    def onecmd(self, argv):
        """Interpret the argument as though it had been typed in response
        to the prompt.

        This may be overridden, but should not normally need to be;
        see the precmd() and postcmd() methods for useful execution hooks.
        The return value is a flag indicating whether interpretation of
        commands by the interpreter should stop.

        """
        # call emptyline() if no arguments
        if not argv:
            return self.emptyline()
        # call 'help <cmd>' when '<cmd> --help' is typed
        if len(argv) == 2 and argv[1] == '--help':
            return self.interpret('help '+argv[0])

        # get command function
        try: cmdrun = getattr(self, 'do_'+argv[0])
        except AttributeError: cmdrun = self.default

        # execute it, and handle error representation if fails:
        try:
            return cmdrun(argv)
        except BaseException as e:
            return self.onexception(e)


    def onexception(self, exception):
        """Hook method executed when a python exception is raised
        on command execution or prompt interface.

        It is called each time the prompt, or a command beeing executed
        by onecmd() raises an exception.
        For custom error handling, special methods except_ERR()
        may be defined. See the except_KeyboardInterrupt() method for
        a concrete example.

        If exception's name except_*() method exists, it is executed,
        and `exception` becomes the method's return value.
        If `exception` is an Exception object, is is converted to a
        tuple (name, str(exception)).
        `exception` is then returned.

        """
        # try to call concerned except_* hooks in the order
        for cls in exception.__class__.mro()[:-1]:
            hook = 'except_' + cls.__name__
            if hasattr(self, hook):
                exception = getattr(self, hook)(exception)
                break

        if isinstance(exception, BaseException):
            name = type(exception).__name__
            name = re.sub('([A-Z][a-z])', ' \\1', name).strip()
            exception = (name,) + exception.args

        return self.return_handler(exception)


    def return_handler(self, code):
        """Called by onecmd() and cmdloop() methods, to manage commands
        and instance return codes. It acts like the sys.exit method,
        converting None returns values to 0, writting error to stderr
        if it is a string (before returning 1).

        """
        if code is None:
            code = 0
        if isinstance(code, tuple):
            code = ': '.join(str(e) for e in code)
        if not isinstance(code, int):
            self.stderr.write(code + "\n")
            code = 1
        return code


    def emptyline(self):
        """Called when an empty line is entered in response to the prompt.

        By default, it does nothing (unless the 'cmd' lib behavior)

        """
        return


    def default(self, argv):
        """Called on an input line when the command prefix is not recognized.

        If this method is not overridden, it prints an error message and
        returns.

        """
        cmdRepr = "${!r}".format(argv[0])
        cmd = argv[0] if argv[0] == cmdRepr[2:-1] else cmdRepr
        self.stdout.write( (self.nocmd+'\n') %cmd )


    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        If a command has not been entered, then complete against command list.
        Otherwise try to call complete_<command> to get list of completions.
        """
        if state == 0:
            import readline
            origline = readline.get_line_buffer()
            line = origline.lstrip()
            stripped = len(origline) - len(line)
            begidx = readline.get_begidx() - stripped
            endidx = readline.get_endidx() - stripped

            # get the current command's name (argv[0])
            try:
                name = self.parseline(line)[-1][0]
            except:
                name = None
            # if the cmd name has been entirely typed, then use it's dedicated
            # complete_*() method, or fallback to completedefault().
            if begidx>0:
                try:
                    compfunc = getattr(self, 'complete_'+name)
                except AttributeError:
                    compfunc = self.completedefault
            # if the cmd name is being typed, completion must suggest the
            # available commands list, aka completenames()
            else:
                compfunc = self.completenames
            self.completion_matches = compfunc(text, line, begidx, endidx)
        try:
            return self.completion_matches[state]+' '
        except IndexError:
            return


    def get_names(self, obj=None, filter=''):
        """Pull in 'obj' base class attributes (defaults to self).
        'filter' ads possibility to add a word prefix condition, auto
        stripped from returned elements.
        >>> get_names(perfix='do_')
        ['help', 'exit']

        """
        if obj is None:
            obj = self

        attrs = dir(obj.__class__)
        return [e[len(filter):] for e in attrs if e.startswith(filter)]


    def do_help(self, argv):
        'List available commands with "help" or detailed help with "help cmd".'
        argv.append('')
        super(Cmd, self).do_help(argv[1])


    def do_exit(self, argv):
        'Leave the shell interface'
        self.stdout.write("*** Command shell left with 'exit'\n")
        exit()


    def except_SystemExit(self, exception):
        """On SystemExit exceptions (aka sys.exit() call), simply
        raise the same exception, sending a leaving query to the
        cmdloop() class.

        """
        raise exception


    def except_KeyboardInterrupt(self, exception):
        """It writes a newline, then returns its own value to keep
        onexception()'s error printing.

        """
        self.stdout.write('\n')
        return exception
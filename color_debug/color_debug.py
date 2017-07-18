import logging
import re

# import sys

# from ansible.logger import levels
# import this module to dump colories DEBUG level logging on stdout
#
# includes thread info by default, so can be useful for some
# quick thread debugging (hahaha...)
#

# TODO: add a Filter or LoggingAdapter that adds a record attribute for parent pid
#       (and maybe thread group/process group/cgroup ?)


def find_format_attrs(format_string):
    attrs_re_string = r"(?P<full_attr>%\((?P<attr_name>" + r'.*' + r"?)\).*?[dsf])"

    attrs_re = re.compile(attrs_re_string)
    format_attrs = attrs_re.findall(format_string)

    return format_attrs


def context_color_format_string(format_string, format_attrs):
    '''For extending a format string for logging.Formatter to include attributes with color info.

    ie, '%(process)d %(threadName)s - %(msg)'

    becomes

    '%(_cdl_process)s%(process)d%(_cdl_reset)s %(_cdl_threadName)%(threadName)s%(_cdl_reset)s - %(msg)'

    Note that adding those log record attributes is left to... <FIXME>.
    '''
    print('ccfs')
    format_attrs = find_format_attrs(format_string)
    # TODO: pass in a list of record/logFormatter attributes to be wrapped for colorization

    color_attrs_string = '|'.join([x[1] for x in format_attrs])

    # This looks for log format strings like '%(threadName)s' or '$(process)d, and replaces
    # the format specifier with a version wrapped with log record color attributes.
    #
    # For ex, '%(threadName)s'  -> %(_cdl_threadName)s%(threadName)s%(cdl_reset)
    #
    # When ColorFormatter.format() is called on a LogRecord, this is equilivent to
    # calling 'log_format_string % log_record.__dict__', and uses the normal (but 'old school')
    # string formatting (ie, %s style). 'threadName' is populated automatically by a logging.Logger() class on .log(),
    # but the custom fields like %(_cdl_threadName)s need to be added to the log record
    # we pass to ColorFormatter.format()
    #
    # ColorFormatter.format() actually does this itself, but those attributes could be set else
    # via a logger, a log adapter, a logging Filter attached to the logger, a filter attached
    # to a logging.Handler, or by a logging handler itself. Since our attributes are purely for
    # formatting, we just do it in the ColorFormatter.format()
    # https://docs.python.org/2/library/logging.html#logrecord-attributes
    #
    # THe captured groups 'full_attr' is the entire record attribute from the string, including
    # string formatting/precsion, and padding info. ie '%(process)-10d' is a process pid right justified with
    # a max length of 10 chars.
    #
    # The capture 'attr_name' is just the name of the attr, 'process' or 'message' or 'levelname' for ex. This
    # is extract so it can be used in the name of the color debug logger attribute that will set the color info
    # For '%(process)-10d', that would make 'process' the attr_name, and the color attribute '%(_cdl_process)'
    # color_attrs_string is a sub regex of the attr names to be given color using the re alternate '|' notation.
    re_string = r"(?P<full_attr>%\((?P<attr_name>" + color_attrs_string + r"?)\).*?[dsf])"

    color_format_re = re.compile(re_string)

    replacement = r"%(_cdl_\g<attr_name>)s\g<full_attr>%(_cdl_unset)s"

    # likely needs thread locking
    # exc_info_post = '%(exc_text_sep)s%(exc_text)s'
    # format_string = '%s%s' % (format_string, exc_info_post)

    # for match in format_attrs.groups():
    #    print('match: %s' % match)

    format_string2 = color_format_re.sub(replacement, format_string)

    # set the default color at the begining of the format string and add a reset to the end
    format_string = r"%(_cdl_default)s" + format_string2 + r"%(_cdl_reset)s"

    return format_string


RGB_COLOR_OFFSET = 16


class ColorFormatter(logging.Formatter):
    FORMAT = ("""%(asctime)-15s"""
              #              """ %(relativeCreated)-8d"""
              """ %(levelname)-0.1s"""
              #              """\033[1;35m%(name)s$RESET """
              #              """%(processName)s """
              # assume we only need 3 digits for worker process number, if you see this wrap, but the '-4s' below
              # to '-5s'. This is fixed width just to make the results easier to read for the normal case
              # (everything before 'name' should be the same width for each log item show...)
              """ %(processName)-4s %(_cdl_process)spid=%(process)-5d%(_cdl_unset)s"""
              # """ %(ppid)-5s"""
              # truncate thread name to 2 chars, we use 2char names or the process filter does MainThread/MT elsewhere
              """ %(threadName)-2s"""
              # """ %(thread)d"""
              # """[tid: \033[32m%(thread)d$RESET tname:\033[32m%(threadName)s]$RESET """
              """ %(name)s"""
              """ """
              """%(funcName)s"""
              """ """
              """%(filename)s"""
              """ """
              """%(lineno)d"""
              """ - %(message)s"""
              """%(_cdl_reset)s""")

    default_record_attrs = ['args', 'asctime', 'created', 'exc_info', 'filename',
                            'funcName', 'levelname', 'levelno', 'lineno', 'module',
                            'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                            'processName', 'relativeCreated', 'thread', 'threadName']
    custom_record_attrs = ['exc_text']

    custom_attrs = ['levelname', 'levelno', 'process', 'processName', 'thread', 'threadName']
    high_cardinality = set(['asctime', 'created', 'msecs', 'relativeCreated', 'args', 'message'])

    default_color_groups = [
        # color almost everything by logger name
        # ('name', ['filename', 'module', 'lineno', 'funcName', 'pathname']),
        # ('process', ['default', 'message']),
        # ('process', ['processName', 'process']),
        # ('thread', ['default', 'threadName', 'message', 'unset', 'processName', 'exc_text']),
        # ('thread', ['threadName', 'thread']),

        # color logger name, filename and lineno same as the funcName
        # ('funcName', ['default', 'message', 'unset', 'name', 'filename', 'lineno']),
        # color message same as debug level
        ('levelname', ['levelname', 'levelno']),

        # color funcName, filename, lineno same as logger name
        # ('name', ['funcName', 'filename', 'lineno']),

        # ('time_color', ['asctime', 'relativeCreated', 'created', 'msecs']),
        # ('task', ['task_uuid', 'task']),
        # color message and default same as funcName
        # ('funcName', ['message', 'unset'])


        # ('funcName', ['relativeCreated', 'asctime'])

        # color default, msg and playbook/play/task by the play
        # ('play', ['default','message', 'unset', 'play', 'task']),
    ]

    # hacky ansi color stuff
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"
    funcName = u""
    processName = u""

    NUMBER_OF_BASE_COLORS = 8
    # NUMBER_OF_THREAD_COLORS = 216
    # the xterm256 colors 0-8 and 8-16 are normal and bright term colors, 16-231 is from a 6x6x6 rgb cube
    # 232-255 are the grays (white to gray to black)
    RGB_COLOR_OFFSET = 16
    START_OF_THREAD_COLORS = RGB_COLOR_OFFSET
    END_OF_THREAD_COLORS = 231
    NUMBER_OF_THREAD_COLORS = END_OF_THREAD_COLORS - RGB_COLOR_OFFSET
    BASE_COLORS = dict((color_number, color_seq) for
                       (color_number, color_seq) in [(x, "\033[38;5;%dm" % x) for x in range(NUMBER_OF_BASE_COLORS)])
    # \ x 1 b [ 38 ; 5; 231m
    THREAD_COLORS = dict((color_number, color_seq) for
                         (color_number, color_seq) in [(x, "\033[38;5;%dm" % x) for x in range(START_OF_THREAD_COLORS, END_OF_THREAD_COLORS)])
    ALL_COLORS = {}
    ALL_COLORS.update(BASE_COLORS)
    ALL_COLORS.update(THREAD_COLORS)

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = BASE_COLORS.keys()

    DEFAULT_COLOR_IDX = 257
    RESET_SEQ_IDX = 256
    ALL_COLORS[RESET_SEQ_IDX] = RESET_SEQ

    DEFAULT_COLOR = WHITE

    # FIXME: use logging.DEBUG etc enums
    LEVEL_COLORS = {'TRACE': BLUE,
                    'SUBDEBUG': BLUE,
                    'DEBUG': BLUE,
                    # levels.VV: BASE_COLORS[BLUE],
                    # levels.VVV: BASE_COLORS[BLUE],
                    # levels.VVVV: BASE_COLORS[BLUE],
                    # levels.VVVVV: BASE_COLORS[BLUE],
                    'INFO': GREEN,
                    # levels.V: BASE_COLORS[GREEN],
                    'SUBWARNING': YELLOW,
                    'WARNING': YELLOW,
                    'ERROR': RED,
                    # bold red?
                    'CRITICAL': RED}

    # A little weird...
    @property
    def color_fmt(self):
        if not self._color_fmt:
            self._color_fmt = context_color_format_string(self._base_fmt, self._format_attrs)
        return self._color_fmt

    # @_fmt.setter
    # def _fmt(self, value):
    #    self._base_fmt = value
    #    self._color_fmt = None

    def __init__(self, fmt=None, default_color_by_attr=None, color_groups=None):
        fmt = fmt or self.FORMAT
        logging.Formatter.__init__(self, fmt)
        self._base_fmt = fmt
        self._color_fmt = None

        self._format_attrs = find_format_attrs(self._base_fmt)

        self.color_groups = color_groups or []

        # self.group_by = [('default', ['default', 'message', 'unset'])]
        self.group_by = self.default_color_groups[:]
        self.group_by.extend(self.color_groups)

        # TODO: be able to set the default color by attr name. Ie, make a record default to the thread or processName
        self.default_color_by_attr = default_color_by_attr or 'process'
        # the name of the record attribute to check for a default color
        self.default_attr_string = '_cdl_%s' % self.default_color_by_attr

        # self.default_color = self.BASE_COLORS[self.WHITE]
        # self.default_color = self.BASE_COLORS[self.YELLOW]

        # if self.default_color_by_attr not in [x[1] for x in self.group_by]:
        #    self.group_by.append((self.default_color_by_attr, ['default']))

    # TODO: rename and generalize
    # TODO: tie tid/threadName and process/processName together so they start same color
    #       so MainProcess, the first pid/processName are same, and maybe MainThread//first tid
    # DOWNSIDE: requires tracking all seen pid/process/tid/threadName ? that could be odd with multi-processes with multi instances
    #           of the Formatter
    # TODO: make so a given first ProcessName will always start the same color (so multiple runs are consistent)
    # TODO: make 'msg' use the most specific combo of pid/processName/tid/threadName
    # TODO: generalize so it will for logger name as well
    # MAYBE: color hiearchy for logger names? so 'foo.model' and 'foo.util' are related...
    #        maybe split on '.' and set initial color based on hash of sub logger name?
    # SEEALSO: chromalog module does something similar, may be easiest to extend
    # TODO: this could be own class/methods like ContextColor(log_record) that returns color info
    def get_thread_color(self, threadid):
        # 220 is useable 256 color term color (forget where that comes from? some min delta-e division of 8x8x8 rgb colorspace?)
        thread_mod = threadid % self.NUMBER_OF_THREAD_COLORS
        # print threadid, thread_mod % 220
        # return self.THREAD_COLORS[thread_mod]
        return thread_mod + self.RGB_COLOR_OFFSET

    # TODO: This could special case 'MainThread'/'MainProcess' to pick a good predictable color
    def get_name_color(self, name, perturb=None):
        # if name == '':
        #    return self._default_color_index
        perturb = perturb or ''
        name = '%s%s' % (name, perturb)
        # name_hash = hash(name)
        name_hash = sum([ord(x) for x in name])
        name_mod = name_hash % self.NUMBER_OF_THREAD_COLORS
        # return self.THREAD_COLORS[name_mod]
        return name_mod + self.RGB_COLOR_OFFSET

    def get_level_color(self, levelname, levelno):
        level_color = self.LEVEL_COLORS.get(levelname, None)
        if not level_color:
            level_color = self.LEVEL_COLORS.get(levelno, self.default_color)
        return level_color

    def get_process_colors(self, record):
        '''Given process/thread info, return reasonable colors for them.

        Roughly:

            - attempts to get a unique color per processName
            - attempts to get a unique color per pid
                - attempt to make those the same for MainProcess
                - any other processName, the pname color and the pid color cann be different
            - if threadName is 'MainThread', make tname_color and tid_color match MainProcess pname_color and pid_color
            - other threadNames get a new color and new tid_color

            Existing get_*color_ methods attempt to divy up colors by mod 220 on tid/pid, or mod 220 on hash of thread or pid name
            NOTE: This doesn't track any state so there is no ordering or prefence to the colors given out.
        '''
        pname, pid, tname, tid = record.processName, record.process, record.threadName, record.thread
        # 'pname' is almost always 'MainProcess' which ends up a ugly yellow. perturb is here to change the color
        # that 'MainProcess' ends up to a nicer light green
        perturb = 'pseudoenthusiastically'
        # perturb = 'a'
        # combine pid+pname otherwise, all MainProcess will get the same pname
        pid_label = '%s%s' % (pname, pid)
        pname_color = self.get_name_color(pid_label, perturb=perturb)
        # pname_color = self.get_name_color(pid_label, perturb=perturb)
        if pname == 'MainProcess':
            pid_color = pname_color
        else:
            pid_color = self.get_thread_color(pid)

        if tname == 'MainThread':
            # tname_color = pname_color
            tname_color = pid_color
            tid_color = tname_color
        else:
            tname_color = self.get_name_color(tname)
            tid_color = self.get_thread_color(tid)

        return pname_color, pid_color, tname_color, tid_color

    # TODO: maybe add a Filter that sets a record attribute for process/pid/thread/tid color that formatter would use
    #       (that would let formatter string do '%(theadNameColor)s tname=%(threadName)s %(reset)s %(processColor)s pid=%(process)d%(reset)s'
    #       so that the entire blurb about process info matches instead of just the attribute
    #       - also allows format to just expand a '%(threadName)s' in fmt string to '%(theadNameColor)s%(threadName)s%(reset)s' before regular formatter
    # DOWNSIDE: Filter would need to be attach to the Logger not the Handler
    def format(self, record):

        _default_color_index = self.DEFAULT_COLOR_IDX
        # 'cdl' is 'context debug logger'. Mostly just an unlikely record name to avod name collisions.
        # record._cdl_reset = self.RESET_SEQ
        # record._cdl_default = self.default_color
        # record._cdl_unset = self.default_color
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)

        record.exc_text_sep = ''
        record.exc_text = ''
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
            record.exc_text_sep = '\n'

        colors = {'_cdl_default': _default_color_index,
                  '_cdl_unset': _default_color_index,
                  '_cdl_reset': self.RESET_SEQ_IDX}

        # custom_mapppers = levelno, levelno
        # thread, threadname, process, processname

        # populate the record with values for any _cdl_* attrs we will use
        # could be self._format_attrs (actually used in format string) + any referenced as color_group keys
        group_by_attrs = [y[0] for y in self.group_by]

        format_attrs = [z[1] for z in self._format_attrs]

        # attrs_needing_default = self.default_record_attrs + self.custom_record_attrs
        attrs_needed = group_by_attrs + format_attrs
        for attr_needed in attrs_needed:
            cdl_name = '_cdl_%s' % attr_needed
            # setattr(record, cdl_name, self.default_color)
            colors[cdl_name] = _default_color_index

        use_level_color = 'levelname' in group_by_attrs or 'levelno' in group_by_attrs
        # NOTE: the impl here is based on info from justthe LogRecord and should be okay across threads
        #       If this wants to use more global data, beware...
        if use_level_color:
            level_color = self.get_level_color(record.levelname, record.levelno)
            # record._cdl_levelname = level_color
            colors['_cdl_levelname'] = level_color

        # set a different color for each logger name. And by default, make filename, funcName, and lineno match.
        use_name_color = 'name' in group_by_attrs
        if use_name_color:
            # module_and_method_color = self.get_name_color('%s.%s' % (record.name, record.funcName))
            module_and_method_color = self.get_name_color(record.name)
            colors['_cdl_name'] = module_and_method_color
            # group mapping should take care of the rest of these once _cdl_name is set

        use_thread_color = False
        for attr in ['process', 'processName', 'thread', 'threadName']:
            if attr in group_by_attrs:
                use_thread_color = True

        if use_thread_color:
            pname_color, pid_color, tname_color, tid_color = self.get_process_colors(record)

            colors['_cdl_process'] = pid_color
            colors['_cdl_processName'] = pname_color
            colors['_cdl_thread'] = tid_color
            colors['_cdl_threadName'] = tname_color
            colors['_cdl_exc_text'] = tid_color

        # fields we don't need to calculate indiv, since they will be a different group
        in_a_group = set()

        # print('self.group_by: %s' % self.group_by)
        for group, members in self.group_by:
            group_color = colors.get('_cdl_%s' % group, _default_color_index)

            for member in members:
                colors['_cdl_%s' % member] = group_color
                # print('group_color: %s' % group_color)
                in_a_group.add(member)

        # print('in_a_group: %s' % in_a_group)
        calc_colors = set()
        for needed_attr in attrs_needed:
            if needed_attr in self.custom_attrs or needed_attr in in_a_group or needed_attr in self.high_cardinality:
                continue
            colors['_cdl_%s' % needed_attr] = self.get_name_color(getattr(record, needed_attr))
            calc_colors.add(needed_attr)

        # set the default color based on computed values, lookup the color
        # mapped to the attr default_color_by_attr  (ie, if 'process', lookup
        # record._cdl_process and set self.default_color to that value
        _color_by_attr_index = colors[self.default_attr_string]

        for cdl_name, cdl_idx in colors.items():
            # print('cdl_name: %s cdl_idx: %s' % (cdl_name, cdl_idx))
            if cdl_idx == self.DEFAULT_COLOR_IDX:
                cdl_idx = _color_by_attr_index
            # print('cdl_name: %s cdl_idx(2): %s' % (cdl_name, cdl_idx))

            setattr(record, cdl_name, self.ALL_COLORS[cdl_idx])

        # pprint.pprint(colors)
        s = self._format(record)
        s = s + record.exc_text
        return s

    # format is based on from stdlib python logging.LogFormatter.format()
    # It's kind of a pain to customize exception formatting, since it
    # just appends the exception string from formatException() to the formatted message.
    def _format(self, record):
        record.message = record.getMessage()
        s = self.color_fmt % record.__dict__
        return s


def _get_handler():
    # %(asctime)s tid:%(thread)d
    # fmt = u'\033[33m**: tname:%(threadName)s @%(filename)s:%(lineno)d - %(message)s\033[0m'
    # fmt = u': tname:%(threadName)s @%(filename)s:%(lineno)d - %(message)s'
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter())
    # handler.setFormatter(logging.Formatter(fmt))
    handler.setLevel(logging.DEBUG)

    return handler

# logging.getLogger().setLevel(logging.DEBUG)
# logging.getLogger().addHandler(_get_handler())

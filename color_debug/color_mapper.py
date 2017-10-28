
DEFAULT_COLOR_BY_ATTR = 'process'

RGB_COLOR_OFFSET = 16

class BaseColorMapper(object):
    # default_color_groups is:
    # ('attr', a_list_of_record_attrs_to_use_attrs_color)
    default_color_groups = [
        # color almost everything by logger name
        ('name', ['filename', 'module', 'lineno', 'funcName', 'pathname']),
        ('process', ['processName', 'thread', 'threadName']),
        ('levelname', ['levelname', 'levelno'])]

    custom_attrs = ['levelname', 'levelno', 'process', 'processName', 'thread', 'threadName']
    high_cardinality = set(['asctime', 'created', 'msecs', 'relativeCreated', 'args', 'message'])

    def __init__(self, fmt=None, default_color_by_attr=None,
                 color_groups=None, format_attrs=None):
        self._fmt = fmt
        self.color_groups = color_groups or []

        self.group_by = self.default_color_groups[:]
        self.group_by.extend(self.color_groups)

        self.default_color_by_attr = default_color_by_attr or DEFAULT_COLOR_BY_ATTR
        self.default_attr_string = '_cdl_%s' % self.default_color_by_attr

        self._format_attrs = format_attrs

    def get_thread_color(self, thread_id):
        '''return color idx for thread_id'''
        return 0

    def get_name_color(self, name, perturb=None):
        '''return color idx for 'name' string'''
        return 0

    def get_level_color(self, levelname, levelno):
        '''return color idx for logging levelname and levelno'''
        return 0

    def get_process_colors(self, record):
        '''return a tuple of pname_color, pid_color, tname_color, tid_color idx for process record'''
        return 0, 0, 0, 0
        # return pname_color, pid_color, tname_color, tid_color

    def get_colors_for_attr(self, record):
        return {}


# TODO: could split into a IndexedColorMapper, TermColorMapper just building the right indexes
class TermColorMapper(BaseColorMapper):
    # hacky ansi color stuff
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    # Note: 'THREAD_COLORS' is a misnomer now and just means all of the colors
    # TODO: update THREAD_COLOR usage

    # NUMBER_OF_THREAD_COLORS = 216 for 256 color terms
    # the xterm256 colors 0-8 and 8-16 are normal and bright term colors, 16-231 is from a 6x6x6 rgb cube
    # 232-255 are the grays (white to gray to black)
    NUMBER_OF_BASE_COLORS = 8
    RGB_COLOR_OFFSET = 16
    START_OF_THREAD_COLORS = RGB_COLOR_OFFSET
    END_OF_THREAD_COLORS = 231
    NUMBER_OF_THREAD_COLORS = END_OF_THREAD_COLORS - RGB_COLOR_OFFSET

    BASE_COLORS = dict((color_number, color_seq) for
                       (color_number, color_seq) in [(x, "\033[38;5;%dm" % x) for x in range(NUMBER_OF_BASE_COLORS)])

    # NOTE: We skip the bold/bright colors (8-16) here
    # TODO: revisit bold/bright colors when we add support for RGB term colors

    # \ x 1 b [ 38 ; 5; 231m
    THREAD_COLORS = dict((color_number, color_seq) for
                         (color_number, color_seq) in [(x, "\033[38;5;%dm" % x) for x in range(START_OF_THREAD_COLORS, END_OF_THREAD_COLORS)])

    # TODO: support changing background colors to get more color options

    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = BASE_COLORS.keys()

    # The indexes into ALL_COLORS list for special cases.
    RESET_SEQ_IDX = 256
    DEFAULT_COLOR_IDX = 257

    DEFAULT_COLOR = WHITE

    # FIXME: ALL_COLORS is a dict indexed by an  incremental int
    #        Could/should be an array. Though the dict could allow
    #        keys like 'default' or 'reset' which would be less obtust
    #        than All_COLORS[257] to get reset.
    ALL_COLORS = {}
    ALL_COLORS.update(BASE_COLORS)
    ALL_COLORS.update(THREAD_COLORS)
    ALL_COLORS[RESET_SEQ_IDX] = RESET_SEQ
    ALL_COLORS[DEFAULT_COLOR_IDX] = ALL_COLORS[DEFAULT_COLOR]

    # FIXME: use logging.DEBUG etc enums
    LEVEL_COLORS = {'TRACE': BLUE,
                    'SUBDEBUG': BLUE,
                    'DEBUG': BLUE,
                    'INFO': GREEN,
                    'SUBWARNING': YELLOW,
                    'WARNING': YELLOW,
                    'ERROR': RED,
                    'CRITICAL': RED}

    _default_color_groups = [
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
    def get_colors_for_record(self, record):
        '''For a log record, compute color for each field and return a color dict'''

        _default_color_index = self.DEFAULT_COLOR_IDX
        # 'cdl' is 'context debug logger'. Mostly just an unlikely record name to avod name collisions.
        # record._cdl_reset = self.RESET_SEQ
        # record._cdl_default = self.default_color
        # record._cdl_unset = self.default_color
        # self._pre_format(record)

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

        for group, members in self.group_by:
            group_color = colors.get('_cdl_%s' % group, _default_color_index)

            for member in members:
                colors['_cdl_%s' % member] = group_color
                in_a_group.add(member)

        for needed_attr in attrs_needed:
            if needed_attr in self.custom_attrs or needed_attr in in_a_group or needed_attr in self.high_cardinality:
                continue
            color_idx = self.get_name_color(getattr(record, needed_attr))
            colors['_cdl_%s' % needed_attr] = color_idx

        # set the default color based on computed values, lookup the color
        # mapped to the attr default_color_by_attr  (ie, if 'process', lookup
        # record._cdl_process and set self.default_color to that value
        _color_by_attr_index = colors[self.default_attr_string]

        name_to_color_map = {}
        for cdl_name, cdl_idx in colors.items():
            # FIXME: revisit setting default idx to a color based on string
            if cdl_idx == self.DEFAULT_COLOR_IDX:
                cdl_idx = _color_by_attr_index
            name_to_color_map[cdl_name] = self.ALL_COLORS[cdl_idx]
        return name_to_color_map

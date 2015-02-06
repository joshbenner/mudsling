import lupa
import types
import logging

from pygments import highlight
from pygments.lexers import LuaLexer
from pygments.formatters import TerminalFormatter, Terminal256Formatter


def filter_attribute_access(obj, attr_name, is_setting):
    if ((not isinstance(attr_name, basestring)) or attr_name.startswith('__')
        or (isinstance(obj, (types.FunctionType, types.MethodType))
            and attr_name.startswith('func_'))):
        raise AttributeError('access denied to %r.%s' % (obj, attr_name))
    return attr_name


try:
    lua = lupa.LuaRuntime(attribute_filter=filter_attribute_access)
    lua_version = lua.eval('_VERSION')
except:
    lua_version = '?'
if lua_version != 'Lua 5.2':
    logging.error('Incorrect Lua version: %s', lua_version)
    lua_enabled = False
else:
    lua_enabled = True

SANDBOX_SCRIPT = r'''
function sandbox_load(untrusted_code, extra_env)
    extra_env = extra_env or {}
    local env = {
        ipairs = ipairs,
        next = next,
        pairs = pairs,
        pcall = pcall,
        tonumber = tonumber,
        tostring = tostring,
        type = type,
        unpack = unpack,
        coroutine = { create = coroutine.create, resume = coroutine.resume,
            running = coroutine.running, status = coroutine.status,
            wrap = coroutine.wrap },
        string = { byte = string.byte, char = string.char, find = string.find,
            format = string.format, gmatch = string.gmatch, gsub = string.gsub,
            len = string.len, lower = string.lower, match = string.match,
            rep = string.rep, reverse = string.reverse, sub = string.sub,
            upper = string.upper },
        table = { insert = table.insert, maxn = table.maxn,
            remove = table.remove, sort = table.sort },
        math = { abs = math.abs, acos = math.acos, asin = math.asin,
            atan = math.atan, atan2 = math.atan2, ceil = math.ceil,
            cos = math.cos, cosh = math.cosh, deg = math.deg, exp = math.exp,
            floor = math.floor, fmod = math.fmod, frexp = math.frexp,
            huge = math.huge, ldexp = math.ldexp, log = math.log,
            log10 = math.log10, max = math.max, min = math.min,
            modf = math.modf, pi = math.pi, pow = math.pow, rad = math.rad,
            random = math.random, sin = math.sin, sinh = math.sinh,
            sqrt = math.sqrt, tan = math.tan, tanh = math.tanh },
        os = { clock = os.clock, difftime = os.difftime, time = os.time },
    }
    for k, v in pairs(extra_env) do env[k] = v end
    return load(untrusted_code, nil, 't', env)
end

function sandbox_run(untrusted_code, extra_env)
    local untrusted_function, message = sandbox_load(untrusted_code, extra_env)
    if not untrusted_function then return nil, message end
    return pcall(untrusted_function)
end
'''
lua.execute(SANDBOX_SCRIPT)
_sandbox_load = lua.globals().sandbox_load
_sandbox_run = lua.globals().sandbox_run


def sandbox_syntax_check(code):
    r = _sandbox_load(code)
    if not isinstance(r, tuple):
        return None
    else:
        return r[1]


def sandbox_run(code, env=None):
    """
    Run untrusted Lua code.

    :param code: The code to execute.
    :type code: str

    :return: The result of attempting execution: (success, error or *return)
    :rtype: tuple
    """
    env = env or {}
    r = _sandbox_run(code, lua.table_from(env))
    if isinstance(r, bool):
        r = (r,)
    if r[0] is None:
        r = list(r)
        r[0] = False
        r = tuple(r)
    return r


def format_code(code, indent='  '):
    lines = str(code).splitlines() if isinstance(code, basestring) else code
    formatted = []
    cur_indent = 0
    next_indent = 0
    for line in lines:
        line = line.strip()
        if (line.startswith('function') or line.startswith('repeat')
                or line.startswith('while') or line.endswith('then')
                or line.endswith('do') or line.endswith('{')):
            next_indent = cur_indent + 1
        if (line in ('end', '}')) or line.startswith('until'):
            cur_indent -= 1
            next_indent = cur_indent
        if line.startswith('else') or line.startswith('elseif'):
            cur_indent -= 1
            next_indent = cur_indent + 1
        formatted.append(line if line == '' else ((indent * cur_indent) + line))
        cur_indent = next_indent
    return '\n'.join(formatted)


def highlight_code(code, ansi256=False, style='monokai'):
    code = str(code) if isinstance(code, basestring) else '\n'.join(code)
    if ansi256:
        formatter = Terminal256Formatter(style=style)
    else:
        formatter = TerminalFormatter(bg='dark')
    return str(highlight(code, LuaLexer(), formatter))

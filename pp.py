import sys
import os
import pwd
import json
import telnetlib
import socket

connect_id = sys.argv[1]
prefix = sys.argv[2]
connect_port = int(sys.argv[3])

echo = telnetlib.Telnet('127.0.0.1', connect_port)

safe_globals = {}

def cover_exec(func, data):
    return func(data)

def get_traceback_frames(exc_type, exc_value, tb):
    frames = []
    while tb is not None:
        # support for __traceback_hide__ which is used by a few libraries
        # to hide internal frames.
        filename = tb.tb_frame.f_code.co_filename
        if filename == '<MYCODE>':
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno
            frames.append({
                'tb': tb,
                'function': function,
                'lineno': lineno,
                'vars': tb.tb_frame.f_locals.items(),
                'id': id(tb),
            })
        tb = tb.tb_next

    if not frames:
        frames = [{
            'filename': '&lt;unknown&gt;',
            'function': '?',
            'lineno': '?',
            'context_line': '???',
        }]

    return frames


def unicoder(line):
    return line


def str_frames(ex, frames):
    frames.reverse()
    result = '%s: %s' % (type(ex).__name__,unicoder(ex)) + '\n'
    trace_lines = []
    for frame in frames:
        trace_lines.append(' %s, %s' % (frame['function'], frame['lineno']))
    return result + '\n'.join(trace_lines)


def str_traceback(ex, *args):
    return str_frames(ex, get_traceback_frames(*args))

def exec_my_code(code):
    try:
        exec (compile(code, '<MYCODE>', 'exec'), safe_globals)
    except Exception as e:
        sys.stderr.write(str_traceback(e, *sys.exc_info()))
        sys.stderr.flush()
        raise

def do_run(data):
    if 'r_seed' in data:
        random.seed(data['r_seed'])
        RANDOM_SEED = data['r_seed']

    if 'env_config' in data:
        config_env(data['env_config'])

    try:
        return {
            'do': 'done',
            'result': exec_my_code(data['code']),
        }
    except Exception as e:
        sys.stderr.write(str_traceback(e, *sys.exc_info()))
        sys.stderr.flush()
        return {
            'do': 'run_fail',
        }

def do_exec(data):
    if data['func'] not in safe_globals:
        return {
            'do': 'exec_fail',
            'text': 'NoExecFunction'
        }
    try:
        return {
            'do': 'exec_done',
            'result': cover_exec(safe_globals[data['func']], data['in'])
        }
    except Exception as e:
        sys.stderr.write(str_traceback(e, *sys.exc_info()))
        sys.stderr.flush()
        return {
            'do': 'exec_fail'
        }

def _recive_sock(sock, trys=4):
    sock.settimeout(1200000)
    try:
        return sock.recv(100000000)
    except socket.error as e:
        if e.errno != 4:
            trys -= 1
            if not trys:
                raise
        return _recive_sock(sock, trys=trys)

def echo_send(send):
    send = str(send)
    echo.write(send.encode('utf-8') + b'\0')

def echo_send_recv(send):
    echo_send(send)
    data = ''
    sock = echo.get_socket()
    no_data_counter = 100
    while True:
        new_data = _recive_sock(sock).decode('utf-8')
        if not new_data:
            no_data_counter -= 1
            if not no_data_counter:
                raise ValueError('No data')
        data += new_data
        if '\0' in new_data:
            recv = data.split('\0')[0]
            return recv

def echo_send_recv_json(send):
    data_send = json.dumps(send)
    return json.loads(echo_send_recv(data_send))

run_data = echo_send_recv_json({'do': 'connect', 'id': connect_id, 'pid': os.getpid(), 'prefix': prefix})
while True:
    run_data = echo_send_recv_json(globals()['do_' + run_data['do']](run_data))
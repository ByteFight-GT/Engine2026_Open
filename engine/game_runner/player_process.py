from multiprocessing import Process, Queue, Pipe

import os
import time
import json
import traceback

from game.game_structs import Action, MoveType, Location, Direction

# Captured at module import (in the trusted engine process), before any
# player-controlled code has a chance to monkey-patch time.perf_counter.
# run_player_process pins this into a closure so the subprocess timer
# resists tampering (vuln 3).
_real_perf_counter = time.perf_counter

# Returned to the engine when a player return value fails validation.
_INVALID_TURN_MSG = "Invalid turn"


"""
Everything regarding managing the user process during gameplay is included here.
PlayerProcess is the interface that the main game process uses to interact
with the player process (the interface also includes nice utility functions to 
restart, pause, and terminate the player process). 

The actual player process that is run is described by run_player_process. It includes
securitization measures, memory checks, and a while(True) loop for recieving
instructions on what player functions to call from the interface.
"""

def get_file_permissions(file_path):
    import stat 
    """
    Get file permissions in both symbolic and octal formats.
    """
    
    # Ensure file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Get file status
    file_stat = os.stat(file_path)

    # Get octal permission mask
    octal_perm = oct(file_stat.st_mode & 0o777)

    # Get symbolic permission string (e.g., -rw-r--r--)
    symbolic_perm = stat.filemode(file_stat.st_mode)

    return symbolic_perm, octal_perm

def drop_priveliges(user_name=None, group_name=None):
    
    import os
    import pwd
    import grp
    
    keys = [
        'AUTH_TOKEN', 
        'PIKA_URL', 
        'WEBSERVER_URL', 
        'UPDATE_QUEUE', 
        'RESULT_QUEUE',
        'MATCH_ROUTING_KEY',
        'EXCHANGE_NAME'
    ]
    
    for key in keys:
        if key in os.environ:
            del os.environ[key]

    if not user_name is None and not group_name is None:
        uid = pwd.getpwnam(user_name).pw_uid
        gid = grp.getgrnam(group_name).gr_gid

        # print(uid, gid)
        os.setgid(gid)
        os.setuid(uid)

    # Get the directory above 'engine'
    # base_dir = os.getcwd()  # /app/BotFightEngine

    # # Build full path
    # agent_path = os.path.join(base_dir, "game_env", "game_subs", "temp", "player_a")

    # print(get_file_permissions(agent_path))

def apply_seccomp():
    try:
        import seccomp
    except ImportError:
        import pyseccomp as seccomp
    import prctl
    import signal
    import os

    # prctl.set_ptracer(None)
    prctl.set_no_new_privs(True)
    ctx = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
    # filesystem
    ctx.add_rule(seccomp.KILL, 'chdir')
    ctx.add_rule(seccomp.KILL, 'chmod')
    ctx.add_rule(seccomp.KILL, 'fchmod')
    ctx.add_rule(seccomp.KILL, 'fchmodat')
    ctx.add_rule(seccomp.KILL, 'chown')
    ctx.add_rule(seccomp.KILL, 'fchown')
    ctx.add_rule(seccomp.KILL, 'lchown')
    ctx.add_rule(seccomp.KILL, 'chroot')
    # ctx.add_rule(seccomp.KILL, 'unlink')
    # ctx.add_rule(seccomp.KILL, 'unlinkat')
    # ctx.add_rule(seccomp.KILL, 'rename')
    # ctx.add_rule(seccomp.KILL, 'renameat')
    # ctx.add_rule(seccomp.KILL, 'rmdir')
    # ctx.add_rule(seccomp.KILL, 'mkdir')
    ctx.add_rule(seccomp.KILL, 'mount')
    ctx.add_rule(seccomp.KILL, 'umount2')
    ctx.add_rule(seccomp.KILL, 'symlink')
    # ctx.add_rule(seccomp.KILL, 'link')
    # ctx.add_rule(seccomp.KILL, 'creat')
    ctx.add_rule(seccomp.KILL, 'truncate')
    ctx.add_rule(seccomp.KILL, 'ftruncate')
    # ctx.add_rule(seccomp.KILL, 'pwrite64')

    # #time
    ctx.add_rule(seccomp.KILL, 'adjtimex')
    ctx.add_rule(seccomp.KILL, 'clock_settime')
    ctx.add_rule(seccomp.KILL, 'clock_adjtime')
    ctx.add_rule(seccomp.KILL, 'settimeofday')

    # #network    
    ctx.add_rule(seccomp.KILL, 'socket')
    ctx.add_rule(seccomp.KILL, 'bind')
    ctx.add_rule(seccomp.KILL, 'accept')
    ctx.add_rule(seccomp.KILL, 'connect')
    ctx.add_rule(seccomp.KILL, 'listen')
    ctx.add_rule(seccomp.KILL, 'setsockopt')
    ctx.add_rule(seccomp.KILL, 'getsockopt')
    ctx.add_rule(seccomp.KILL, "sendto")
    ctx.add_rule(seccomp.KILL, "recvfrom")
    ctx.add_rule(seccomp.KILL, "sendmsg")
    ctx.add_rule(seccomp.KILL, "recvmsg")
    ctx.add_rule(seccomp.KILL, 'unshare')
    
    # kernel
    ctx.add_rule(seccomp.KILL, 'reboot')
    ctx.add_rule(seccomp.KILL, 'shutdown')
    ctx.add_rule(seccomp.KILL, 'sysfs')
    ctx.add_rule(seccomp.KILL, 'sysinfo')
    ctx.add_rule(seccomp.KILL, "delete_module")
    ctx.add_rule(seccomp.KILL, 'prctl')
    ctx.add_rule(seccomp.KILL, 'execve')
    ctx.add_rule(seccomp.KILL, 'execveat')
    ctx.add_rule(seccomp.KILL, 'seccomp')

    # #i/o
    # ctx.add_rule(seccomp.KILL, 'ioctl')
    # ctx.add_rule(seccomp.KILL, 'keyctl')
    # ctx.add_rule(seccomp.KILL, 'perf_event_open')
    ctx.add_rule(seccomp.KILL, 'kexec_load')
    # ctx.add_rule(seccomp.KILL, 'iopl')
    # ctx.add_rule(seccomp.KILL, 'ioperm')
    
    #process limiting + scheduling
    ctx.add_rule(seccomp.KILL, 'exit')
    ctx.add_rule(seccomp.KILL, 'setuid')
    ctx.add_rule(seccomp.KILL, 'setgid')
    ctx.add_rule(seccomp.KILL, 'capset')
    ctx.add_rule(seccomp.KILL, 'capget')
    ctx.add_rule(seccomp.KILL, 'kill')
    ctx.add_rule(seccomp.KILL, 'tkill')
    ctx.add_rule(seccomp.KILL, 'tgkill')
    ctx.add_rule(seccomp.KILL, "setrlimit")
    ctx.add_rule(seccomp.KILL, "setpriority")
    ctx.add_rule(seccomp.KILL, "sched_setparam")
    ctx.add_rule(seccomp.KILL, "sched_setscheduler")
    
    ctx.load()


# ============================================================
# Vuln 5 fix: safe player -> engine serialization over a Pipe
# ============================================================
#
# multiprocessing.Queue uses pickle internally. If the player returns a
# custom object, pickle.loads() in the (unsandboxed) main engine process
# runs whatever __reduce__ payload they put there -- arbitrary code execution
# in the engine. Fixing the `== None` comparison (vuln 4) is not enough: the
# RCE fires *during* return_queue.get(), before any check runs.
#
# Instead we keep the player -> engine direction on a multiprocessing.Pipe
# using Connection.send_bytes / recv_bytes (pickle-free framing), and only
# ever send JSON-encoded payloads of primitives. The player subprocess
# converts every return value -- action, bid, commentary -- into a structure
# of ints, strings, bools, None, and lists/dicts of those, using strict
# `type(x) is C` identity checks. Anything that doesn't validate is sent as
# a structured "invalid" frame, and the engine treats the turn as failed.
#
# The opposite direction (engine -> player) keeps multiprocessing.Queue.
# The engine controls what goes through, so pickle is safe there.

def _safe_dir(d):
    if d is None:
        return None
    if type(d) is Direction:
        return d.name
    raise ValueError(f"bad direction type: {type(d).__name__}")


def _safe_move_type(mt):
    if type(mt) is MoveType:
        return int(mt)
    raise ValueError(f"bad move_type: {type(mt).__name__}")


def _safe_loc(loc):
    if loc is None:
        return None
    if type(loc) is Location:
        return [int(loc.r), int(loc.c)]
    raise ValueError(f"bad location type: {type(loc).__name__}")


def _safe_action(action):
    a_type = type(action)
    if a_type is Action.Move:
        if type(action.place_beacon) is not bool:
            raise ValueError("place_beacon not bool")
        return {
            "name": "Move",
            "direction": _safe_dir(action.direction),
            "move_type": _safe_move_type(action.move_type),
            "place_beacon": action.place_beacon,
            "beacon_target": _safe_loc(action.beacon_target),
        }
    if a_type is Action.Paint:
        return {"name": "Paint", "location": _safe_loc(action.location)}
    raise ValueError(f"bad action type: {a_type.__name__}")


def _safe_player_move(pm):
    if pm is None:
        return None
    pm_type = type(pm)
    if pm_type is Action.Move or pm_type is Action.Paint:
        return [_safe_action(pm)]
    if pm_type is list or pm_type is tuple:
        out = []
        for a in pm:
            out.append(_safe_action(a))
        return out
    raise ValueError(f"bad player_move type: {pm_type.__name__}")


def _safe_bid(b):
    bt = type(b)
    if bt is int or bt is float:
        return b
    raise ValueError(f"bad bid type: {bt.__name__}")


def _safe_commentary(c):
    if type(c) is str:
        return c
    raise ValueError(f"bad commentary type: {type(c).__name__}")


# Engine-side inverse. Runs in the trusted main process on a dict tree that
# json.loads has already produced, so there are no metaclass / __reduce__
# surprises -- just standard type checks.

def _from_safe_dir(s):
    if s is None:
        return None
    if isinstance(s, str) and s in Direction.__members__:
        return Direction[s]
    raise ValueError("bad direction")


def _from_safe_move_type(v):
    if isinstance(v, bool):
        raise ValueError("bad move_type (bool)")
    if isinstance(v, int) and v in (0, 1, 2):
        return MoveType(v)
    raise ValueError("bad move_type")


def _from_safe_loc(v):
    if v is None:
        return None
    if (isinstance(v, list) and len(v) == 2
            and all(isinstance(x, int) and not isinstance(x, bool) for x in v)):
        return Location(v[0], v[1])
    raise ValueError("bad location")


def _from_safe_action(d):
    if not isinstance(d, dict):
        raise ValueError("action not a dict")
    name = d.get("name")
    if name == "Move":
        pb = d.get("place_beacon")
        if not isinstance(pb, bool):
            raise ValueError("bad place_beacon")
        return Action.Move(
            direction=_from_safe_dir(d.get("direction")),
            move_type=_from_safe_move_type(d.get("move_type")),
            place_beacon=pb,
            beacon_target=_from_safe_loc(d.get("beacon_target")),
        )
    if name == "Paint":
        return Action.Paint(_from_safe_loc(d.get("location")))
    raise ValueError(f"bad action name: {name!r}")


def _from_safe_player_move(spec):
    if spec is None:
        return None
    if not isinstance(spec, list):
        raise ValueError("player_move not a list")
    if len(spec) == 1:
        return _from_safe_action(spec[0])
    return [_from_safe_action(a) for a in spec]


# Wire framing. Each frame is a JSON dict with a "kind" discriminator:
#   {"kind": "ready"}                                  (subprocess startup)
#   {"kind": "<op>_ok", "value": ..., "timer": float, "msg": str}
#   {"kind": "<op>_invalid", "msg": "Invalid turn"}    (validation rejected)
#   {"kind": "<op>_exception", "msg": "<traceback>"}   (player raised)
#   {"kind": "<op>_memory" | "<op>_vram", "msg": "..."}
#   {"kind": "<op>_fail", "msg": "<traceback>"}        (engine-side bug)
# where <op> in {construct, play, bid, commentate}.

def _send_frame(conn, payload):
    try:
        data = json.dumps(payload).encode("utf-8")
    except (TypeError, ValueError):
        data = json.dumps({"kind": "invalid_serialization"}).encode("utf-8")
    conn.send_bytes(data)


def _recv_frame(conn, timeout):
    if not conn.poll(timeout):
        raise TimeoutError("player did not respond in time")
    raw = conn.recv_bytes()
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"malformed player frame: {e}")


# starts up a player process ready to recieve instructions
def run_player_process(player_name, submission_dir, player_queue,
                       result_conn, limit_resources, use_gpu, out_queue,
                       user_name=None, group_name=None):
    
    
    # try:
    import traceback
    import sys
    import importlib
    import os
    import tempfile

    import psutil

    # Pin perf_counter into a closure local BEFORE the player module is
    # imported (vuln 3). Any subsequent time.perf_counter = ... by player
    # code is ignored because get_cur_time() uses this name, not the
    # attribute lookup on the time module.
    perf_counter = _real_perf_counter

    sys.path.append(submission_dir)

    # numba_cache_root = os.path.join(submission_dir, ".numba_cache")
    # try:
    #     os.makedirs(numba_cache_root, exist_ok=True)
    # except Exception:
    #     numba_cache_root = tempfile.mkdtemp(prefix="numba_cache_")
    # os.environ.setdefault("NUMBA_CACHE_DIR", numba_cache_root)
    # os.environ.setdefault("NUMBA_TEMP_DIR", numba_cache_root)
    
    if(use_gpu):
        import pynvml
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # GPU 0

    limit_mb = 1536
    limit_bytes = limit_mb * 1024 * 1024 #set limit to 1 gb
    
    def checkMemory():
        pid = os.getpid()
        process = psutil.Process(pid)

        total_memory = process.memory_info().rss

        for child in process.children(recursive=True):
            total_memory += child.memory_info().rss

        if limit_resources and total_memory > limit_bytes:
            raise MemoryError("Allocated too much memory on physical RAM")
        
        return total_memory
    
    # Set your VRAM limit in bytes
    vram_limit_bytes = 4 * 1024**3  # 4 GB
    def checkVRAM():
        if(use_gpu):
            pid = os.getpid()
            
            # Get current process + all child PIDs
            process = psutil.Process(pid)
            pids = [process.pid] + [child.pid for child in process.children(recursive=True)]

            total_vram = 0
            for proc in pynvml.nvmlDeviceGetComputeRunningProcesses(handle):
                if proc.pid in pids:
                    total_vram += proc.usedGpuMemory  # in bytes                

            if limit_resources and total_vram > vram_limit_bytes:
                raise MemoryError("Allocated too much VRAM on GPU")

            return total_vram
        return 0
    
    def get_cur_time():
        return perf_counter()


    if(limit_resources):
        import resource
        resource.setrlimit(resource.RLIMIT_RSS, (limit_bytes, limit_bytes)) # only allow current process to run
        
        drop_priveliges(user_name, group_name)
        apply_seccomp()
    else:
        class QueueWriter:
            def __init__(self, queue):
                self.queue = queue
                self.turn = ""

            def set_turn(self, t):
                self.turn = t

            def write(self, message):
                # This method is called by print, we send message to out_queue
                if message != '\n':  # Ignore empty newlines that can be printed
                    self.queue.put("".join(["[", player_name," | ", self.turn, "]: ", message]))

            def flush(self):
                pass
    
        printer = QueueWriter(out_queue)
        sys.stdout = printer

        
    importlib.import_module(player_name)
    module = importlib.import_module(player_name+".controller")

    
    # Signal that the subprocess loaded and is ready to take commands.
    # Sent over the JSON pipe so the engine never has to pickle-deserialize
    # anything the player process produced (vuln 5).
    _send_frame(result_conn, {"kind": "ready"})

    def perform_memory_checks(op):
        """Return a failure-frame dict if a limit is exceeded, else None."""
        try:
            checkMemory()
        except MemoryError:
            print(traceback.format_exc())
            return {"kind": f"{op}_memory", "msg": traceback.format_exc()}
        try:
            checkVRAM()
        except MemoryError:
            print(traceback.format_exc())
            return {"kind": f"{op}_vram", "msg": traceback.format_exc()}
        return None

    def controller_play(player_controller):
        try:
            board_state, player_parity, time_left = player_queue.get()
            if(not limit_resources):
                try:
                    turn_label = board_state.turn_count
                except AttributeError:
                    turn_label = "?"
                printer.set_turn(f"turn #{turn_label}")

            try:
                start = get_cur_time()
                def time_left_func():
                    return time_left - (get_cur_time() - start)
                player_move = player_controller.play(board_state, player_parity, time_left_func)
                stop = get_cur_time()
            except:
                print(traceback.format_exc())
                return {"kind": "play_exception", "msg": traceback.format_exc()}

            mem_fail = perform_memory_checks("play")
            if mem_fail is not None:
                return mem_fail

            # Strictly validate the player's return value and reduce it to
            # JSON-safe primitives before sending. Anything weird -> invalid
            # turn (vuln 5).
            try:
                safe_move = _safe_player_move(player_move)
            except (ValueError, AttributeError, TypeError):
                return {"kind": "play_invalid", "msg": _INVALID_TURN_MSG}

            return {"kind": "play_ok", "value": safe_move,
                    "timer": stop - start, "msg": ""}

        except:
            return {"kind": "play_fail", "msg": traceback.format_exc()}

    def controller_bid(player_controller):
        try:
            board_state, player_parity, time_left = player_queue.get()
            if(not limit_resources):
                printer.set_turn("bid")

            try:
                start = get_cur_time()
                def time_left_func():
                    return time_left - (get_cur_time() - start)
                bid_value = player_controller.bid(board_state, player_parity, time_left_func)
                stop = get_cur_time()
            except:
                print(traceback.format_exc())
                return {"kind": "bid_exception", "msg": traceback.format_exc()}

            mem_fail = perform_memory_checks("bid")
            if mem_fail is not None:
                return mem_fail

            try:
                safe_bid = _safe_bid(bid_value)
            except (ValueError, AttributeError, TypeError):
                return {"kind": "bid_invalid", "msg": _INVALID_TURN_MSG}

            return {"kind": "bid_ok", "value": safe_bid,
                    "timer": stop - start, "msg": ""}
        except:
            return {"kind": "bid_fail", "msg": traceback.format_exc()}

    def controller_commentate(player_controller):
        try:
            if(not limit_resources):
                printer.set_turn("commentate")

            board_state, player_parity, time_left = player_queue.get()

            try:
                start = get_cur_time()
                def time_left_func():
                    return time_left - (get_cur_time() - start)
                commentary = player_controller.commentate(board_state, player_parity, time_left_func)
                stop = get_cur_time()
            except:
                return {"kind": "commentate_exception", "msg": traceback.format_exc()}

            mem_fail = perform_memory_checks("commentate")
            if mem_fail is not None:
                return mem_fail

            try:
                safe_commentary = _safe_commentary(commentary)
            except (ValueError, AttributeError, TypeError):
                return {"kind": "commentate_invalid", "msg": _INVALID_TURN_MSG}

            return {"kind": "commentate_ok", "value": safe_commentary,
                    "timer": stop - start, "msg": ""}
        except:
            print(traceback.format_exc())
            return {"kind": "commentate_fail", "msg": traceback.format_exc()}


    player_controller = None
    while True:
        func = player_queue.get()

        payload = None
        if(func == "construct"):
            try:
                if(not limit_resources):
                    printer.set_turn("construct")

                player_parity, time_left = player_queue.get()

                try:
                    start = get_cur_time()
                    def time_left_func():
                        return time_left - (get_cur_time() - start)
                    player_controller = module.PlayerController(player_parity, time_left_func)
                    stop = get_cur_time()

                    payload = {"kind": "construct_ok", "timer": stop - start, "msg": ""}
                except:
                    payload = {"kind": "construct_exception", "msg": traceback.format_exc()}

                mem_fail = perform_memory_checks("construct")
                if mem_fail is not None:
                    payload = mem_fail

            except:
                print(traceback.format_exc())
                payload = {"kind": "construct_fail", "msg": traceback.format_exc()}
        elif(func == "play"):
            payload = controller_play(player_controller)
        elif(func == "bid"):
            payload = controller_bid(player_controller)
        elif(func == "commentate"):
            payload = controller_commentate(player_controller)
        else:
            payload = {"kind": "unknown_command", "msg": str(func)[:200]}

        _send_frame(result_conn, payload)
            


class PlayerProcess:
    def __init__(self, is_player_a, player_name, submission_dir, player_queue,
                 limit_resources, use_gpu, out_queue,
                 user_name=None, group_name=None):
        # Player -> engine results travel over a multiprocessing.Pipe using
        # send_bytes / recv_bytes (no pickle on payloads). JSON validation and
        # Action reconstruction happen in this process, on already-parsed
        # primitives, so the legacy pickle-RCE vector is closed (vuln 5).
        self._result_recv, self._result_send = Pipe(duplex=False)
        self.process = Process(
            target=run_player_process,
            args=(player_name, submission_dir, player_queue,
                  self._result_send, limit_resources, use_gpu, out_queue,
                  user_name, group_name))
        self.player_queue = player_queue
        self.is_player_a = is_player_a
        self.limit_resources = limit_resources

    def start(self):
        self.process.start()

    def wait_ready(self, timeout):
        """True if the subprocess sent a well-formed `ready` frame within
        `timeout` seconds. False on timeout, EOF, or any malformed frame."""
        try:
            frame = _recv_frame(self._result_recv, timeout)
        except (TimeoutError, ValueError, EOFError, OSError):
            return False
        return isinstance(frame, dict) and frame.get("kind") == "ready"

    def _recv(self, timeout):
        """Read a frame; returns (frame_dict, error_message) where exactly one
        is non-None. Engine code never sees a partially-validated dict."""
        try:
            return _recv_frame(self._result_recv, timeout), None
        except TimeoutError:
            return None, "Timeout"
        except (ValueError, EOFError, OSError) as e:
            return None, f"Player IPC error: {e}"

    # runs player construct command
    def run_timed_constructor(self, timeout, player_parity, extra_ret_time):
        self.player_queue.put("construct")
        self.player_queue.put((player_parity, timeout))

        frame, err = self._recv(timeout + extra_ret_time)
        if frame is None:
            print(f"run_timed_constructor: {err}")
            return False, err
        kind = frame.get("kind")
        if kind == "construct_ok":
            timer = frame.get("timer", -1)
            if not isinstance(timer, (int, float)):
                return False, _INVALID_TURN_MSG
            return timer < timeout, frame.get("msg", "")
        if kind in ("construct_exception", "construct_memory", "construct_vram"):
            return False, frame.get("msg", "")
        if kind == "construct_fail":
            raise RuntimeError(
                f"Something went wrong while running player constructor.\n {frame.get('msg', '')}")
        return False, f"Unexpected frame: {kind!r}"

    def run_timed_bid(self, board_state, player_parity, timeout, extra_ret_time):
        self.player_queue.put("bid")
        self.player_queue.put((board_state, player_parity, timeout))

        frame, err = self._recv(timeout + extra_ret_time)
        if frame is None:
            print(f"run_timed_bid: {err}")
            return None, timeout, err
        kind = frame.get("kind")
        if kind == "bid_ok":
            value = frame.get("value")
            timer = frame.get("timer", -1)
            # Reject bool here because isinstance(True, int) is True in Python
            # and we don't want a `True` bid sneaking through as 1.
            if (not isinstance(value, (int, float)) or isinstance(value, bool)
                    or not isinstance(timer, (int, float))):
                return None, -1, _INVALID_TURN_MSG
            if timer < timeout:
                return value, timer, frame.get("msg", "")
            return None, timeout, "Timeout"
        if kind == "bid_invalid":
            print("Player bid did not validate")
            return None, -1, frame.get("msg", _INVALID_TURN_MSG)
        if kind == "bid_exception":
            print("Player bid caused exception")
            return None, -1, frame.get("msg", "")
        if kind in ("bid_memory", "bid_vram"):
            print("Memory error")
            return None, -2, frame.get("msg", "")
        if kind == "bid_fail":
            raise RuntimeError(
                f"Something went wrong while running player bid. \n{frame.get('msg', '')}")
        return None, -1, f"Unexpected frame: {kind!r}"

    # runs player play command
    def run_timed_play(self, board_state, player_parity, timeout, extra_ret_time):
        self.player_queue.put("play")
        self.player_queue.put((board_state, player_parity, timeout))

        frame, err = self._recv(timeout + extra_ret_time)
        if frame is None:
            print(f"run_timed_play: {err}")
            return None, timeout, err
        kind = frame.get("kind")
        if kind == "play_ok":
            timer = frame.get("timer", -1)
            if not isinstance(timer, (int, float)):
                return None, -1, _INVALID_TURN_MSG
            try:
                actions = _from_safe_player_move(frame.get("value"))
            except (ValueError, TypeError, KeyError):
                print("Player play did not validate")
                return None, -1, _INVALID_TURN_MSG
            if timer < timeout:
                return actions, timer, frame.get("msg", "")
            return None, timeout, "Timeout"
        if kind == "play_invalid":
            print("Player play did not validate")
            return None, -1, frame.get("msg", _INVALID_TURN_MSG)
        if kind == "play_exception":
            print("Player code caused exception")
            return None, -1, frame.get("msg", "")
        if kind in ("play_memory", "play_vram"):
            print("Memory error")
            return None, -2, frame.get("msg", "")
        if kind == "play_fail":
            raise RuntimeError(
                f"Something went wrong while running player move. \n{frame.get('msg', '')}")
        return None, -1, f"Unexpected frame: {kind!r}"

    # runs player commentate command
    def run_timed_commentate(self, board_state, player_parity, timeout, extra_ret_time):
        self.player_queue.put("commentate")
        self.player_queue.put((board_state, player_parity, timeout))

        frame, err = self._recv(timeout + extra_ret_time)
        if frame is None:
            print(f"run_timed_commentate: {err}")
            return "", timeout, err
        kind = frame.get("kind")
        if kind == "commentate_ok":
            value = frame.get("value", "")
            timer = frame.get("timer", -1)
            if not isinstance(value, str) or not isinstance(timer, (int, float)):
                return "", -1, _INVALID_TURN_MSG
            if timer < timeout:
                return value, timer, frame.get("msg", "")
            return "", timeout, "Timeout"
        if kind == "commentate_invalid":
            return "", -1, frame.get("msg", _INVALID_TURN_MSG)
        if kind == "commentate_exception":
            return "", -1, frame.get("msg", "")
        if kind in ("commentate_memory", "commentate_vram"):
            return "", -2, frame.get("msg", "")
        if kind == "commentate_fail":
            raise RuntimeError(
                f"Something went wrong while running player commentary. \n{frame.get('msg', '')}")
        return "", -1, f"Unexpected frame: {kind!r}"



    def terminate_process_and_children(self):
        import psutil
        # Find the process by PID
        pid = self.process.pid  
        parent_process = None
        children = None
        try:
            parent_process = psutil.Process(pid)
        except psutil.NoSuchProcess as e:
            print(f"Process has already been closed.")
        
        if(not parent_process is None):
            children = parent_process.children(recursive=True)

        # Kill the parent process
        if not parent_process is None and parent_process.is_running():
            try:
                parent_process.terminate()
            except psutil.NoSuchProcess as e:
                print(f"Process has already been closed.")
            except Exception as e:
                print(f"Error while killing process: {e}")    
        
        if not children is None:
            for child in children:
                if child.is_running():
                    try:
                        child.terminate()

                    except psutil.NoSuchProcess as e:
                        print(f"Process  does not exist.")
                    except Exception as e:
                        print(f"Error while killing process: {e}")

        if not parent_process is None and parent_process.is_running():
            try:
                parent_process.kill()   
            except psutil.NoSuchProcess:
                print(f"Process  does not exist.")
            except Exception as e:
                print(f"Error while killing process: {e}")  

        if not children is None:
            for child in children:
                if child.is_running():
                    try:
                        child.kill()   
                    except psutil.NoSuchProcess:
                        print(f"Process  does not exist.")
                    except Exception as e:
                        print(f"Error while killing process: {e}")


    def pause_process_and_children(self):
        # Find the process by PID
        if(self.limit_resources):
            import time
            import signal
            import os
            import psutil
            try:
                pid = self.process.pid
                parent_process = psutil.Process(pid)
                
                children = parent_process.children(recursive=True)
                
                # send sigstop to parent process
                if parent_process.is_running():
                    try:
                        os.kill(pid, signal.SIGSTOP)
                    except psutil.NoSuchProcess:
                        print(f"Process  does not exist.")
                    except Exception as e:
                        print(f"Error while killing process: {e}")    

                i = 0
                while(parent_process.status() == psutil.STATUS_RUNNING and i < 50):
                    time.sleep(0.001) 
                    i+=1
                if(parent_process.status() == psutil.STATUS_RUNNING):
                    os.kill(parent_process.pid, signal.SIGKILL)   

                for child in children:
                    if child.is_running():
                        try:
                            os.kill(child.pid, signal.SIGSTOP)
                        except psutil.NoSuchProcess:
                            print(f"Process  does not exist.")
                        except Exception as e:
                            print(f"Error while killing process: {e}")    
                
                for child in children:
                    i = 0
                    while(child.status() == psutil.STATUS_RUNNING and i < 50):
                        time.sleep(0.001) 
                        i+=1
                    if(child.status()== psutil.STATUS_RUNNING):
                        os.kill(child.pid, signal.SIGKILL)

            except:
                print("error pausing processes")


    def restart_process_and_children(self):
        if(self.limit_resources):  
            import psutil
            import os
            import time
            import signal      
            pid = self.process.pid
            parent_process = psutil.Process(pid)
            
            children = parent_process.children(recursive=True)

            try:

                for child in children:
                    if child.is_running():
                        try:
                            os.kill(child.pid, signal.SIGCONT)
                        except psutil.NoSuchProcess:
                            print(f"Process does not exist.")
                        except Exception as e:
                            print(f"Error while killing process: {e}") 

                for child in children:
                    i = 0
                    while(child.status() == psutil.STATUS_STOPPED and i < 50):
                        time.sleep(0.001) 
                        i+=1
        
                
                # send sigstop to parent process
                if parent_process.is_running():
                    try:
                        os.kill(pid, signal.SIGCONT)
                    except psutil.NoSuchProcess:
                        print(f"Process does not exist.")
                    except Exception as e:
                        print(f"Error while killing process: {e}")    

            
                i = 0
                while(parent_process.status() == psutil.STATUS_STOPPED and i < 50):
                    time.sleep(0.001) 
                    i+=1
            
                
            except:
                print("error restarting processes")

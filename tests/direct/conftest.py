"""Windows-safe setup for genlayer-test's direct-mode loader."""
import os
import tempfile

from gltest.direct import loader
from gltest.direct.vm import VMContext


def _message_injection_keeps_temp_file_until_cleanup(vm):
    try:
        from genlayer.py import calldata
        from genlayer.py.types import Address
    except ImportError:
        return
    sender = Address(vm.sender) if isinstance(vm.sender, bytes) else vm.sender
    contract_address = Address(vm._contract_address) if isinstance(vm._contract_address, bytes) else vm._contract_address
    origin = Address(vm.origin) if isinstance(vm.origin, bytes) else vm.origin
    message = {
        'contract_address': contract_address,
        'sender_address': sender,
        'origin_address': origin,
        'stack': [],
        'value': vm._value,
        'datetime': vm._datetime,
        'is_init': False,
        'chain_id': vm._chain_id,
        'entry_kind': 0,
        'entry_data': b'',
        'entry_stage_data': None,
    }
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, calldata.encode(message))
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        paths = getattr(vm, '_quorum_temp_message_paths', [])
        paths.append(path)
        vm._quorum_temp_message_paths = paths
    finally:
        os.close(fd)


_original_cleanup = VMContext._cleanup_after_deactivate


def _cleanup_after_temp_messages(vm):
    _original_cleanup(vm)
    for path in getattr(vm, '_quorum_temp_message_paths', []):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    vm._quorum_temp_message_paths = []


loader._inject_message_to_fd0 = _message_injection_keeps_temp_file_until_cleanup
VMContext._cleanup_after_deactivate = _cleanup_after_temp_messages

"""User-scoped Windows generic credential, accessed through the native API."""
import ctypes
from ctypes import wintypes
import os

TARGET = 'MangaLocalTranslator/GoogleCloudTranslation'


class Credential(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]


def api():
    dll = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    dll.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                              ctypes.POINTER(ctypes.POINTER(Credential))]
    dll.CredReadW.restype = wintypes.BOOL
    dll.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
    dll.CredWriteW.restype = wintypes.BOOL
    dll.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    dll.CredDeleteW.restype = wintypes.BOOL
    dll.CredFree.argtypes = [ctypes.c_void_p]
    dll.CredFree.restype = None
    return dll


def read_key():
    dll = api()
    pointer = ctypes.POINTER(Credential)()
    if not dll.CredReadW(TARGET, 1, 0, ctypes.byref(pointer)):
        if ctypes.get_last_error() == 1168:
            return ''
        raise OSError('Windows Credential Manager could not read the saved key.')
    try:
        item = pointer.contents
        try:
            return ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize).decode('utf-16-le')
        except UnicodeError:
            raise OSError('The saved credential is unreadable. Replace it using Configure Google API Key.') from None
    finally:
        dll.CredFree(pointer)


def write_key(value):
    value = value.strip()
    blob = value.encode('utf-16-le')
    if not value or len(blob) > 2560:
        raise ValueError('Enter a nonempty API key shorter than 1280 characters.')
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    item = Credential(Type=1, TargetName=TARGET, CredentialBlobSize=len(blob),
                      CredentialBlob=buffer, Persist=2, UserName='MangaLocalTranslator')
    if not api().CredWriteW(ctypes.byref(item), 0):
        raise OSError('Windows Credential Manager could not save the key.')


def delete_key():
    if not api().CredDeleteW(TARGET, 1, 0) and ctypes.get_last_error() != 1168:
        raise OSError('Windows Credential Manager could not delete the saved key.')


def available_key():
    return os.environ.get('MANGA_GOOGLE_TRANSLATE_API_KEY', '').strip() or read_key()

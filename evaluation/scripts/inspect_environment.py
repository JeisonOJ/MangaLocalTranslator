import ctypes,json,platform,winreg,pathlib,shutil,sys
class Memory(ctypes.Structure):
 _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total_phys','avail_phys','total_page','avail_page','total_virtual','avail_virtual','avail_extended']]
m=Memory();m.length=ctypes.sizeof(m);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'HARDWARE\DESCRIPTION\System\CentralProcessor\0') as k: cpu=winreg.QueryValueEx(k,'ProcessorNameString')[0]
d={'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'cpu':cpu,'memory':{n:getattr(m,n) for n in ['total_phys','avail_phys','load']},'disk':shutil.disk_usage('.')._asdict()}
pathlib.Path('evaluation/environment.json').write_text(json.dumps(d,indent=2));print(json.dumps(d,indent=2))

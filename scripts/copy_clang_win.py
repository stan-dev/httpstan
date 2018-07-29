import os
import shutil

# copy clang-cl.exe to cl.exe
src = os.popen("where clang-cl.exe").read().strip().splitlines()[0].strip()
src = os.path.normpath(os.path.abspath(src))
#dst, _ = os.path.split(src)
#dst = os.path.join(dst, "cl.exe")
dst = "C:\\Program Files (x86)\\Microsoft Visual Studio 14.0\\VC\\BIN\\x86_amd64\\cl.exe"
shutil.copy2(src, dst)
print("copied {} to {}".format(src, dst))

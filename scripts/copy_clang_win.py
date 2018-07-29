import os
import shutil

# copy clang-cl.exe to cl.exe
src = os.popen("which clang-cl.exe").read().strip()
src = os.path.normpath(os.path.abspath(src))
dst, _ = os.path.split(src)
dst = os.path.join(dst, "cl.exe")
shutil.copy2(src, dst)
print("copied {} to {}".format(src, dst))

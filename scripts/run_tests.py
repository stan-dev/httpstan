from glob import glob
import subprocess
import os
import re
import sys

# see https://stackoverflow.com/a/24131590
if sys.platform.startswith("win"):
    # Don't display the Windows GPF dialog if the invoked program dies.
    # See comp.os.ms-windows.programmer.win32
    #  How to suppress crash notification dialog?, Jan 14,2004 -
    #     Raymond Chen's response [1]

    import ctypes

    SEM_NOGPFAULTERRORBOX = 0x0002  # From MSDN
    ctypes.windll.kernel32.SetErrorMode(SEM_NOGPFAULTERRORBOX)
    CREATE_NO_WINDOW = 0x08000000  # From Windows API
    subprocess_flags = CREATE_NO_WINDOW
else:
    subprocess_flags = 0

argv = sys.argv[1:]
if len(argv):
    testfiles = glob(argv[0])
else:
    testfiles = glob("tests/test_*.py")
print("\n".join(testfiles))
# gather results
passed = []
failures = []
failing_names = []
for testfile in testfiles:
    command = ["py.test", os.path.abspath(testfile)]
    print(" ".join(command), flush=True)
    process = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=600,
        creationflags=subprocess_flags,
    )

    # use re to find summaryline
    pattern = "=+.*passed.*=+"
    string = process.stdout.decode("utf-8")
    passed_line = re.findall(pattern, string)
    if not passed_line:
        failing_names.append(testfile)
        passed_line = [""]
    # parse the summary line for passed and failures
    for line in passed_line:
        numbers = re.findall("\s([0-9]*)\s*passed", line)
        if not len(numbers):
            numbers = ["0"]
        elif len(numbers) > 1:
            print(
                "Found too many numbers in passed, be wary of the results given at the end:",
                numbers,
            )
        passed.append(int(numbers[0]))

        numbers = re.findall("\s([0-9]*)\s*failed", line)
        if numbers:
            failing_names.append(os.path.basename(testfile))
        if not len(numbers):
            numbers = ["0"]
        elif len(numbers) > 1:
            print(
                "Found too many numbers in failures, be wary of the results given at the end:",
                numbers,
            )
        failures.append(int(numbers[0]))

    if len(passed_line) == 1:
        print(passed_line[0])
    else:
        print("\n".join(passed_line))
    if len(process.stderr):
        print("There was an error:")
        print(process.stderr.decode("utf-8"))

print("\n\n==============================================================================")
print("==============================================================================")
print("Testing done\n")
print("Passed tests: " + " ".join(map(str, passed)))
print(f"PASSED: {sum(passed)}/{sum(passed)+sum(failures)} were successful\n\n")
print("Failed tests: " + " ".join(map(str, failures)))
for fname in failing_names:
    print(f"Failed: {fname}")
print(f"FAILED: {sum(failures)}/{sum(passed)+sum(failures)} were failing")
print("==============================================================================")
print("==============================================================================\n\n")
# exit script
if sum(failures):
    sys.exit(1)
else:
    sys.exit(0)

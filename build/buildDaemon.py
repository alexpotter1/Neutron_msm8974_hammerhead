#!/usr/bin/env python3

'''
Build Daemon for the Neutron Kernel compilation process.
Designed to run on Debian (Linux) enviroments;  this will fail on other OSes.
Copyright Alex Potter 2015.
'''

import sys
import subprocess
import time
import datetime
import os
import sqlite3
import threading
import re
import itertools
import glob

class bcolours:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class InitStub:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.CPUcores = None
        self.CPUversion = None
        self.localversion = "-Neutron-"
        self.dt = None
        self.dtbSucceeded = None
        self.lines = None
        self.spinnerShutdown = None
        self.data = None
        self.checkEnv()

    def spinner(self):
        spinner = itertools.cycle(['-','/','|','\\'])
        import time
        while self.spinnerShutdown == 0:
            sys.stdout.write(next(spinner))
            sys.stdout.flush()
            sys.stdout.write('\b')
            time.sleep(0.15)
        return

    def checkEnv(self):
        # Checking CPU info
        p = subprocess.Popen("grep -c ^processor /proc/cpuinfo", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in iter(p.stdout.readline, b''):
            self.CPUcores = int(line.rstrip())

        p = subprocess.Popen('cat /proc/cpuinfo | grep "model name"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in iter(p.stdout.readline, b''):
            self.CPUversion = line.rstrip()

        # Check for build tools
        print("Checking build environment...")
        time.sleep(0.8)
        p = subprocess.Popen("apt --installed list", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = p.communicate()
        outString = str(output)

        InstallList = ["bison", "build-essential", "curl", "flex", "git", "gnupg", "gperf",
        "libesd0-dev", "liblz4-tool", "libncurses5-dev", "libsdl1.2-dev", "libwxgtk2.8-dev",
        "libxml2", "libxml2-utils", "lzop", "openjdk-7-jdk", "openjdk-7-jre", "pngcrush",
        "schedtool", "squashfs-tools", "xsltproc", "zip", "g++-multilib",
        "gcc-multilib", "lib32ncurses5-dev", "lib32readline-gplv2-dev", "lib32z1-dev", "pv", "openjdk-7-jre-headless", "abootimg"]

        for program in InstallList:
            if not program in outString:
                subprocess.call("sudo apt-get install %s" % program, shell=True)
                #subprocess.call("sudo apt-get install openjdk-7-jre-headless", shell=True)
        print(bcolours.OKGREEN + "OK: Build Environment" + bcolours.ENDC)

        print("Checking Java version...")
        if os.path.isfile("/usr/bin/java"):
            time.sleep(0.5)
            p = subprocess.Popen("java -version", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = p.communicate()
            outString = str(err)[2:]
            outString = outString[:-1]
            if '"1.7.0' in outString and "OpenJDK" in outString:
                print(bcolours.OKGREEN + "OK: Java Runtime Environment version: OpenJDK 1.7.0" + bcolours.ENDC)
            else:
                print(outString)
                print(bcolours.WARNING + "WARNING: Check Java version before continuing" + bcolours.ENDC)
                raise SystemExit

        else:
            print(bcolours.FAIL + "FAIL: Java not installed" + bcolours.ENDC)
            print("Installing OpenJDK 7...")
            subprocess.call("sudo apt-get install openjdk-7-jre openjdk-7-jdk openjdk-7-jre-headless", shell=True)

        self.checkEnvVariables()
    def checkEnvVariables(self):
        CROSS_COMPILE = os.environ.get('CROSS_COMPILE')
        print("Checking toolchain path...")
        time.sleep(0.5)
        if CROSS_COMPILE == None:
            print(bcolours.FAIL + "FAIL: Toolchain path not set. Compilation will fail." + bcolours.ENDC)
        else:
            print(bcolours.OKGREEN + "OK: Toolchain path" + bcolours.ENDC)
            print(bcolours.OKBLUE + "Using toolchain path %s" % CROSS_COMPILE + bcolours.ENDC)

            self.conn = sqlite3.connect("build/neutronBuild.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute("CREATE TABLE IF NOT EXISTS UserDefaults (VariableKey TEXT, StringChoice TEXT);")
            self.cursor.execute('SELECT * FROM {tn} WHERE {cn}="SaberMod"'.format(tn="UserDefaults", cn="VariableKey"))
            data = self.cursor.fetchall()
            if len(data) == 0:
                sabermod_choice = input("Are you using a SaberMod GCC toolchain? (y/n): ")
                self.cursor.execute("INSERT INTO UserDefaults VALUES (?, ?);", ("SaberMod", sabermod_choice.upper()))
                self.conn.commit()

            self.cursor.execute('SELECT * FROM {tn} WHERE {cn}="SaberMod"'.format(tn="UserDefaults", cn="VariableKey"))
            data = self.cursor.fetchall()
            SaberMod_persistent_choice = data[0][1]

            if SaberMod_persistent_choice == "Y":
                if not os.path.isdir("/usr/include/cloog") or not os.path.isfile("/usr/lib/libisl.a"):
                    print(bcolours.FAIL + "FAIL: Extra SaberMod prebuilts are not installed correctly." + bcolours.ENDC)
                else:
                    print(bcolours.OKGREEN + "OK: SaberMod libraries detected" + bcolours.ENDC)

            self.spinnerShutdown = 0
            spinningThread = threading.Thread(target=self.spinner)
            spinningThread.start()
            time.sleep(3.5)
            self.spinnerShutdown = 1

            subprocess.call("clear", shell=True)

            self.setupBuildPrelim()

    def setupBuild(self, error=None):
        time.sleep(1)
        os.environ['ARCH']="arm"
        os.environ['SUBARCH']="arm"
        if os.path.isfile("arch/arm/boot/zImage-dtb") or os.path.isfile("arch/arm/boot/zImage"):
            choice = input("Previous kernel zImage found. Do you want to make clean? (y/n):")
            if choice.upper() == "N":
                error = 1
                self.buildInit(zImageExists=True)
        if error == None:
            print("Last build was successful. Running make clean...")
            self.spinnerShutdown = 0
            spinnerThread = threading.Thread(target=self.spinner)
            spinnerThread.start()
            time.sleep(0.5)
            p = subprocess.Popen("make clean && make mrproper", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = p.communicate()
            rc = p.returncode
            if rc == 0:
                if os.path.isfile("/arch/arm/boot/compressed/piggy.lz4"):
                    subprocess.call("rm /arch/arm/boot/compressed/piggy.lz4")
                if os.path.isfile("arch/arm/boot/zImage"):
                    subprocess.call("rm arch/arm/boot/zImage && rm arch/arm/boot/zImage-dtb", shell=True)
                if os.path.isfile("zip/setup/zImage-dtb"):
                    subprocess.call("rm zip/Neutron*", shell=True)
                    subprocess.call("rm zip/setup/zImage-dtb", shell=True)
                if not os.listdir("zip/modules") == []:
                    subprocess.call("cd zip/modules; rm *", shell=True)
                print(bcolours.OKGREEN + "OK: Cleaned build directories" + bcolours.ENDC)
            else:
                print(bcolours.WARNING + "WARNING: make clean failed" + bcolours.ENDC)
            self.spinnerShutdown = 1


            self.localversion += str(input("Enter new version string: "))
            self.buildInit(localversionarg=1) # use the localversion that the user entered
        else:
            self.buildInit(localversionarg=0) # use the localversion that is stored in SQLite db

    def setupBuildPrelim(self):
        print("---------------------------------------------------------------------------------")
        print(bcolours.HEADER + "Neutron Build preparation" + bcolours.ENDC)
        print("---------------------------------------------------------------------------------")
        time.sleep(1)

        self.cursor.execute("CREATE TABLE IF NOT EXISTS BuildFailure (FailureReason TEXT, FileName TEXT, KernelVersion TEXT, DateTime TEXT)")
        self.cursor.execute('SELECT * FROM {tn} WHERE {cn}="Compile Error"'.format(tn="BuildFailure", cn="FailureReason"))
        self.data = self.cursor.fetchall()
        if len(self.data) == 0:
            self.cursor.execute('SELECT * FROM {tn} WHERE {cn}="Linker Error"'.format(tn="BuildFailure", cn="FailureReason"))
            dataLinker = self.cursor.fetchall()
            if len(dataLinker) == 0:
                self.setupBuild()
            else:
                print(bcolours.FAIL + "An incomplete build was detected." + bcolours.ENDC)
                print("Error Reason: %s" % data[0][0])
                print("File Name: %s" % data[0][1])
                print("Kernel Version: %s" % data[0][2])
                print("Date: %s" % data[0][3])
                print("---------------------------------------------------------------------------------")

                self.cursor.execute('DELETE FROM {tn} WHERE {cn}="Linker Error"'.format(tn='BuildFailure', cn="FailureReason"))
                self.conn.commit()
                self.setupBuild(error=1)
        else:
            print(bcolours.FAIL + "An incomplete build was detected." + bcolours.ENDC)
            print("Error Reason: %s" % self.data[0][0])
            print("File Name: %s" % self.data[0][1][:60])
            print("Kernel Version: %s" % self.data[0][2])
            print("Date: %s" % self.data[0][3])
            print("---------------------------------------------------------------------------------")

            self.cursor.execute('DELETE FROM {tn} WHERE {cn}="Compile Error"'.format(tn='BuildFailure', cn='FailureReason'))
            self.conn.commit()
            clean = input("Do you want to discard this build? (y/n): ")
            print(clean)
            if clean.upper() == "N":
                self.setupBuild(error=1)
            elif clean.upper() == "Y":
                self.setupBuild()
            else:
                raise SystemExit


    def buildInit(self, localversionarg=None, zImageExists=False):
        if zImageExists == True:
            self.createFlashableZip()
        else:
            if localversionarg == 0:
                localversion = str(self.data[0][2])
                self.localversion += localversion
                makeThread = threading.Thread(target=self.buildMake)
                makeThread.start()
            else:
                localversion = self.localversion
            subprocess.call("clear", shell=True)
            print("---------------------------------------------------------------------------------")
            print(bcolours.HEADER + "Neutron Build Process" + bcolours.ENDC)
            print("---------------------------------------------------------------------------------")
            print(bcolours.BOLD + "BUILD VARIABLES" + bcolours.ENDC)

            self.cursor.execute('SELECT * FROM {tn} WHERE {cn}="SaberMod"'.format(tn="UserDefaults", cn="VariableKey"))
            data = self.cursor.fetchall()

            path = str(os.environ.get('CROSS_COMPILE'))
            version = re.search('el/(.*)/b', path)
            if len(data) == 0:
                print(bcolours.OKBLUE + "Toolchain version: %s" % str(version.group(1)) + bcolours.ENDC)
            else:
                print(bcolours.OKBLUE + "Toolchain version: %s" % str(version.group(1)) + " " + "SaberMod GCC" + bcolours.ENDC)

            print(bcolours.OKBLUE + "Toolchain path: %s" % path + bcolours.ENDC)
            print(bcolours.OKBLUE + "Kernel version: %s" % localversion + bcolours.ENDC)
            p = subprocess.Popen("uname -o -n -i -v -r", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            for line in iter(p.stdout.readline, b''):
                self.lines = line.rstrip()
            print(bcolours.OKBLUE + "Host: %s" % str(self.lines.decode('utf-8')) + bcolours.ENDC)
            print(bcolours.OKBLUE + "CPU: %s with %i core(s)" % (self.CPUversion.decode("utf-8"), self.CPUcores) + bcolours.ENDC)
            print("                                                                             ")
            OK = input("If this is okay, press Enter to continue or Q to quit...")
            if OK.upper() == "Q":
                raise SystemExit
            else:
                self.conn.close()
                buildThread = threading.Thread(target=self.build)
                buildThread.start()





    def build(self):
        import time
        print("---------------------------------------------------------------------------------")
        time.sleep(0.6)
        os.environ['LOCALVERSION'] = self.localversion
        print("Preparing defconfig...")
        subprocess.call(["make", "hammerhead_defconfig"])
        print("Preparing menuconfig...")
        subprocess.call(["make", "menuconfig"])
        print("Preparing kernelrelease...")
        p = subprocess.Popen(["make", "kernelrelease"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, err = p.communicate()
        if self.localversion in output.decode('utf-8'):
            print(bcolours.OKGREEN + "OK: Kernel Version set correctly" + bcolours.ENDC)
        else:
            print(bcolours.WARNING + "WARNING: Kernel Version not set correctly" + bcolours.ENDC)

        makeThread = threading.Thread(target=self.buildMake)
        makeThread.start()

    def createFlashableZip(self):
        print(bcolours.OKBLUE + "Moving kernel modules..." + bcolours.ENDC)
        time.sleep(0.5)
        subprocess.call('find . -name "*.ko" -type f -exec cp {} zip/modules \;', shell=True)

        print(bcolours.OKBLUE + "Packing into flashable zip..." + bcolours.ENDC)
        time.sleep(0.5)
        subprocess.call("rm zip/Neutron*.zip", shell=True)
        try:
            subprocess.call("cp arch/arm/boot/zImage-dtb zip/setup/zImage-dtb", shell=True)
            cmd = 'cd zip && zip -r -9 "' + (str(self.localversion)[1:] + '.zip') + '" *'
            os.system(cmd)
        except TypeError:
            cmd = 'cd zip && zip -r -9 "Neutron-undefined.zip" *'
            os.system(cmd)


        print(bcolours.OKBLUE + "Signing zip file..." + bcolours.ENDC)
        if os.listdir('build/openssl') == []:
            print("Generating OpenSSL certificates...")
            time.sleep(0.3)
            print("Follow the prompts on screen.")
            time.sleep(2)
            subprocess.call("cd build/openssl && openssl genrsa -out sign.key 8192; openssl req -new -key sign.key -out request.pem; openssl x509 -req -days 9999 -in request.pem -signkey sign.key -out certificate.pem; openssl pkcs8 -topk8 -outform DER -in sign.key -inform PEM -out key.pk8 -nocrypt", shell=True)

        path = glob.glob("zip/*.zip")[0]
        signed_name = str(self.localversion)[1:] + "-signed" + ".zip"
        subprocess.call("java -jar build/signapk.jar build/openssl/certificate.pem build/openssl/key.pk8 %s zip/%s.zip" % (path, signed_name), shell=True)
        #subprocess.call("build/zipadjust zip/Neutron-signed.zip zip/Neutron-fixed.zip; rm zip/Neutron-signed.zip", shell=True)
        #subprocess.call("java -jar build/minsignapk.jar build/openssl/certificate.pem build/openssl/key.pk8 zip/Neutron-fixed.zip zip/Neutron-%s; rm zip/Neutron-fixed.zip" % signed_name, shell=True)

        print(bcolours.OKGREEN + "Done! Closing processes..." + bcolours.ENDC)
        subprocess.call("rm include/generated/compile.h", shell=True)
        subprocess.call("rm .build.py.conf", shell=True)
        time.sleep(2)
        raise SystemExit

    def buildMake(self):
        import time
        import sqlite3
        import datetime
        import subprocess
        time.sleep(0.5)
        print("---------------------------------------------------------------------------------")
        print(bcolours.BOLD + "Building..." + bcolours.ENDC)
        time.sleep(0.5)
        coreArg = "-j%i" % self.CPUcores

        spinnerThread = threading.Thread(target=self.spinner)
        self.spinnerShutdown = 0
        spinnerThread.start()

        time.sleep(3)

        p = subprocess.Popen(['make', coreArg], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        outLog = []
        for line in iter(p.stdout.readline, b''):
            print(str(line.rstrip().decode('utf-8')))
            outLog.append(" " + str(line.rstrip()))
        lastFile = None
        succeed = None
        for i, s in enumerate(outLog):
            if "Error" in s or "error" in s or "ERROR" in s:
                lastFile = outLog[i-1]

            if "arch/arm/boot/zImage-dtb is ready" in s:
                succeed = outLog[i]

        if lastFile == None or succeed is not None:
            print(bcolours.OKGREEN + "OK: Build succeeded" + bcolours.ENDC)
        else:
            time = datetime.datetime.now().strftime("%a %d %b %H:%M")
            print(bcolours.FAIL + "FAIL: Build error" + bcolours.ENDC)
            self.spinnerShutdown = 1
            self.conn = sqlite3.connect("build/neutronBuild.db")
            self.cursor = self.conn.cursor()
            self.cursor.execute("INSERT INTO BuildFailure VALUES (?, ?, ?, ?);", ("Compile Error", lastFile, self.localversion, time) )
            self.conn.commit()
            self.conn.close()
            raise SystemExit

        self.spinnerShutdown = 1

        if os.path.isfile("arch/arm/boot/zImage-dtb"):
            self.createFlashableZip()
        else:
            print("Hmm...the zImage can't be found.")



# Initial display of program in terminal
subprocess.call("clear", shell=True)
print("-----------------------------------------------------------------------------------------")
print(bcolours.HEADER + "Neutron hammerhead Debian/Linux build tool by Alex Potter (alexpotter1)" + bcolours.ENDC)
print(bcolours.HEADER + "Please only run on Linux (Debian, Ubuntu, etc)." + bcolours.ENDC)
print(bcolours.HEADER + "Version v3.0" + bcolours.ENDC)
print("-----------------------------------------------------------------------------------------")

app = InitStub()

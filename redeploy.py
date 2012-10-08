#!/usr/bin/python

import os
import fnmatch
import string
import shutil
import logging
import json
import zipfile
import sys

if not sys.platform.startswith('win'):
    import pexpect

REDEPLOY_DIR='.redeploy'
PACKAGE_INFO_FILE='package-info.json'


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger('redeploy')
logger.setLevel(logging.INFO)


def __isFileModifiedWithinPeriod(comparedFile, baseFile, periodInSec):
    if(periodInSec == -1):
        return os.stat(comparedFile).st_mtime == os.stat(baseFile).st_mtime
    else:
        return os.stat(comparedFile).st_mtime + periodInSec >= os.stat(baseFile).st_mtime
    

def __searchLastestModifiedFilesInDir(dir, filter, periodInSec=-1):
    changedFiles=[]
    matchFiles=[]
    for root,dirnames,filenames in os.walk(dir):
        for filename in fnmatch.filter(filenames, filter):
            matchFiles.append(os.path.join(root,filename))
    if len(matchFiles)==0:
    	return changedFiles
    latestFileTime=os.stat(matchFiles[0]).st_mtime
    latestFile=matchFiles[0];
    for resultFile in matchFiles:
        if(latestFileTime < os.stat(resultFile).st_mtime):
            latestFileTime=os.stat(resultFile).st_mtime
            latestFile=resultFile
    
    for resultFile in matchFiles:
        if (__isFileModifiedWithinPeriod(resultFile,latestFile,periodInSec)):
            changedFiles.append(resultFile)

    logger.info('Changed files: ' + str(changedFiles))
    return changedFiles;


def __copyRedeployFiles(changedFiles, packageName):
    if os.path.exists(REDEPLOY_DIR) == False:
        os.mkdir(REDEPLOY_DIR)

    redeployPackagePath = os.path.join(REDEPLOY_DIR,packageName)
    if os.path.exists(redeployPackagePath):
         shutil.rmtree(redeployPackagePath,ignore_errors=True)

    os.mkdir(redeployPackagePath)

    for changedFile in changedFiles:
        fileFolderStartIndex = changedFile.find('classes') + len('classes') + 1
        fileFolderEndIndex = changedFile.rfind(os.sep)
        fileFolderPath = changedFile[fileFolderStartIndex:fileFolderEndIndex]
        print fileFolderPath

        fileFolderFullPath = os.path.join(redeployPackagePath,fileFolderPath)
        try:
            os.makedirs(fileFolderFullPath)
        except:
            pass

        try:
            shutil.copy(changedFile, fileFolderFullPath)
        except:
            pass 


def __loadPackageInfo(packageInfos, packageName):
    logger.info('load ' + packageName + ' info.')
    for packageInfo in packageInfos:
        if packageName in packageInfo:        
            return packageInfo[packageName]


def __compressAndPackage(compressFolder, compressPackageName):
    if os.path.exists(compressPackageName):
        shutil.rmtree(compressPackageName, ignore_errors=True)

    zip = zipfile.ZipFile(compressPackageName, 'w', compression=zipfile.ZIP_DEFLATED)
    rootlen = len(compressFolder) + 1
    for base, dirs, files in os.walk(compressFolder):
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])

    shutil.rmtree(compressFolder, ignore_errors=True)


def __scpFiles(targetIp, targetUser, targetUserPwd, targetDeployPath):
    logger.info('scp redeploy files.')
    child = pexpect.spawn('scp -r redeploy.zip repackage.py redeployApplication.sh '+ targetUser + '@' + targetIp + ':' + targetDeployPath)
    child.logfile = sys.stdout
    __scpExpectIteration(child, targetUserPwd)


def __scpExpectIteration(child, targetUserPwd):
    result = child.expect(['Are you sure you want to continue connecting (yes/no)?', '(?i)password', pexpect.TIMEOUT, pexpect.EOF])
    if result == 0:
        child.sendline('yes')
        __scpExpectIteration(child, targetUserPwd)
    if result == 1:
        child.sendline(targetUserPwd)
        __scpExpectIteration(child, targetUserPwd)
    if result == 2:
        logger.error('scp files failed due to timeout.')
    if result == 3:
        pass


def __executeRemoteScript(targetIp, targetUser, targetUserPwd, targetDeployPath, targetPackage):
    logger.info('execute repackage.py script in remote target server.')
    child = pexpect.spawn('ssh ' + targetUser + '@' + targetIp, timeout=None)
    child.logfile = sys.stdout
    __exeucteRemoteScriptExpectIteration(child, targetUserPwd, targetDeployPath, targetPackage)


def __exeucteRemoteScriptExpectIteration(child, targetUserPwd, targetDeployPath, targetPackage):
    result = child.expect(['Are you sure you want to continue connecting', '(?i)password:', pexpect.TIMEOUT, pexpect.EOF])
    if result == 0:
        child.sendline('yes')
        __exeucteRemoteScriptExpectIteration(child, targetUserPwd, targetDeployPath)
    if result == 1:
        child.sendline(targetUserPwd)
        child.expect('#')
        child.sendline('cd ' + targetDeployPath)
        child.expect('#')
        child.sendline('./repackage.py')
        child.expect('#')
        child.sendline('./redeployApplication.sh ' + targetPackage)
        child.expect('#')
        child.sendline('exit')
        __exeucteRemoteScriptExpectIteration(child, targetUserPwd, targetDeployPath)
    if result ==2:
        logger.error('execute remote script failed due to timeout.')
    if result ==3:
        pass


def __rollback():
    shutil.rmtree(REDEPLOY_DIR, ignore_errors=True)
    shutil.rmtree('redeploy.zip', ignore_errors=True)


def main():
    jsonFile = open('redeploy.json', 'rb')
    redeployData = json.load(jsonFile)

    try:
        sourcePackageNames = redeployData['sourcePackages']
        packageInfos = redeployData['packages']

        for packageName in sourcePackageNames:
            packageInfo = __loadPackageInfo(packageInfos, packageName)

            searchDir = packageInfo['filePath']

            if 'filter' in packageInfo:
                searchFilter = packageInfo['filter']
            else:
                searchFilter = '*'

            changedFiles = __searchLastestModifiedFilesInDir(searchDir, searchFilter, 600)
            
            if len(changedFiles) != 0:
                __copyRedeployFiles(changedFiles, packageName)

        jsonFile.close()

        try:
            shutil.copy('redeploy.json', REDEPLOY_DIR)
        except:
            pass

        __compressAndPackage(REDEPLOY_DIR, 'redeploy.zip')

        if not sys.platform.startswith('win'):
            targetIp = redeployData['targetServerIP']
            targetUser = redeployData['targetServerUser']
            targetUserPwd = redeployData['targetServerPwd']
            targetDeployPath = redeployData['targetServerDeployPath']
            targetPackage = redeployData['targetPackage']

            __scpFiles(targetIp, targetUser, targetUserPwd, targetDeployPath)
            __executeRemoteScript(targetIp, targetUser, targetUserPwd, targetDeployPath, targetPackage)
    except:
        __rollback()
        jsonFile.close()


if __name__ == "__main__":
    main()

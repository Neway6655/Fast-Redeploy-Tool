#!/usr/bin/python

import os
import fnmatch
import string
import shutil
import logging
import json
from collections import OrderedDict

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
    

def __searchLastestModifiedFilesInDir(dir, periodInSec=-1):
    changedFiles=[]
    matchFiles=[]
    for root,dirnames,filenames in os.walk(dir):
        for filename in fnmatch.filter(filenames, '*'):
            matchFiles.append(os.path.join(root,filename))

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


def __copyRedeployFiles(packageName, changedFiles):
    if os.path.exists(REDEPLOY_DIR) == False:
        os.mkdir(REDEPLOY_DIR)

    redeployPackagePath = os.path.join(REDEPLOY_DIR,packageName)
    if os.path.exists(redeployPackagePath):
         shutil.rmtree(redeployPackagePath,ignore_errors=True)

    os.mkdir(redeployPackagePath)

    for changedFile in changedFiles:
        try:
            shutil.copy(changedFile, redeployPackagePath)
        except:
            pass 


def __loadPackageInfo(packageInfos, packageName):
    logger.info('load ' + packageName + ' info.')
    for packageInfo in packageInfos:
        if packageName in packageInfo:        
            return packageInfo[packageName]


def main():
    jsonFile = open('redeploy.json', 'rb')
    redeployData = json.load(jsonFile)
    
    sourcePackageNames = redeployData['sourcePackages']
    packageInfos = redeployData['packages']

    for packageName in sourcePackageNames:
        packageInfo = __loadPackageInfo(packageInfos, packageName)

        searchDir = packageInfo['filePath']

        changedFiles = __searchLastestModifiedFilesInDir(searchDir, 120)        
        
        __copyRedeployFiles(packageName, changedFiles)    
    

    jsonFile.close()

    try:
        shutil.copy('redeploy.json', REDEPLOY_DIR)
    except:
        pass
    

if __name__ == "__main__":
    main()
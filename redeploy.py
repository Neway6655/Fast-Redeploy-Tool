#!/usr/bin/python

import os
import fnmatch
import string
import shutil
import logging
import json
import zipfile

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
        fileFolderEndIndex = changedFile.rfind('\\')
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
    zip = zipfile.ZipFile(compressPackageName, 'w', compression=zipfile.ZIP_DEFLATED)
    rootlen = len(compressFolder) + 1
    for base, dirs, files in os.walk(compressFolder):
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])

    shutil.rmtree(compressFolder, ignore_errors=True)


def main():
    jsonFile = open('redeploy.json', 'rb')
    redeployData = json.load(jsonFile)
    
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
        
        __copyRedeployFiles(changedFiles, packageName)

    jsonFile.close()

    try:
        shutil.copy('redeploy.json', REDEPLOY_DIR)
    except:
        pass

    __compressAndPackage(REDEPLOY_DIR, 'redeploy.zip')    
    

if __name__ == "__main__":
    main()
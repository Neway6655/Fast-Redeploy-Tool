#!/usr/bin/python

import os
import fnmatch
import string
import shutil
import zipfile
import logging
import json
from datetime import datetime


TEMP_EXTRACT_DIR='.temp'
REDEPLOY_DIR='.redeploy'

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger('repackage')
logger.setLevel(logging.INFO)


def getCurrentDateTime():
    now = datetime.now()
    return string.join([str(now.year),str(now.month),str(now.day)],'.')+'_'+string.join([str(now.hour),str(now.minute)],'.')


### clean up the temp dir which used for extract old package files and packaging new files.
def __cleanUp():
    if os.path.exists(TEMP_EXTRACT_DIR):
        shutil.rmtree(TEMP_EXTRACT_DIR,ignore_errors=True)
        
    if os.path.exists(REDEPLOY_DIR):
        shutil.rmtree(REDEPLOY_DIR,ignore_errors=True)
        

### search the old package file filter by package name.
def __searchOldPackage(packageFilterName):
    packageFile = ''
    for root,dirnames,filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, packageFilterName):
            packageFile = os.path.join(root,filename)
            break
        
    if packageFile == '':
        logger.error('package not found by filter: ' + packageFilterName)
        exit(1)
    else:
        logger.info('package found: ' + packageFile)
    return packageFile


### back up the old package with current dateTime as suffix.
def __backupOldPackage(packageFile):
    currentTimeString = getCurrentDateTime()
    logger.info('backup old package: ' + packageFile)
    shutil.copy(packageFile, packageFile + '_' + currentTimeString)
        
        
### extract the old package files into desPackageDir
def __extractOldPackageFiles(packageFile, desPackageDir):
    logger.info('extract package files into ' + desPackageDir)
    z = zipfile.ZipFile(packageFile)
    z.extractall(desPackageDir)


### update the modified files into the desFilesDir.
def __updateModifiedFiles(modifiedFilesDir, desFilesDir, packageName, packageType):
    dst = desFilesDir
    if packageType == 'war':
        dst = os.path.join(desFilesDir, 'WEB-INF', 'classes')

    for root,dirnames,filenames in os.walk(modifiedFilesDir):
        index = root.find(packageName) + len(packageName) + 1
        if not index >= len(root):
            for dirname in dirnames:
                if not os.path.exists(os.path.join(dst, root[index:], dirname)):
                    os.makedirs(os.path.join(dst, root[index:], dirnames))
            for filename in filenames:
                logger.info('update file: ' + filename)
                shutil.copy(os.path.join(root, filename), os.path.join(dst, root[index:], filename))


### re-package the tempPackageDir as an new package and replace the oldPackageFile
def __repackageFiles(tempPackageDir, oldPackageFile):
    zip = zipfile.ZipFile(oldPackageFile, 'w', compression=zipfile.ZIP_DEFLATED)
    rootlen = len(tempPackageDir) + 1
    for base, dirs, files in os.walk(tempPackageDir):
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])


def __getPackageType(packageInfos, packageName):
    for packageInfo in packageInfos:
        if packageName in packageInfo:
            return packageInfo[packageName]['packageType']

    logger.error('Can not find package type of package: ' + packageName)
    exit(1)

def __cleanUpTemporaryDir(tempDir):
    if os.path.exists(tempDir):
        shutil.rmtree(tempDir, ignore_errors=True)


def __updatePackageFiles(packageName, packageType, needBackup):
    packageFile = __searchOldPackage(packageName + '*.' + packageType)

    if needBackup:
        __backupOldPackage(packageFile)

    packageDir = os.path.dirname(packageFile)
    tempExtractDir = os.path.join(packageDir, TEMP_EXTRACT_DIR)
    __extractOldPackageFiles(packageFile, tempExtractDir)
    __updateModifiedFiles(os.path.join(REDEPLOY_DIR, packageName), tempExtractDir, packageName, packageType)

    return packageFile


def main():
    jsonFile = open(os.path.join(REDEPLOY_DIR,'redeploy.json'), 'rb')
    redeployData = json.load(jsonFile)

    targetPackage = redeployData['targetPackage']
    sourcePackages = redeployData['sourcePackages']
    packageInfos = redeployData['packages']
    
    # first, find the target package in dest server, and un-package it, and replace the files in .redeploy's target package folder.    
    targetPackageType = __getPackageType(packageInfos, targetPackage)
    packageFile = __updatePackageFiles(targetPackage, targetPackageType, True)
    
    # second, replace the files in .redeploy's left sub-packages.
    for sourcePackage in sourcePackages:
        if sourcePackage != targetPackage:
            sourcePackageType = __getPackageType(packageInfos, sourcePackage)
            sourcePackageFile = __updatePackageFiles(sourcePackage, sourcePackageType, False)

            sourcePackageDir = os.path.dirname(sourcePackageFile)
            tempExtractDir = os.path.join(sourcePackageDir, TEMP_EXTRACT_DIR)
            __repackageFiles(tempExtractDir, sourcePackageFile)
            __cleanUpTemporaryDir(os.path.join(sourcePackageDir, TEMP_EXTRACT_DIR))

    __repackageFiles(TEMP_EXTRACT_DIR, packageFile)
    __cleanUpTemporaryDir(TEMP_EXTRACT_DIR)

    logger.info('repackage finished.')
    

if __name__ == "__main__":
    main()
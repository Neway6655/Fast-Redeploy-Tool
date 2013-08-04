#!/usr/bin/python

import os
import fnmatch
import string
import shutil
import zipfile
import logging
import json
import re
import traceback
from datetime import datetime


TEMP_EXTRACT_DIR='.temp'
REDEPLOY_DIR='.redeploy'
REDEPLOY_ZIP='redeploy.zip'

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger('repackage')
logger.setLevel(logging.INFO)


def getCurrentDateTime():
    now = datetime.now()
    return string.join([str(now.year),str(now.month),str(now.day)],'.')+'_'+string.join([str(now.hour),str(now.minute)],'.')
        

### clean up the folder generated temporary.
def __cleanUpOldTempFiles():
    if os.path.exists(REDEPLOY_DIR):
        shutil.rmtree(REDEPLOY_DIR, ignore_errors=True)
    if os.path.exists(TEMP_EXTRACT_DIR):
        shutil.rmtree(TEMP_EXTRACT_DIR, ignore_errors=True)


### search the old package file filter by package name.
def __searchOldPackage(packageFilterName):
    packageFilePath = ''
    packageFileName = ''
    for root,dirnames,filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, packageFilterName):
            packageFilePath = os.path.join(root,filename)
            packageFileName = filename
            break
        
    if packageFilePath == '':
        logger.error('package not found by filter: ' + packageFilterName)
        exit(1)

    return packageFilePath, packageFileName


### back up the old package with current dateTime as suffix.
def __backupOldPackage(packageFile):
    currentTimeString = getCurrentDateTime()
    logger.info('backup old package: ' + packageFile)
    shutil.copy(packageFile, packageFile + '_' + currentTimeString)

    return packageFile + '_' + currentTimeString
         
        
### extract the old package files into desPackageDir
def __extractPackageFiles(packageFile, desPackageDir):
    z = zipfile.ZipFile(packageFile)
    z.extractall(desPackageDir)


### update the modified files into the desFilesDir.
def __updateModifiedFiles(modifiedFilesDir, desFilesDir, packageName, packageType):
    logger.info('update modified files of package: ' + packageName)
    dst = desFilesDir
    if packageType == 'war':
        dst = os.path.join(desFilesDir, 'WEB-INF', 'classes')

    for root,dirnames,filenames in os.walk(modifiedFilesDir):
        index = root.find(packageName) + len(packageName) + 1
        if not index > len(root) + 1:
            for dirname in dirnames:
                dirnameEscape = re.escape(str(dirname))
                if not os.path.exists(os.path.join(dst, root[index:], dirnameEscape)):
                    os.makedirs(os.path.join(dst, root[index:], dirnameEscape))
            for filename in filenames:
                logger.info('update file: ' + filename)
                shutil.copy(r''+(str(os.path.join(root, filename))), r''+(str(os.path.join(dst, root[index:], filename))))


### re-package the tempPackageDir as an new package and replace the oldPackageFile
def __repackageFiles(tempPackageDir, oldPackageFile):
    os.system("cd " + tempPackageDir + "; jar cf " + oldPackageFile + " *; mv -f "+ oldPackageFile +" ../; cd ..")
    logger.info('repackage finished: ' + oldPackageFile)


def __getPackageAttribute(packageInfos, packageName, packageAttribute):
    for packageInfo in packageInfos:
        if packageName in packageInfo:
            return packageInfo[packageName][packageAttribute]

    logger.error('Can not find package attribute of package: ' + packageName)
    exit(1)    

def __cleanUpFileOrDir(tempFileOrDir):
    if os.path.exists(tempFileOrDir):
        if os.path.isdir(tempFileOrDir):
            shutil.rmtree(tempFileOrDir, ignore_errors=True)
        else:
            os.remove(tempFileOrDir)


def __updatePackageFiles(packageName, packageType, needBackup):
    packageFilePath, packageFileName = __searchOldPackage(packageName + '*.' + packageType)

    if needBackup:
        __backupOldPackage(packageFilePath)

    packageDir = os.path.dirname(packageFilePath)
    tempExtractDir = os.path.join(packageDir, TEMP_EXTRACT_DIR)
    __extractPackageFiles(packageFilePath, tempExtractDir)
    __updateModifiedFiles(os.path.join(REDEPLOY_DIR, packageName), tempExtractDir, packageName, packageType)

    return packageFilePath, packageFileName


def __rollback(newPackageFile, backupPackageFile):
    if (os.path.exists(backupPackageFile)):
        os.remove(newPackageFile)
        os.rename(backupPackageFile, newPackageFile)


def main():
    __cleanUpOldTempFiles()
    __extractPackageFiles(REDEPLOY_ZIP, REDEPLOY_DIR)

    try:
        jsonFile = open(os.path.join(REDEPLOY_DIR,'redeploy.json'), 'rb')
        redeployData = json.load(jsonFile)

        targetPackage = redeployData['targetPackage']
        targetPackageType = redeployData['targetPackageType']
        sourcePackages = redeployData['sourcePackages']
        packageInfos = redeployData['packages']
        
        # first, backup old target package and extract the target package into temp folder.
        packageFilePath, packageFileName = __searchOldPackage(targetPackage + '*.' + targetPackageType)
        backupPackageFilePath = __backupOldPackage(packageFilePath)
        packageDir = os.path.dirname(packageFilePath)
        tempExtractDir = os.path.join(packageDir, TEMP_EXTRACT_DIR)
        __extractPackageFiles(packageFilePath, tempExtractDir)
        
        # second, replace the files in .redeploy's left sub-packages.
        for sourcePackage in sourcePackages:
            sourcePackageType = __getPackageAttribute(packageInfos, sourcePackage, 'packageType')
            isInnerPackage = __getPackageAttribute(packageInfos, sourcePackage, 'innerPackage')
            if not isInnerPackage:
                logger.info('repackage the outer package: ' + sourcePackage)
                __updateModifiedFiles(os.path.join(REDEPLOY_DIR, sourcePackage), tempExtractDir, sourcePackage, sourcePackageType)
            else:
                logger.info('repackage the inner package: ' + sourcePackage)
                sourcePackageFilePath, sourcePackageFileName = __updatePackageFiles(sourcePackage, sourcePackageType, False)
                sourcePackageDir = os.path.dirname(sourcePackageFilePath)
                subTempExtractDir = os.path.join(sourcePackageDir, TEMP_EXTRACT_DIR)
                __repackageFiles(subTempExtractDir, sourcePackageFileName)
                __cleanUpFileOrDir(subTempExtractDir)

        logger.info('finish replacing files.')
        __repackageFiles(TEMP_EXTRACT_DIR, packageFilePath)
        jsonFile.close()

        logger.info('finish repackage.')
        __cleanUpFileOrDir(TEMP_EXTRACT_DIR)
        __cleanUpFileOrDir(REDEPLOY_DIR)
        __cleanUpFileOrDir(REDEPLOY_ZIP)

        logger.info('repackage finished.')
    except:
        logger.info('Error happens, rollback.')
        traceback.print_exc()
        __rollback(packageFilePath, backupPackageFilePath)
        jsonFile.close()
    

if __name__ == "__main__":
    main()

import os
import fnmatch
import string
import shutil
import zipfile
import csv
import logging
from datetime import datetime

PACKAGE_INFO_FILE='package-info'
PACKAGE_NAME='package_name'
PACKAGE_TYPE='package_type'

TEMP_EXTRACT_DIR='.temp'
REDEPLOY_DIR='.redeploy'

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger('repackage')
logger.setLevel(logging.INFO)


def getCurrentDateTime():
    now = datetime.now()
    return string.join([str(now.year),str(now.month),str(now.day)],'.')+'_'+string.join([str(now.hour),str(now.minute)],'.')


### Search file in the desDir with fileName, then replace it with new modifiedFile. 
def searchAndReplaceFile(modifiedFile, fileName, desDir):
    logger.info('update file: ' + fileName)
    for root,dirnames,filenames in os.walk(desDir):
        for filename in fnmatch.filter(filenames, fileName):
            shutil.copy(modifiedFile, os.path.join(root,filename))


### read value from csv file with 'key=value' format
def readProperties(propertiesFile, key):
    reader = csv.reader(open(propertiesFile, 'rb'), delimiter='=', quotechar='|')
    value=''
    for line in reader:
        if(line[0].strip().lower() == key):
            value = line[1].strip()
            break
        
    return value


### clean up the temp dir which used for extract old package files and packaging new files.
def __cleanUp():
    if os.path.exists(TEMP_EXTRACT_DIR):
        shutil.rmtree(TEMP_EXTRACT_DIR,ignore_errors=True)
        

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
    shutil.copy(packageFile, packageFile + '_' + currentTimeString)
        
        
### extract the old package files into desPackageDir
def __extractOldPackageFiles(packageFile, desPackageDir):
    z = zipfile.ZipFile(packageFile)
    z.extractall(desPackageDir)


### update the modified files into the desFilesDir.
def __updateModifiedFiles(modifiedFilesDir, desFilesDir):
    for root,dirnames,filenames in os.walk(modifiedFilesDir):
        for filename in filenames:
            if(filename != PACKAGE_INFO_FILE):
                searchAndReplaceFile(os.path.join(root, filename), filename, desFilesDir)


### re-package the tempPackageDir as an new package and replace the oldPackageFile
def __repackageFiles(tempPackageDir, oldPackageFile):
    zip = zipfile.ZipFile(oldPackageFile, 'w', compression=zipfile.ZIP_DEFLATED)
    rootlen = len(tempPackageDir) + 1
    for base, dirs, files in os.walk(tempPackageDir):
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])

def __updateWarPackageFiles():
    __cleanUp();
    
    packageName = readProperties(os.path.join(REDEPLOY_DIR,PACKAGE_INFO_FILE), PACKAGE_NAME)
    
    packageFile = __searchOldPackage(packageName + '*.war')
    
    __backupOldPackage(packageFile)
    
    __extractOldPackageFiles(packageFile, TEMP_EXTRACT_DIR)
    
    __updateModifiedFiles(REDEPLOY_DIR, TEMP_EXTRACT_DIR)
    
    __repackageFiles(TEMP_EXTRACT_DIR, packageFile)


def main():
    packageType = readProperties(os.path.join(REDEPLOY_DIR,PACKAGE_INFO_FILE), PACKAGE_TYPE)
    if (packageType == 'war'):
        __updateWarPackageFiles()
    

if __name__ == "__main__":
    main()
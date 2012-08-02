import os
import fnmatch
import string
import csv
import shutil
import logging
from collections import OrderedDict

PROPERTIES_FILE='./redeploy.properties'
PACKAGE_INFO_FILE='package-info'

DIR='dir'
FILTER='filter'
PACKAGE_NAME='package_name'
PACKAGE_TYPE='package_type'

REDEPLOY_DIR='.redeploy'


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)

logger = logging.getLogger('repackage')
logger.setLevel(logging.INFO)

def readProperties(propertiesFile, key):
    reader = csv.reader(open(propertiesFile, 'rb'), delimiter='=', quotechar='|')
    value=''
    for line in reader:
        if(line[0].strip().lower() == key):
            value = line[1].strip()
            break
    return value

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


def __loadPackageInfoFromPom():
    if(os.path.exists('pom.xml')):
        with open('pom.xml') as lines:
            for line in lines:
                line = line.strip()
                if (line.startswith('<packaging>')):
                    startIndex = len('<packaging>')
                    endIndex = line.index('</packaging>')
                    packageType = line[startIndex:endIndex]
                    print packageType
        
        
def __loadPackageInfoFromProperties():
    packageInfo = {}
    packageName = readProperties(PROPERTIES_FILE, PACKAGE_NAME)
    packageType = readProperties(PROPERTIES_FILE, PACKAGE_TYPE)
    
    packageInfo[PACKAGE_NAME] = packageName
    packageInfo[PACKAGE_TYPE] = packageType

    return packageInfo
    
    
def __getPackageInfo():
    return __loadPackageInfoFromProperties()
    
    
def __generatePackageInfoFile():
    packageInfo = __getPackageInfo()
    packageInfoFilePath = os.path.join(REDEPLOY_DIR,PACKAGE_INFO_FILE)
    ordered_fieldnames = OrderedDict([('KEY',None),('VALUE',None)])
    writer=csv.DictWriter(open(packageInfoFilePath,'w+'), delimiter='=',fieldnames=ordered_fieldnames, extrasaction='ignore' )
    logger.info("Package info: " + str(packageInfo))
    for key in packageInfo.keys():
        writer.writerow({'KEY':key, 'VALUE':packageInfo[key]})


def __copyRedeployFiles(changedFiles):
    if (os.path.exists(REDEPLOY_DIR)):
        shutil.rmtree(REDEPLOY_DIR)
    os.mkdir(REDEPLOY_DIR)
    for file in changedFiles:
        shutil.copy(file, REDEPLOY_DIR)


def main():
    projectDir = readProperties(PROPERTIES_FILE, DIR)
    fileSearchFilter = readProperties(PROPERTIES_FILE, FILTER)
    
    changedFiles = __searchLastestModifiedFilesInDir(projectDir, fileSearchFilter, 60)
    
    __copyRedeployFiles(changedFiles)
    
    __generatePackageInfoFile()
    
    

if __name__ == "__main__":
    main()
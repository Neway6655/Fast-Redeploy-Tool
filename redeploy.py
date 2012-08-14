#!/usr/bin/python

import os
import fnmatch
import string
import csv
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
        
    
    
def __generatePackageInfoFile(packageName, packageType):
    packageInfoDict = {}
    packageInfoDict['packageName'] = packageName
    packageInfoDict['packageType'] = packageType

    if os.path.exists(os.path.join(REDEPLOY_DIR, packageName)) == False:
        logger.error('folder "' +packageName + '" in dir "' + REDEPLOY_DIR + '"" not exists, can not write package-info.json into it')

    packageInfoFilePath = os.path.join(REDEPLOY_DIR, packageName, PACKAGE_INFO_FILE)
    packageInfoFile = open(packageInfoFilePath,'w+')

    json.dump(packageInfoDict, packageInfoFile)    

    packageInfoFile.close()


def __copyRedeployFiles(projectName, changedFiles):
    if os.path.exists(REDEPLOY_DIR) == False:
        os.mkdir(REDEPLOY_DIR)

    redeployProjectPath = os.path.join(REDEPLOY_DIR,projectName)
    if os.path.exists(redeployProjectPath):
         shutil.rmtree(redeployProjectPath,ignore_errors=True)

    os.mkdir(redeployProjectPath)

    for file in changedFiles:
        try:
            shutil.copy(file, redeployProjectPath)
        except:
            pass 
        
#def __scpRedepolyedFiles2Server():
    #call("scp -r .redeploy root@10.44.136.241:/home/occas/deployables/oauth2-api")
    #child = pexpect.spawn('scp -r .redeploy root@10.44.136.241:/home/occas/deployables/oauth2-api')
    #child.expect ('Password:')
    #child.sendline ('rootroot')

def __loadProjectInfo(projectInfos, projectName):
    logger.info('load ' + projectName + ' info.')
    for project in projectInfos:
        if projectName in project:        
            return project[projectName]


def main():
    jsonFile = open('redeploy.json', 'rb')
    redeployData = json.load(jsonFile)
    
    sourceProjectNames = redeployData['sourceProjects']
    projectInfos = redeployData['projects']

    for projectName in sourceProjectNames:
        projectInfo = __loadProjectInfo(projectInfos, projectName)

        searchDir = projectInfo['buildPath']
        searchFilter = projectInfo['filter']

        changedFiles = __searchLastestModifiedFilesInDir(searchDir, searchFilter, 120)

        packageName = projectInfo['packageName']
        
        __copyRedeployFiles(packageName, changedFiles)
        
        __generatePackageInfoFile(packageName, projectInfo['packageType'])
    
 #   __scpRedepolyedFiles2Server()

    jsonFile.close()
    

if __name__ == "__main__":
    main()
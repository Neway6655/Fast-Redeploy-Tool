Fast-Redeploy-Tool
==================

It's a redeploy tool which used to fast redeploy a java based application package. Common used when doing the performance tuning.

Pre-condition:
Python 2.7(or 2.6) installed in your machine.

How to use it:
* config redeploy.json, comments as below:

```
{
	// the redeployed target server ip address
	"targetServerIP": "10.44.132.113",
	"targetServerUser": "root",
	"targetServerPwd": "rootroot",
	// the path of the redeploy packaged folder.
	"targetServerDeployPath": "/home/occas/deployables/user-profile",
	// redeploy package name
	"targetPackage": "user-profile",
	// redeploy package type
	"targetPackageType": "ear",
	// the source code you want to redeploy, for example, some code in access-common has modified, and you want them to be redeployed, then write down the source package name here, and you can write down multi source package seperated by ','.
	"sourcePackages": [
		"access-common"
	],
	// define the source package above here. The package name, type, file path and innerPackage (true of false), which means the package is inside the target package or not. 
	"packages": [
		{
			"access-common": {
				"packageType": "jar",
				"innerPackage": true,
				"filePath": "C:\\work\\ECE\\common-function\\access-common\\target\\classes"
			}
		}
	]
}
```

* execute the redeploy.py and an redeploy.zip file will be generated(if you are in windows.), then all the files modified will be packaged into it.

* upload the redeploy.zip (and repackage.py if its your first time using this) into the target server, under same folder of redeploy package.

* execute repackage.py(python repackage.py) and you will see how many files has been redeployed. (the previous target package will be back up by adding suffix with the timestamp)

* execute ./redeployApplication.sh appName (such as oauth2-api) to redeploy in weblogic.
